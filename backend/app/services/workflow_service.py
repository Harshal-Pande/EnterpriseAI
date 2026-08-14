"""
Starter implementation for workflow management services.
"""
def trigger_workflow(order_id: str):
    print(f"Triggering workflow for {order_id}")
    return {"status": "started", "workflow_id": f"WF-{order_id}"}
