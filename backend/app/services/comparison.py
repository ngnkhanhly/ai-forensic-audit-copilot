from openai import OpenAI
from typing import Dict, Any, List
from pydantic import BaseModel
from backend.app.config import settings

class ClauseComparisonItem(BaseModel):
    clause_type: str
    change_type: str # Added, Removed, Modified, Unchanged
    description: str # Detail of what changed (e.g. Net 30 days to Net 90 days)
    v1_summary: str  # Summarized text of clause in V1
    v2_summary: str  # Summarized text of clause in V2

class RiskComparisonItem(BaseModel):
    risk_category: str
    change_description: str # Detail of the risk change
    impact: str # Increased, Decreased, Neutral

class ContractComparisonResult(BaseModel):
    overall_summary: str
    score_change_explanation: str
    clause_changes: List[ClauseComparisonItem]
    risk_changes: List[RiskComparisonItem]

def compare_contracts_logic(
    filename_v1: str,
    filename_v2: str,
    text_v1: str,
    text_v2: str,
    v1_score: int,
    v2_score: int
) -> Dict[str, Any]:
    """
    Compares two versions of a contract using OpenAI Structured Outputs.
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    prompt = f"""
    You are an expert contract auditor comparing two versions of a contract.
    
    Version 1: {filename_v1} (Risk Score: {v1_score})
    Version 2: {filename_v2} (Risk Score: {v2_score})
    
    Please perform a detailed comparison. Look for changes in:
    1. Payment Terms
    2. Termination
    3. Confidentiality
    4. Liability
    5. Governing Law
    
    Compare the text of both versions, analyze how the risk has shifted, and explain why the score changed from {v1_score} to {v2_score}.

    Version 1 Text (Snippet or Full):
    {text_v1[:10000]} # Limit to first 10k chars to avoid token flood, typical for standard contracts
    
    Version 2 Text (Snippet or Full):
    {text_v2[:10000]}
    """
    
    try:
        completion = client.beta.chat.completions.parse(
            model=settings.DEFAULT_LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional contract comparison analyst."},
                {"role": "user", "content": prompt}
            ],
            response_format=ContractComparisonResult
        )
        result = completion.choices[0].message.parsed
        
        # Build dictionary from structured output
        return {
            "v1_filename": filename_v1,
            "v2_filename": filename_v2,
            "v1_score": v1_score,
            "v2_score": v2_score,
            "score_diff": v2_score - v1_score,
            "overall_summary": result.overall_summary,
            "score_change_explanation": result.score_change_explanation,
            "clause_changes": [
                {
                    "clause_type": item.clause_type,
                    "change_type": item.change_type,
                    "description": item.description,
                    "v1_summary": item.v1_summary,
                    "v2_summary": item.v2_summary
                }
                for item in result.clause_changes
            ],
            "risk_changes": [
                {
                    "risk_category": item.risk_category,
                    "change_description": item.change_description,
                    "impact": item.impact
                }
                for item in result.risk_changes
            ]
        }
    except Exception as e:
        return {
            "error": f"Failed to compare contracts: {str(e)}",
            "v1_filename": filename_v1,
            "v2_filename": filename_v2,
            "v1_score": v1_score,
            "v2_score": v2_score,
            "score_diff": v2_score - v1_score,
            "overall_summary": "Failed to generate AI comparison summary.",
            "score_change_explanation": "An error occurred during LLM analysis.",
            "clause_changes": [],
            "risk_changes": []
        }
