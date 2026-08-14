from pydantic import BaseModel
from typing import Optional

class Order(BaseModel):
    id: str
    customer_id: str
    status: str
    total_amount: Optional[float] = None
