from pydantic import BaseModel, Field
from typing import List, Optional, Any, Union
from datetime import datetime

class ValidationLog(BaseModel):
    rule: str
    passed: bool
    message: str

class DocumentBase(BaseModel):
    filename: str

class DocumentResponse(DocumentBase):
    id: int
    file_path: str
    document_type: str
    status: str
    uploaded_at: datetime
    raw_text: Optional[str] = None
    extracted_data: Optional[dict] = None
    validation_status: str
    validation_logs: List[ValidationLog] = []
    risk_score: float = 0.0

    class Config:
        from_attributes = True

# Pydantic validation schemas for Structured Extraction
class InvoiceSchema(BaseModel):
    vendor: str = Field(description="Name of the vendor/seller issuing the invoice")
    invoice_id: str = Field(description="The unique invoice ID/number")
    date: str = Field(description="Date of invoice issue (YYYY-MM-DD or standard representation)")
    subtotal: float = Field(description="Subtotal amount before tax")
    tax: float = Field(description="Tax amount")
    total: float = Field(description="Total amount including tax")
    bank_account: Optional[str] = Field(None, description="The bank account number to receive payment if visible")

class ContractSchema(BaseModel):
    parties: List[str] = Field(description="Names of the parties involved in the contract")
    effective_date: str = Field(description="The start date/effective date of the contract")
    expiration_date: str = Field(description="The end/expiration date of the contract")
    payment_terms: str = Field(description="Details on payment schedule, duration, or conditions")
    risk_flags: List[str] = Field(description="Flags indicating potential legal or financial risks (e.g. indemnity, liability gaps)")
    bank_account: Optional[str] = Field(None, description="The registered bank account number if visible")

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    active_document_context: Optional[str] = None
    active_document_id: Optional[int] = None
