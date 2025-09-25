from pydantic import BaseModel

class Transaction(BaseModel):
    id: str
    kind: str
    gateway: str
    parent_transaction_id: str