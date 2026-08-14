from pydantic import BaseModel

class InventoryItem(BaseModel):
    id: str
    name: str
    quantity: int
    warehouse_id: str
