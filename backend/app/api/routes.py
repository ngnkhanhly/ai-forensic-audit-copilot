import os
import json
import datetime
import re
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from backend.app.database import get_db
from backend.app import models, schemas
from backend.app.services.ocr import perform_ocr
from backend.app.services.chunker import chunk_text
from backend.app.services.vector_db import VectorDBService
from backend.app.services.extractor import classify_document, extract_structured_data, validate_document
from backend.app.services.comparison import compare_contracts_logic

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Directory to save uploads
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def safe_parse_date(date_str: Any) -> datetime.datetime:
    if not date_str:
        return None
    try:
        # Match YYYY-MM-DD
        match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", str(date_str))
        if match:
            return datetime.datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except Exception:
        pass
    return None

def normalize_vendor_name(name: str) -> str:
    if not name:
        return ""
    name_clean = name.lower().strip()
    name_clean = re.sub(r"[^\w\s]", "", name_clean)
    name_clean = re.sub(r"\b(llc|inc|co|corp|corporation|company|ltd|limited|trading)\b", "", name_clean)
    return " ".join(name_clean.split())

def populate_relational_data(
    doc: models.Document,
    extracted: Dict[str, Any],
    val_status: str,
    val_logs: List[Dict[str, Any]],
    db: Session
):
    """
    Populates relational tables (Vendor, Invoice, Contract, ExtractedField, ValidationResult)
    based on the analysis results of the document.
    """
    try:
        vendor_name = ""
        if doc.document_type in ["invoice", "receipt"]:
            vendor_name = extracted.get("vendor", "")
        elif doc.document_type == "contract":
            parties = extracted.get("parties", [])
            if isinstance(parties, list) and len(parties) > 0:
                vendor_name = parties[-1] if len(parties) > 1 else parties[0]
            else:
                vendor_name = "Unknown Vendor"

        vendor_name = str(vendor_name).strip()
        if not vendor_name:
            vendor_name = "Unknown Vendor"

        normalized_name = normalize_vendor_name(vendor_name)
        
        vendor = db.query(models.Vendor).filter(models.Vendor.normalized_name == normalized_name).first()
        bank_acc = str(extracted.get("bank_account") or "").strip()
        if not vendor:
            vendor = models.Vendor(
                name=vendor_name,
                normalized_name=normalized_name,
                tax_id=extracted.get("tax_id") if isinstance(extracted, dict) else None,
                bank_account=bank_acc,
                trust_score=100.0
            )
            db.add(vendor)
            db.flush()
        else:
            if bank_acc and not vendor.bank_account:
                vendor.bank_account = bank_acc

        if doc.document_type in ["invoice", "receipt"]:
            invoice_num = extracted.get("invoice_id") or extracted.get("invoice_number", f"INV-GEN-{doc.id}")
            invoice = db.query(models.Invoice).filter(models.Invoice.document_id == doc.id).first()
            if not invoice:
                subtotal = float(extracted.get("subtotal") or 0.0)
                tax = float(extracted.get("tax") or 0.0)
                total = float(extracted.get("total") or 0.0)
                
                invoice = models.Invoice(
                    document_id=doc.id,
                    vendor_id=vendor.id,
                    invoice_number=str(invoice_num),
                    po_number=extracted.get("po_reference") or extracted.get("po_number"),
                    issue_date=safe_parse_date(extracted.get("date")),
                    subtotal=subtotal,
                    tax=tax,
                    total_amount=total,
                    payment_terms=extracted.get("payment_terms")
                )
                db.add(invoice)

        elif doc.document_type == "contract":
            contract = db.query(models.Contract).filter(models.Contract.document_id == doc.id).first()
            if not contract:
                contract = models.Contract(
                    document_id=doc.id,
                    vendor_id=vendor.id,
                    contract_number=extracted.get("contract_number", doc.filename),
                    total_value=float(extracted.get("total_value") or 0.0),
                    effective_date=safe_parse_date(extracted.get("effective_date")),
                    expiration_date=safe_parse_date(extracted.get("expiration_date")),
                    payment_terms=extracted.get("payment_terms")
                )
                db.add(contract)

        db.query(models.ExtractedField).filter(models.ExtractedField.document_id == doc.id).delete()
        for k, v in extracted.items():
            if isinstance(v, (list, dict)):
                val_str = json.dumps(v)
            else:
                val_str = str(v) if v is not None else ""
            
            field_record = models.ExtractedField(
                document_id=doc.id,
                field_name=k,
                field_value=val_str,
                confidence=1.0
            )
            db.add(field_record)

        db.query(models.ValidationResult).filter(models.ValidationResult.document_id == doc.id).delete()
        for log in val_logs:
            rule_name = log.get("rule", "unknown")
            passed = bool(log.get("passed", True))
            msg = log.get("message", "")
            
            val_record = models.ValidationResult(
                document_id=doc.id,
                rule_name=rule_name,
                passed=passed,
                message=msg
            )
            db.add(val_record)

        db.flush()
    except Exception as e:
        print(f"Error populating relational data: {e}")
        raise e

