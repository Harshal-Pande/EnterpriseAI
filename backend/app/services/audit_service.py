"""
Starter implementation for audit services.
"""
def log_audit_event(order_id: str, event_type: str):
    print(f"Logging audit event {event_type} for {order_id}")
    return True
