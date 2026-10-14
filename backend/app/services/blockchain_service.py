"""
Blockchain service — SIMULATION ONLY.

This module returns a locally-generated placeholder transaction hash.
No network connection is made, no smart contract is called, and no
transaction is submitted to any blockchain.

The return value MUST NOT be displayed as a confirmed or verified
on-chain transaction. Label it clearly as simulated in all callers
and in any API response that surfaces it to the UI.

Real blockchain integration is deferred to Phase 7.
"""


def record_on_chain(event_hash: str) -> dict:
    """
    Simulate recording an audit-event hash on-chain.

    Returns a dict with a clearly labelled placeholder transaction hash.
    The `status` field is 'SIMULATED' to prevent callers from treating
    this as a real on-chain confirmation.
    """
    print(f"[SIMULATION] Would record hash on blockchain: {event_hash}")
    return {
        "tx_hash": "0x0000000000000000000000000000000000000000000000000000000000000000",
        "status": "SIMULATED",
        "note": (
            "No blockchain transaction has been submitted. "
            "This is a placeholder pending Phase 7 real integration."
        ),
    }
