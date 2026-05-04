from pydantic import BaseModel, field_validator
from typing import Optional, Any, Dict
from datetime import datetime


class UpdateWebhookSchema(BaseModel):
    update_id: int
    update_type: str
    request_date: datetime

    payload: dict

class InvoicePayloadSchema(BaseModel):
    telegram_id: int
    tokens_count: int

class CryptoInvoiceSchema(BaseModel):
    invoice_id: int
    hash: str

    currency_type: str
    asset: str

    amount: float
    paid_asset: str
    paid_amount: float

    description: str
    status: str

    created_at: datetime
    paid_at: datetime

    paid_usd_rate: float
    usd_rate: float

    payload: InvoicePayloadSchema

    @field_validator('payload', mode='before')
    @classmethod
    def ensure_list(cls, value: Any) -> InvoicePayloadSchema:
        if isinstance(value, str):
            return InvoicePayloadSchema.model_validate_json(value)
        return InvoicePayloadSchema.model_validate(value)
