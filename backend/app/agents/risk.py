from openai import OpenAI
from typing import Dict, Any, List
from backend.app.config import settings
from backend.app.schemas import RiskDetectionOutput

def run_risk_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent node to analyze contract clauses and full text for risks, assigning severity and numerical risk scores.
    """
    contract_text = state.get("contract_text", "")
    extracted_clauses = state.get("extracted_clauses", [])
    
    if not contract_text:
        return {"errors": state.get("errors", []) + ["No contract text found for risk analysis"]}

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    # Format extracted clauses for LLM context
    clauses_formatted = "\n".join([
        f"- {c['clause_type']}: {c['text']}" for c in extracted_clauses
    ])
    
    prompt = f"""
    You are an expert legal risk assessor. Review the following contract and its extracted clauses.
    Identify all potential risks, such as:
    - Unusually high penalties or violation charges
    - Extremely long payment terms (e.g. net 60/90 days)
    - One-sided termination clauses
    - Unlimited liability or lack of limitations of liability
    - Hostile governing law
    
    For each risk, provide:
    1. Risk category (e.g., Liability, Payment, Termination, Confidentiality, Governing Law, Other)
    2. Detailed description of why this is a risk for the client.
    3. Severity (low, medium, high).
    4. Risk Score (a number between 0 and 100, where 0 is no risk and 100 is catastrophic risk).
       - High severity risks should have a score between 70-100.
       - Medium severity risks between 40-69.
       - Low severity risks between 0-39.
    5. Evidence text: Quote or specific sentence from the contract text representing this risk.

    Extracted Key Clauses:
    {clauses_formatted}

    Full Contract Text:
    {contract_text}
    """

    try:
        completion = client.beta.chat.completions.parse(
            model=settings.DEFAULT_LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional legal risk detection system."},
                {"role": "user", "content": prompt}
            ],
            response_format=RiskDetectionOutput
        )
        result = completion.choices[0].message.parsed
        
        detected_risks = [
            {
                "risk_category": risk.risk_category,
                "description": risk.description,
                "severity": risk.severity.value,
                "risk_score": risk.risk_score,
                "evidence_text": risk.evidence_text
            }
            for risk in result.risks
        ]
        
        return {"detected_risks": detected_risks}
    except Exception as e:
        return {"errors": state.get("errors", []) + [f"Risk Agent error: {str(e)}"]}