def run_cross_document_audit(doc: models.Document, extracted: Dict[str, Any], val_logs: List[Dict[str, Any]], db: Session):
    if doc.document_type in ["invoice", "receipt"]:
        vendor_name = extracted.get("vendor", "")
        normalized_name = normalize_vendor_name(vendor_name)
        
        vendor = db.query(models.Vendor).filter(models.Vendor.normalized_name == normalized_name).first()
        if vendor:
            contract = db.query(models.Contract).filter(models.Contract.vendor_id == vendor.id).first()
            
            # Check Bank Account Takeover Risk
            inv_bank = re.sub(r"\D", "", str(extracted.get("bank_account") or ""))
            con_bank = re.sub(r"\D", "", str(vendor.bank_account or ""))
            if inv_bank and con_bank and inv_bank != con_bank:
                val_logs.append({
                    "rule": "contract_bank_account_mismatch",
                    "passed": False,
                    "message": f"Bank Account Takeover Risk: Invoice bank account ({inv_bank}) does not match registered vendor account ({con_bank})."
                })
            elif inv_bank and con_bank:
                val_logs.append({
                    "rule": "contract_bank_account_mismatch",
                    "passed": True,
                    "message": "Bank account matches registered vendor profile."
                })
                
            if contract:
                # Check Payment Term Mismatch
                inv_terms = extracted.get("payment_terms")
                con_terms = contract.payment_terms
                if inv_terms and con_terms and normalize_vendor_name(str(inv_terms)) != normalize_vendor_name(str(con_terms)):
                    val_logs.append({
                        "rule": "contract_payment_term_mismatch",
                        "passed": False,
                        "message": f"Contract Mismatch: Invoice payment terms ({inv_terms}) violate contract terms ({con_terms})."
                    })
                elif inv_terms and con_terms:
                    val_logs.append({
                        "rule": "contract_payment_term_mismatch",
                        "passed": True,
                        "message": "Invoice payment terms match contract terms."
                    })

def calculate_weighted_risk_score(doc: models.Document, extracted: Dict[str, Any], val_logs: List[Dict[str, Any]], db: Session) -> float:
    duplicate_risk = 0.0
    contract_mismatch_risk = 0.0
    amount_anomaly_risk = 0.0
    vendor_risk = 0.0
    missing_fields_risk = 0.0
    confidence_penalty = 0.0

    for log in val_logs:
        rule = log.get("rule", "")
        passed = log.get("passed", True)
        
        if not passed:
            if rule == "duplicate_check":
                duplicate_risk = 100.0
            elif rule in ["contract_payment_term_mismatch", "contract_bank_account_mismatch"]:
                contract_mismatch_risk = 100.0
            elif rule == "subtotal_tax_total":
                amount_anomaly_risk = 100.0
            elif rule == "missing_required_fields":
                missing_fields_risk = 100.0
            elif rule in ["expiration_check", "risk_flags_check"]:
                contract_mismatch_risk = 50.0

    vendor_name = extracted.get("vendor", "") if doc.document_type in ["invoice", "receipt"] else ""
    if doc.document_type == "contract":
        parties = extracted.get("parties", [])
        if isinstance(parties, list) and len(parties) > 0:
            vendor_name = parties[-1] if len(parties) > 1 else parties[0]
            
    if vendor_name:
        normalized_name = normalize_vendor_name(vendor_name)
        vendor = db.query(models.Vendor).filter(models.Vendor.normalized_name == normalized_name).first()
        if not vendor:
            vendor_risk = 50.0
        elif vendor.trust_score < 70.0:
            vendor_risk = 100.0

    confidence_penalty = 10.0

    score = (
        (0.35 * duplicate_risk) +
        (0.25 * contract_mismatch_risk) +
        (0.15 * amount_anomaly_risk) +
        (0.10 * vendor_risk) +
        (0.10 * missing_fields_risk) +
        (0.05 * confidence_penalty)
    )
    return float(max(0.0, min(100.0, score)))

