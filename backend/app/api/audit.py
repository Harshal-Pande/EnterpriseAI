from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def get_audit_trail():
    """
    Stub audit-trail endpoint.

    Returns a single hardcoded sample event for development scaffolding.
    The `tx_hash` field is intentionally absent; `blockchain_status` is
    set to 'SIMULATED' so callers never treat this as a confirmed
    on-chain record.

    Real audit-trail data backed by PostgreSQL is implemented in Phase 2.
    Blockchain anchoring (real transaction hashes and receipts) is
    implemented in Phase 7.
    """
    return [
        {
            "event": "ORDER_RECEIVED",
            "timestamp": "2026-08-09T16:42:08Z",
            "blockchain_status": "SIMULATED",
            "note": (
                "No blockchain transaction has been submitted. "
                "This record is a development stub pending Phase 2/7 integration."
            ),
        }
    ]
