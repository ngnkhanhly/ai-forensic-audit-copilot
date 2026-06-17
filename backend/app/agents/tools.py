import json
import datetime
import re
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal
from backend.app.models import Document
from backend.app.services.vector_db import VectorDBService

def list_documents() -> str:
    """
    List all documents currently registered in the database, including their IDs, filenames, status, and document types.
    Use this to find the ID of a document when the user specifies a filename or asks general questions.
    """
    db = SessionLocal()
    try:
        docs = db.query(Document).all()
        if not docs:
            return "No documents found in the database."
        res = []
        for doc in docs:
            res.append(f"ID: {doc.id} | Filename: {doc.filename} | Type: {doc.document_type} | Status: {doc.status}")
        return "\n".join(res)
    finally:
        db.close()

def search_documents(query: str) -> str:
    """
    Search across all documents semantically using the vector database.
    Use this to find relevant clauses, specific terms, or statements in the documents.
    """
    vector_service = VectorDBService()
    hits = vector_service.search_similar_chunks(query, limit=5)
    
    db = SessionLocal()
    try:
        results = []
        for hit in hits:
            doc = db.query(Document).filter(Document.id == hit["document_id"]).first()
            filename = doc.filename if doc else f"Doc #{hit['document_id']}"
            results.append(f"Source: {filename} (ID: {hit['document_id']})\nContent: {hit['text']}\n")
        return "\n---\n".join(results) if results else "No matching document contents found."
    finally:
        db.close()

def extract_fields(document_id: int) -> str:
    """
    Get the structured fields (vendor, total, effective_date, parties, etc.) that were extracted from a document.
    """
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return f"Document ID {document_id} not found."
        return json.dumps({
            "id": doc.id,
            "filename": doc.filename,
            "document_type": doc.document_type,
            "extracted_data": doc.extracted_data
        }, indent=2)
    finally:
        db.close()

def validate_document(document_id: int) -> str:
    """
    Get the validation results, warnings, and business rule logs for a document.
    """
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return f"Document ID {document_id} not found."
        return json.dumps({
            "id": doc.id,
            "filename": doc.filename,
            "validation_status": doc.validation_status,
            "validation_logs": doc.validation_logs
        }, indent=2)
    finally:
        db.close()

def find_expiring_contracts(days: int = 30) -> str:
    """
    Find all contracts in the database that will expire within the specified number of days (or are already expired).
    """
    db = SessionLocal()
    try:
        contracts = db.query(Document).filter(Document.document_type == "contract").all()
        results = []
        today = datetime.date.today()
        
        for doc in contracts:
            if not doc.extracted_data:
                continue
            exp_date_str = doc.extracted_data.get("expiration_date")
            if exp_date_str:
                try:
                    date_match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", str(exp_date_str))
                    if date_match:
                        exp_date = datetime.date(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))
                        delta = (exp_date - today).days
                        if delta <= days:
                            results.append({
                                "id": doc.id,
                                "filename": doc.filename,
                                "parties": doc.extracted_data.get("parties", []),
                                "expiration_date": exp_date_str,
                                "days_remaining": delta
                            })
                except Exception:
                    pass
                    
        return json.dumps(results, indent=2) if results else f"No contracts expiring in the next {days} days."
    finally:
        db.close()

def generate_report(results_json_str: str) -> str:
    """
    Generates a beautifully formatted Markdown report summary from search or query results.
    Use this tool as a final step when the user requests a report.
    """
    try:
        data = json.loads(results_json_str)
    except Exception:
        # If it's not JSON, just wrap the text in report structure
        data = results_json_str
        
    report = "# Enterprise Document Intelligence Agent Report\n"
    report += f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    if isinstance(data, list):
        report += f"Found {len(data)} items matching query.\n\n"
        for idx, item in enumerate(data):
            report += f"### {idx+1}. {item.get('filename', 'Unknown Document')}\n"
            for k, v in item.items():
                if k != "filename":
                    report += f"- **{k.replace('_', ' ').title()}**: {v}\n"
            report += "\n"
    else:
        report += "## Summary of Findings\n\n"
        report += str(data)
        
    return report
