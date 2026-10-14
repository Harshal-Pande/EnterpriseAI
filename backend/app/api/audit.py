from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.database import get_db
from app.models.audit import AuditEvent

logger = logging.getLogger("enterpriseai.audit")

router = APIRouter()


@router.get("/", response_model=List[AuditEvent])
def get_audit_trail(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    order_id: Optional[str] = Query(None, description="Filter by order ID"),
    actor_id: Optional[str] = Query(None, description="Filter by actor ID"),
    actor: Optional[str] = Query(None, description="Filter by actor"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by event status"),
    limit: int = Query(50, ge=1, le=500, description="Maximum audit events to return"),
    offset: int = Query(0, ge=0, description="Number of audit events to skip"),
    sort_order: str = Query("desc", description="Sort direction by timestamp (asc or desc)"),
    conn=Depends(get_db),
):
    """Retrieve immutable audit trail from PostgreSQL event_log and blockchain_anchors tables."""
    sort_order_upper = sort_order.upper()
    if sort_order_upper not in {"ASC", "DESC"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_order: {sort_order}. Must be 'asc' or 'desc'.",
        )

    clauses: list[str] = []
    params: list = []

    if event_type:
        clauses.append("el.event_type = %s")
        params.append(event_type.strip())

    effective_entity = entity_id or order_id
    if effective_entity:
        clauses.append("el.entity_id = %s")
        params.append(effective_entity.strip())

    effective_actor = actor_id or actor
    if effective_actor:
        clauses.append("el.actor_id = %s")
        params.append(effective_actor.strip())

    if status_filter:
        clauses.append("el.status = %s")
        params.append(status_filter.strip())

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    sql = f"""
        SELECT
            el.event_id,
            el.event_timestamp,
            el.event_type,
            el.entity_type,
            el.entity_id,
            el.scenario_id,
            el.workflow_run_id,
            el.actor_type,
            el.actor_id,
            el.status,
            el.reason_code,
            el.evidence_refs,
            el.payload_hash,
            el.previous_event_hash,
            el.source_channel,
            ba.transaction_hash,
            ba.block_number,
            ba.confirmation_status,
            ba.verification_status
        FROM event_log el
        LEFT JOIN blockchain_anchors ba ON el.event_id::text = ba.event_id_or_batch_id
        {where_sql}
        ORDER BY el.event_timestamp {sort_order_upper}, el.event_id {sort_order_upper}
        LIMIT %s OFFSET %s;
    """
    params.extend([limit, offset])

    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    except Exception as exc:
        logger.error("Database query failed in get_audit_trail: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query failed while retrieving audit trail",
        ) from exc

    results: list[AuditEvent] = []
    for r in rows:
        event_id_str = str(r[0])
        ts_str = r[1].isoformat() if r[1] else ""
        ev_type = r[2]
        ent_type = r[3]
        ent_id = r[4]
        ord_id = ent_id if ent_type == "ORDER" else None
        act_id = r[8]
        ev_status = r[9]
        reason = r[10]
        evidence = r[11] if r[11] is not None else []
        tx_hash = r[15]
        block_num = int(r[16]) if r[16] is not None else None
        chain_status = r[17] if r[17] else ("SIMULATED" if "SIMULATED" in (ev_status or "").upper() else "NOT_SUBMITTED")
        details_str = reason or f"Event {ev_type} recorded for {ent_type} {ent_id} by {act_id}."

        results.append(
            AuditEvent(
                event_id=event_id_str,
                eventId=event_id_str,
                event_type=ev_type,
                event=ev_type,
                type=ev_type,
                timestamp=ts_str,
                event_timestamp=ts_str,
                entity_type=ent_type,
                entity_id=ent_id,
                order_id=ord_id,
                orderId=ord_id,
                actor_type=r[7],
                actor_id=act_id,
                actor=act_id,
                status=ev_status,
                blockchain_status=chain_status,
                block_number=block_num,
                blockNumber=block_num,
                tx_hash=tx_hash,
                txHash=tx_hash,
                details=details_str,
                note=details_str,
                reason_code=reason,
                evidence_refs=evidence if isinstance(evidence, list) else [evidence],
                payload_hash=r[12],
                previous_event_hash=r[13],
                source_channel=r[14],
                scenario_id=str(r[5]) if r[5] else None,
                workflow_run_id=str(r[6]) if r[6] else None,
            )
        )
    return results


@router.get("/{event_id}", response_model=AuditEvent)
def get_audit_event_detail(event_id: str, conn=Depends(get_db)):
    """Retrieve detailed single audit event record by UUID."""
    try:
        val_uuid = uuid.UUID(event_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event_id UUID format: {event_id}",
        )

    sql = """
        SELECT
            el.event_id,
            el.event_timestamp,
            el.event_type,
            el.entity_type,
            el.entity_id,
            el.scenario_id,
            el.workflow_run_id,
            el.actor_type,
            el.actor_id,
            el.status,
            el.reason_code,
            el.evidence_refs,
            el.payload_hash,
            el.previous_event_hash,
            el.source_channel,
            ba.transaction_hash,
            ba.block_number,
            ba.confirmation_status,
            ba.verification_status
        FROM event_log el
        LEFT JOIN blockchain_anchors ba ON el.event_id::text = ba.event_id_or_batch_id
        WHERE el.event_id = %s;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (str(val_uuid),))
            r = cur.fetchone()
            if not r:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Audit event {event_id} not found",
                )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Database query failed in get_audit_event_detail: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query failed while retrieving audit event",
        ) from exc

    event_id_str = str(r[0])
    ts_str = r[1].isoformat() if r[1] else ""
    ev_type = r[2]
    ent_type = r[3]
    ent_id = r[4]
    ord_id = ent_id if ent_type == "ORDER" else None
    act_id = r[8]
    ev_status = r[9]
    reason = r[10]
    evidence = r[11] if r[11] is not None else []
    tx_hash = r[15]
    block_num = int(r[16]) if r[16] is not None else None
    chain_status = r[17] if r[17] else ("SIMULATED" if "SIMULATED" in (ev_status or "").upper() else "NOT_SUBMITTED")
    details_str = reason or f"Event {ev_type} recorded for {ent_type} {ent_id} by {act_id}."

    return AuditEvent(
        event_id=event_id_str,
        eventId=event_id_str,
        event_type=ev_type,
        event=ev_type,
        type=ev_type,
        timestamp=ts_str,
        event_timestamp=ts_str,
        entity_type=ent_type,
        entity_id=ent_id,
        order_id=ord_id,
        orderId=ord_id,
        actor_type=r[7],
        actor_id=act_id,
        actor=act_id,
        status=ev_status,
        blockchain_status=chain_status,
        block_number=block_num,
        blockNumber=block_num,
        tx_hash=tx_hash,
        txHash=tx_hash,
        details=details_str,
        note=details_str,
        reason_code=reason,
        evidence_refs=evidence if isinstance(evidence, list) else [evidence],
        payload_hash=r[12],
        previous_event_hash=r[13],
        source_channel=r[14],
        scenario_id=str(r[5]) if r[5] else None,
        workflow_run_id=str(r[6]) if r[6] else None,
    )