def run_document_analysis_task(doc_id: int, file_path: str, db_session_factory):
    """
    Background worker task to run OCR, Classify, Extract, Validate, and Vectorize.
    Uses its own DB session to avoid sharing session across threads.
    """
    db: Session = db_session_factory()
    try:
        doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
        if not doc:
            return

        # 1. OCR Layer
        raw_text = perform_ocr(file_path)
        doc.raw_text = raw_text
        db.commit()

        # 2. Classification
        doc_type = classify_document(raw_text)
        doc.document_type = doc_type
        db.commit()

        # 3. Structured Extraction
        extracted = extract_structured_data(raw_text, doc_type)
        doc.extracted_data = extracted
        db.commit()

        # 4. Validation
        # Pass doc_id to db.info for duplicate check exclusion
        db.info["current_doc_id"] = doc_id
        val_status, val_logs = validate_document(extracted, doc_type, db)
        
        # 5. Cross-Document Auditing
        run_cross_document_audit(doc, extracted, val_logs, db)
        
        # 6. Calculate Weighted Risk Score
        risk_score = calculate_weighted_risk_score(doc, extracted, val_logs, db)
        doc.risk_score = risk_score
        
        # Map score to final validation status
        if risk_score >= 86.0:
            val_status = "invalid"  # Critical / Blocked
        elif risk_score >= 31.0:
            val_status = "warning"  # Warning
        else:
            val_status = "valid"    # Valid / Low Risk
            
        doc.validation_status = val_status
        doc.validation_logs = val_logs
        db.commit()

        # 7. Populate Normalized Relational Tables
        populate_relational_data(doc, extracted, val_status, val_logs, db)
        db.commit()

        # 5. Vector database indexing (Qdrant)
        if raw_text and len(raw_text.strip()) > 0:
            chunks = chunk_text(raw_text)
            vector_service = VectorDBService()
            vector_service.index_chunks(doc_id, chunks)

        doc.status = "completed"
        db.commit()
    except Exception as e:
        db.rollback()
        doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
        if doc:
            doc.status = "failed"
            doc.validation_status = "invalid"
            doc.validation_logs = [{"rule": "system_pipeline", "passed": False, "message": f"Pipeline error: {str(e)}"}]
            db.commit()
        print(f"Background task failed for document {doc_id}: {str(e)}")
    finally:
        db.close()


