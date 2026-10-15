"""Order State Machine & Lifecycle Service (Phase 7).

Enforces deterministic status transitions:
OPEN -> IN_PROGRESS -> AT_RISK -> COMPLETED / CANCELLED.
Handles inventory reservation releases upon order cancellation and validates shipment delivery before completion.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from fastapi import HTTPException, status

logger = logging.getLogger("enterpriseai.orders.lifecycle")

LEGAL_TRANSITIONS: Dict[str, Set[str]] = {
    "OPEN": {"IN_PROGRESS", "AT_RISK", "CANCELLED"},
    "IN_PROGRESS": {"AT_RISK", "COMPLETED", "CANCELLED"},
    "AT_RISK": {"IN_PROGRESS", "COMPLETED", "CANCELLED"},
    "COMPLETED": set(),  # Terminal
    "CANCELLED": set(),  # Terminal
}


def transition_order_status(
    conn,
    order_id: str,
    new_status: str,
    reason: Optional[str] = None,
    actor_id: str = "system_operator",
) -> Dict[str, Any]:
    """Execute a validated order status transition with precondition checks and audit logging."""
    target_status = new_status.strip().upper()
    now = datetime.now(timezone.utc)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT order_id, status, customer_ref, entity_id
            FROM orders
            WHERE order_id = %s
            FOR UPDATE;
            """,
            (order_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order '{order_id}' not found.",
            )

        current_status = row[1]

        # Idempotent no-op
        if current_status == target_status:
            return {
                "order_id": order_id,
                "current_status": current_status,
                "previous_status": current_status,
                "transitioned": False,
                "message": f"Order {order_id} is already in status {target_status}.",
            }

        allowed = LEGAL_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Illegal order status transition from '{current_status}' to '{target_status}'. Allowed transitions: {sorted(allowed)}",
            )

        # Precondition for COMPLETED: ensure no pending/in-transit shipments
        if target_status == "COMPLETED":
            cur.execute(
                """
                SELECT shipment_id, status
                FROM shipments
                WHERE order_id = %s AND status NOT IN ('DELIVERED', 'CANCELLED');
                """,
                (order_id,),
            )
            undelivered = cur.fetchall()
            if undelivered:
                pending_ids = [r[0] for r in undelivered]
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot complete order '{order_id}': shipments pending delivery ({pending_ids}).",
                )

        # Precondition for CANCELLED: release any active stock reservations
        released_reservations = []
        if target_status == "CANCELLED":
            cur.execute(
                """
                SELECT reservation_id, product_id, warehouse_id, reserved_qty_mt
                FROM stock_reservations
                WHERE reference_id = %s AND status = 'ACTIVE'
                FOR UPDATE;
                """,
                (order_id,),
            )
            for res_row in cur.fetchall():
                res_id, prod_id, wh_id, qty = res_row[0], res_row[1], res_row[2], float(res_row[3])
                # Release reservation
                cur.execute(
                    "UPDATE stock_reservations SET status = 'RELEASED', updated_at = %s WHERE reservation_id = %s;",
                    (now, res_id),
                )
                # Adjust inventory
                cur.execute(
                    """
                    UPDATE inventory
                    SET reserved_qty = GREATEST(0.0, reserved_qty - %s),
                        available_qty = on_hand_qty - GREATEST(0.0, reserved_qty - %s),
                        updated_at = %s
                    WHERE item_id = %s AND warehouse_id = %s;
                    """,
                    (qty, qty, now, prod_id, wh_id),
                )
                # Log movement
                mov_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO inventory_movements (
                        movement_id, product_id, warehouse_id, movement_type,
                        quantity_mt, reference_type, reference_id, actor_id, notes
                    )
                    VALUES (%s, %s, %s, 'RESERVATION_RELEASE', %s, 'ORDER', %s, %s, %s);
                    """,
                    (mov_id, prod_id, wh_id, qty, order_id, actor_id, f"Order {order_id} cancelled release"),
                )
                released_reservations.append(res_id)

        # Update order status
        cur.execute(
            """
            UPDATE orders
            SET status = %s, updated_at = %s
            WHERE order_id = %s;
            """,
            (target_status, now, order_id),
        )

        # Append audit event into event_log
        import hashlib
        import json

        evt_id = str(uuid.uuid4())
        payload = {
            "order_id": order_id,
            "previous_status": current_status,
            "new_status": target_status,
            "reason": reason or "Status transition via lifecycle API",
            "actor_id": actor_id,
            "released_reservations": released_reservations,
        }
        payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        cur.execute(
            """
            INSERT INTO event_log (
                event_id, event_type, entity_type, entity_id,
                actor_type, actor_id, status, payload_hash, event_timestamp
            )
            VALUES (%s, 'ORDER_STATUS_CHANGED', 'ORDER', %s, 'OPERATOR', %s, 'RECORDED', %s, %s);
            """,
            (evt_id, order_id, actor_id, payload_hash, now),
        )

        conn.commit()

        logger.info(
            "Order %s transitioned from %s to %s by %s",
            order_id,
            current_status,
            target_status,
            actor_id,
        )

        return {
            "order_id": order_id,
            "previous_status": current_status,
            "new_status": target_status,
            "transitioned": True,
            "event_id": evt_id,
            "released_reservations_count": len(released_reservations),
            "updated_at": now.isoformat(),
        }
