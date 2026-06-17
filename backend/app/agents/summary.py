from openai import OpenAI
from typing import Dict, Any, List
from backend.app.config import settings
from backend.app.schemas import ExecutiveSummaryOutput

def run_summary_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent node to synthesize clauses, risks, and evidence into an Executive Summary
    including a numerical overall risk score (0-100) and top action items.
    """
    contract_text = state.get("contract_text", "")
    extracted_clauses = state.get("extracted_clauses", [])
    detected_risks = state.get("detected_risks", [])
    
    if not contract_text:
        return {"errors": state.get("errors", []) + ["No contract text found for summary"]}

    # Compute a default baseline score if no risks are found
    if not detected_risks:
        return {
            "executive_summary": {
                "overall_risk_level": "low",
                "overall_risk_score": 10,
                "top_3_risks": ["No significant risks identified."],
                "top_2_negotiations": ["No urgent negotiation needed."]
            }
        }

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    # Format risks and clauses for LLM context
    risks_formatted = "\n".join([
        f"- [{r['severity'].upper()} - Score: {r['risk_score']}] {r['risk_category']}: {r['description']}"
        for r in detected_risks
    ])
    clauses_formatted = "\n".join([
        f"- {c['clause_type']}: {c['text']}" for c in extracted_clauses
    ])
    
    prompt = f"""
    You are an executive legal advisor. Review the extracted clauses and identified risks below:
    
    Extracted Clauses:
    {clauses_formatted}
    
    Identified Risks:
    {risks_formatted}
    
    Synthesize this information and output a structured report containing:
    1. Overall risk level (low, medium, high).
    2. Overall risk score (a number from 0 to 100 representing the total risk exposure of this contract).
    3. Top 3 most critical risks.
    4. Top 2 specific negotiation recommendations (what the client should ask to modify).

    Ensure your overall risk score and level are logically aligned with the severities of the detected risks.
    For example:
    - If there are High severity risks, the overall score should generally be 70 or above, and level should be 'high'.
    - If there are mostly Medium severity risks, the score should be 40 to 69, and level should be 'medium'.
    - If there are only Low risks, the score should be below 40, and level should be 'low'.
    """

    try:
        completion = client.beta.chat.completions.parse(
            model=settings.DEFAULT_LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert executive legal summary generator."},
                {"role": "user", "content": prompt}
            ],
            response_format=ExecutiveSummaryOutput
        )
        result = completion.choices[0].message.parsed
        
        # Build the final dict
        executive_summary = {
            "overall_risk_level": result.overall_risk_level,
            # We enforce a safe integer cast and range check
            "overall_risk_score": max(0, min(100, int(result.overall_risk_score if hasattr(result, 'overall_risk_score') else 50))),
            "top_3_risks": result.top_3_risks,
            "top_2_negotiations": result.top_2_negotiations
        }
        
        # Wait, let's also compute a fallback risk score from the average of the detected risk scores
        # if the LLM output is missing or incorrect, but with Structured Outputs it will be present.
        
        return {"executive_summary": executive_summary}
    except Exception as e:
        # Fallback calculation if LLM call fails
        scores = [r.get("risk_score", 0) for r in detected_risks]
        avg_score = int(sum(scores) / len(scores)) if scores else 10
        level = "low"
        if avg_score >= 70:
            level = "high"
        elif avg_score >= 40:
            level = "medium"
            
        fallback_summary = {
            "overall_risk_level": level,
            "overall_risk_score": avg_score,
            "top_3_risks": [r.get("description", "") for r in detected_risks[:3]],
            "top_2_negotiations": [f"Negotiate {r.get('risk_category', 'clause')}" for r in detected_risks[:2]]
        }
        return {
            "executive_summary": fallback_summary,
            "errors": state.get("errors", []) + [f"Summary Agent error: {str(e)}"]
        }
