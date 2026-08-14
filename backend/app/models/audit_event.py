from pydantic import BaseModel
from datetime import datetime

class AuditEvent(BaseModel):
    order_id: str
    event_type: str
    event_hash: str
    timestamp: datetime
    actor: str