@router.post("/upload", response_model=schemas.DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Endpoint to upload PDF or image documents, classify them, extract fields, validate them, and index for RAG.
    """
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".pdf", ".png", ".jpg", ".jpeg", ".webp"]:
        raise HTTPException(status_code=400, detail="Unsupported file format. Use PDF or images (PNG, JPG, WEBP).")

    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Create Document record
    doc = models.Document(
        filename=filename,
        file_path=file_path,
        document_type="unknown",
        status="processing",
        validation_status="pending",
        validation_logs=[]
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Trigger async background pipeline execution
    from backend.app.database import SessionLocal
    background_tasks.add_task(run_document_analysis_task, doc.id, file_path, SessionLocal)

    return doc


@router.get("/", response_model=List[schemas.DocumentResponse])
def get_all_documents(db: Session = Depends(get_db)):
    """
    Fetch all documents.
    """
    return db.query(models.Document).all()


@router.get("/{doc_id}", response_model=schemas.DocumentResponse)
def get_document_by_id(doc_id: int, db: Session = Depends(get_db)):
    """
    Fetch a single document processing result.
    """
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    """
    Delete a document.
    """
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    # Try deleting actual file
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass
            
    # Delete from Qdrant vector database
    try:
        vector_service = VectorDBService()
        vector_service.delete_document_vectors(doc_id)
    except Exception as e:
        print(f"Failed to delete vector database chunks for doc {doc_id}: {e}")

    db.delete(doc)
    db.commit()
    return {"message": "Document successfully deleted."}


@router.post("/chat")
def chat_rag(request: schemas.ChatRequest, db: Session = Depends(get_db)):
    """
    Direct RAG Question Answering endpoint using Qdrant vector retrieval and Gemini.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list is empty.")
        
    user_query = request.messages[-1].content
    
    # Search similar text from Qdrant
    vector_service = VectorDBService()
    hits = vector_service.search_similar_chunks(user_query, limit=5)
    
    context = ""
    for idx, hit in enumerate(hits):
        doc_info = ""
        doc = db.query(models.Document).filter(models.Document.id == hit["document_id"]).first()
        if doc:
            doc_info = f" (Source File: {doc.filename})"
        context += f"Chunk {idx+1}{doc_info}:\n{hit['text']}\n\n"
        
    # Standard prompt for QA
    system_prompt = (
        "You are an Enterprise Document Intelligence QA bot. Use the retrieved context below to answer "
        "the user's questions about invoices, contracts, receipts, etc. "
        "If the answer cannot be found in the context, clearly state that you don't know based on the documents.\n\n"
        f"Retrieved Document Context:\n{context or 'No matching document context found.'}\n"
    )
    
    from openai import OpenAI
    from backend.app.config import settings
    
    try:
        openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        messages_payload = [
            {"role": "system", "content": system_prompt}
        ]
        # Append history
        for msg in request.messages[:-1]:
            role_map = {"user": "user", "assistant": "assistant", "model": "assistant"}
            messages_payload.append({
                "role": role_map.get(msg.role, "user"),
                "content": msg.content
            })
        # Append user query
        messages_payload.append({"role": "user", "content": user_query})
        
        response = openai_client.chat.completions.create(
            model=settings.DEFAULT_LLM_MODEL,
            messages=messages_payload,
            temperature=0.0
        )
        return {"answer": response.choices[0].message.content, "sources": [{"document_id": h["document_id"], "score": h["score"]} for h in hits]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QA failed: {str(e)}")

from backend.app.agents.graph import run_document_agent

@router.post("/agent")
def execute_agent(request: schemas.ChatRequest, db: Session = Depends(get_db)):
    """
    Endpoint to run the LangGraph Document Intelligence Agent workflow.
    """
    chat_history = []
    if request.active_document_id:
        doc = db.query(models.Document).filter(models.Document.id == request.active_document_id).first()
        if doc:
            chat_history.append({
                "role": "user",
                "content": f"[Context] The active document is ID: {doc.id}, Filename: {doc.filename}, Type: {doc.document_type}. If I ask about 'this contract', 'this invoice', 'the document', or anything without specifying a filename, I am referring to this file. You MUST use ID {doc.id} directly with tools."
            })
            chat_history.append({
                "role": "assistant",
                "content": f"Understood. I have locked my focus on '{doc.filename}' (ID: {doc.id}) as the active context."
            })
    elif request.active_document_context:
        chat_history.append({
            "role": "user",
            "content": f"[Context] I am currently inspecting this document: {request.active_document_context}. If I ask about 'this contract', 'this invoice', 'the document', or anything without specifying a filename, I am referring to this file. I do not need to type the filename."
        })
        chat_history.append({
            "role": "assistant",
            "content": f"Understood. I have locked my focus on '{request.active_document_context}' as the active context."
        })
        
    for msg in request.messages:
        chat_history.append({"role": msg.role, "content": msg.content})
        
    try:
        answer = run_document_agent(chat_history)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent workflow execution failed: {str(e)}")

@router.post("/compare")
def compare_documents(payload: Dict[str, int], db: Session = Depends(get_db)):
    """
    Compares two contracts (version 1 and version 2) and returns structured analysis.
    """
    doc_id_v1 = payload.get("doc_id_v1")
    doc_id_v2 = payload.get("doc_id_v2")
    if not doc_id_v1 or not doc_id_v2:
        raise HTTPException(status_code=400, detail="Missing doc_id_v1 or doc_id_v2.")
        
    doc_v1 = db.query(models.Document).filter(models.Document.id == doc_id_v1).first()
    doc_v2 = db.query(models.Document).filter(models.Document.id == doc_id_v2).first()
    
    if not doc_v1 or not doc_v2:
        raise HTTPException(status_code=404, detail="One or both documents not found.")
        
    # Calculate a mock/basic risk score based on warnings or flags to pass to the comparator
    def compute_score(doc):
        score = 85 # baseline
        if doc.validation_logs:
            for log in doc.validation_logs:
                if isinstance(log, dict):
                    passed = log.get("passed", True)
                else:
                    passed = getattr(log, "passed", True)
                if not passed:
                    score -= 10
        return max(30, score)
        
    score_v1 = compute_score(doc_v1)
    score_v2 = compute_score(doc_v2)
    
    comparison = compare_contracts_logic(
        filename_v1=doc_v1.filename,
        filename_v2=doc_v2.filename,
        text_v1=doc_v1.raw_text or "",
        text_v2=doc_v2.raw_text or "",
        v1_score=score_v1,
        v2_score=score_v2
    )
    return comparison
