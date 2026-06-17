import os
import json
import datetime
import re
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from openai import OpenAI
from backend.app.config import settings
from backend.app.models import Document
from backend.app.schemas import InvoiceSchema, ContractSchema

# Initialize OpenAI client
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

def classify_document(text: str) -> str:
    """
    Classifies the document text into invoice, contract, receipt, or unknown.
    """
    if not text or len(text.strip()) < 10:
        return "unknown"
        
    try:
        response = openai_client.chat.completions.create(
            model=settings.DEFAULT_LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert document classifier. Categorize the following text into exactly one of these types: 'invoice', 'contract', 'receipt', or 'unknown'."},
                {"role": "user", "content": f"Document Text:\n{text[:4000]}"}
            ],
            temperature=0.0
        )
        label = response.choices[0].message.content.strip().lower()
        
        # Clean label
        for possible in ["invoice", "contract", "receipt"]:
            if possible in label:
                return possible
        return "unknown"
    except Exception as e:
        print(f"Classification failed: {e}")
        # Rule-based fallback
        text_lower = text.lower()
        if "invoice" in text_lower or "invoice number" in text_lower or "bill to" in text_lower:
            return "invoice"
        elif "contract" in text_lower or "agreement" in text_lower or "parties" in text_lower:
            return "contract"
        elif "receipt" in text_lower or "cashier" in text_lower or "total amount" in text_lower:
            return "receipt"
        return "unknown"

def extract_structured_data(text: str, document_type: str) -> Dict[str, Any]:
    """
    Extracts structured data from the document text based on its classified type using OpenAI's structured outputs.
    """
    if document_type == "unknown":
        return {}
        
    try:
        if document_type in ["invoice", "receipt"]:
            schema = InvoiceSchema
            prompt = (
                "Extract structured data from the following receipt/invoice text. "
                "Ensure amounts are extracted as float numbers. Dates should be in YYYY-MM-DD format if possible."
            )
        elif document_type == "contract":
            schema = ContractSchema
            prompt = (
                "Extract structured data from the following contract text. "
                "Identify parties, effective and expiration dates (in YYYY-MM-DD if possible), "
                "payment terms, and highlight any risk flags or severe termination clauses."
            )
        else:
            return {}

        response = openai_client.beta.chat.completions.parse(
            model=settings.DEFAULT_LLM_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text[:8000]}
            ],
            response_format=schema,
            temperature=0.0
        )
        # The parsed output can be converted to dict directly via Pydantic model
        parsed = response.choices[0].message.parsed
        if parsed:
            # Pydantic v2 use model_dump()
            return parsed.model_dump()
        return {}
    except Exception as e:
        print(f"Structured extraction failed: {e}")
        # Fallback empty schemas
        if document_type in ["invoice", "receipt"]:
            return {"vendor": "", "invoice_id": "", "date": "", "subtotal": 0.0, "tax": 0.0, "total": 0.0}
        else:
            return {"parties": [], "effective_date": "", "expiration_date": "", "payment_terms": "", "risk_flags": []}

