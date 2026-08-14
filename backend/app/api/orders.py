from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def list_orders():
    # Starter implementation
    return [{"id": "ORD-1042", "status": "processing"}]

@router.post("/")
def create_order(order_data: dict):
    # Starter implementation
    return {"status": "created", "order_id": "ORD-1043"}
