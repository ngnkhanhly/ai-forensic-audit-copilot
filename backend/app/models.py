from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
import datetime
from backend.app.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    file_path = Column(String)
    document_type = Column(String, default="unknown") # invoice, contract, receipt, po, payment_record
    status = Column(String, default="processing")
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    raw_text = Column(Text, nullable=True)
    extracted_data = Column(JSON, nullable=True)
    validation_status = Column(String, default="pending")
    validation_logs = Column(JSON, default=[])
    risk_score = Column(Float, default=0.0)

class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    normalized_name = Column(String, index=True)
    tax_id = Column(String, nullable=True)
    bank_account = Column(String, nullable=True)
    trust_score = Column(Float, default=100.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    contract_number = Column(String, index=True)
    total_value = Column(Float, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    expiration_date = Column(DateTime, nullable=True)
    payment_terms = Column(String, nullable=True) # e.g. "Net 30"
    
class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    invoice_number = Column(String, index=True)
    po_number = Column(String, nullable=True)
    issue_date = Column(DateTime, nullable=True)
    subtotal = Column(Float, nullable=True)
    tax = Column(Float, nullable=True)
    total_amount = Column(Float, nullable=True)
    payment_terms = Column(String, nullable=True)

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    po_number = Column(String, index=True)
    total_amount = Column(Float, nullable=True)
    status = Column(String, default="open")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    amount = Column(Float)
    payment_date = Column(DateTime)
    bank_account_used = Column(String)

class ExtractedField(Base):
    __tablename__ = "extracted_fields"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    field_name = Column(String)
    field_value = Column(String)
    confidence = Column(Float)

class ValidationResult(Base):
    __tablename__ = "validation_results"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    rule_name = Column(String)
    passed = Column(Boolean)
    message = Column(Text)

class RiskCase(Base):
    __tablename__ = "risk_cases"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String, unique=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    risk_score = Column(Float)
    risk_level = Column(String) # LOW, MEDIUM, HIGH, CRITICAL
    risk_type = Column(String)
    financial_exposure = Column(Float)
    recommendation = Column(Text)
    review_status = Column(String, default="PENDING_REVIEW") # PENDING_REVIEW, APPROVED, REJECTED, BLOCKED, NEED_MORE_INFO
    reviewer_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class RiskEvidence(Base):
    __tablename__ = "risk_evidence"
    id = Column(Integer, primary_key=True, index=True)
    risk_case_id = Column(Integer, ForeignKey("risk_cases.id"))
    evidence_json = Column(JSON) # Stores specific rule hits and comparisons

class ReviewTask(Base):
    __tablename__ = "review_tasks"
    id = Column(Integer, primary_key=True, index=True)
    risk_case_id = Column(Integer, ForeignKey("risk_cases.id"))
    assigned_to = Column(String, nullable=True)
    status = Column(String, default="OPEN")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String) # invoice, contract, risk_case
    entity_id = Column(Integer)
    action = Column(String) # CREATE, UPDATE, APPROVE, REJECT
    performed_by = Column(String, default="SYSTEM")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    details = Column(JSON)