def validate_document(extracted_data: Dict[str, Any], document_type: str, db: Session) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Validates the extracted data according to the business rules.
    Returns: (validation_status: "valid"|"invalid"|"warning", validation_logs: List[Dict])
    """
    logs = []
    status = "valid"
    
    if document_type in ["invoice", "receipt"]:
        subtotal = float(extracted_data.get("subtotal") or 0.0)
        tax = float(extracted_data.get("tax") or 0.0)
        total = float(extracted_data.get("total") or 0.0)
        invoice_id = str(extracted_data.get("invoice_id") or "").strip()
        vendor = str(extracted_data.get("vendor") or "").strip()
        
        # 1. Total check: subtotal + tax == total (allow minor tolerance)
        diff = abs((subtotal + tax) - total)
        if diff > 1.0:
            status = "invalid"
            logs.append({
                "rule": "subtotal_tax_total",
                "passed": False,
                "message": f"Calculation mismatch: Subtotal ({subtotal}) + Tax ({tax}) = {subtotal + tax}, which differs from Total ({total}) by {diff:.2f}"
            })
        else:
            logs.append({
                "rule": "subtotal_tax_total",
                "passed": True,
                "message": f"Calculation matches: Subtotal ({subtotal}) + Tax ({tax}) = Total ({total})"
            })
            
        # 2. Duplicate invoice ID check
        if invoice_id:
            duplicate = db.query(Document).filter(
                Document.document_type.in_(["invoice", "receipt"]),
                Document.id != db.info.get("current_doc_id", -1) # Exclude current document if saving/updating
            ).all()
            
            is_dup = False
            for doc in duplicate:
                if doc.extracted_data and str(doc.extracted_data.get("invoice_id")).strip() == invoice_id:
                    is_dup = True
                    break
                    
            if is_dup:
                if status == "valid": 
                    status = "warning"
                logs.append({
                    "rule": "duplicate_check",
                    "passed": False,
                    "message": f"Duplicate Invoice Warning: Invoice ID '{invoice_id}' already exists in database."
                })
            else:
                logs.append({
                    "rule": "duplicate_check",
                    "passed": True,
                    "message": "Unique Invoice ID verified."
                })
        else:
            status = "invalid"
            logs.append({
                "rule": "duplicate_check",
                "passed": False,
                "message": "Invoice ID is missing or empty."
            })
            
        # 3. Missing required fields
        if not vendor:
            status = "invalid"
            logs.append({
                "rule": "missing_required_fields",
                "passed": False,
                "message": "Vendor name is missing or empty."
            })
        else:
            logs.append({
                "rule": "missing_required_fields",
                "passed": True,
                "message": "Required fields (Vendor) are populated."
            })

    elif document_type == "contract":
        expiration_date_str = str(extracted_data.get("expiration_date") or "").strip()
        risk_flags = extracted_data.get("risk_flags") or []
        
        # 1. Expiry Check: Check if expiring in 30 days
        if expiration_date_str:
            try:
                # Attempt to parse date in YYYY-MM-DD or similar standard format
                # Using regex to extract YYYY-MM-DD
                date_match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", expiration_date_str)
                if date_match:
                    exp_date = datetime.date(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))
                    today = datetime.date.today()
                    delta = (exp_date - today).days
                    
                    if 0 <= delta <= 30:
                        status = "warning"
                        logs.append({
                            "rule": "expiration_check",
                            "passed": False,
                            "message": f"Contract is expiring soon: Expiration Date is {expiration_date_str} ({delta} days remaining)."
                        })
                    elif delta < 0:
                        status = "invalid"
                        logs.append({
                            "rule": "expiration_check",
                            "passed": False,
                            "message": f"Contract has expired: Expiration Date was {expiration_date_str} (expired {-delta} days ago)."
                        })
                    else:
                        logs.append({
                            "rule": "expiration_check",
                            "passed": True,
                            "message": f"Contract active: Expiration Date is {expiration_date_str} ({delta} days remaining)."
                        })
                else:
                    logs.append({
                        "rule": "expiration_check",
                        "passed": False,
                        "message": f"Could not parse expiration date format: '{expiration_date_str}'"
                    })
            except Exception as e:
                logs.append({
                    "rule": "expiration_check",
                    "passed": False,
                    "message": f"Error parsing expiration date: {e}"
                })
        else:
            status = "warning"
            logs.append({
                "rule": "expiration_check",
                "passed": False,
                "message": "Expiration date is not specified in the contract."
            })
            
        # 2. Risky clause flags
        if risk_flags:
            status = "warning"
            logs.append({
                "rule": "risk_flags_check",
                "passed": False,
                "message": f"Risky clauses detected: {', '.join(risk_flags)}"
            })
        else:
            logs.append({
                "rule": "risk_flags_check",
                "passed": True,
                "message": "No risky clauses or risk flags were flagged."
            })
            
    else:
        status = "valid"
        logs.append({
            "rule": "generic_check",
            "passed": True,
            "message": "Document classification unknown, skipping validation rules."
        })
        
    return status, logs
