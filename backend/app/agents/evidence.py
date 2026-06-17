from openai import OpenAI
from typing import Dict, Any, List
from backend.app.config import settings
from pydantic import BaseModel

class VerifiedEvidence(BaseModel):
    exact_quote: str
    verified: bool

def run_evidence_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent node that verifies risk evidence quotes against the original contract text,
    finding the exact character matches to prevent hallucinations.
    """
    contract_text = state.get("contract_text", "")
    detected_risks = state.get("detected_risks", [])
    
    if not contract_text or not detected_risks:
        return {}

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    verified_risks = []

    for risk in detected_risks:
        raw_evidence = risk.get("evidence_text", "").strip()
        
        # 1. Simple heuristic: If it is already a substring of the contract text (case insensitive)
        if raw_evidence.lower() in contract_text.lower():
            # Find the exact case-sensitive matching string in the contract
            start_idx = contract_text.lower().find(raw_evidence.lower())
            exact_match = contract_text[start_idx:start_idx + len(raw_evidence)]
            risk["evidence_text"] = exact_match
            verified_risks.append(risk)
            continue

        # 2. If it's not a direct substring, ask the LLM to extract the exact matching sentence/phrase
        # from the contract text that contains the claim, ensuring it retains punctuation and casing.
        prompt = f"""
        You are an auditor. We found a risk in a contract, and the agent provided a summary quote: "{raw_evidence}".
        Your job is to find the EXACT quote (sentence or phrase) inside the contract text that represents this.
        Do not modify the text, punctuation, or casing. It must be a substring of the contract text.
        
        If you find it, output verified=true and the exact_quote.
        If it does not exist at all in the contract, output verified=false.

        Contract Text:
        {contract_text}
        """
        
        try:
            completion = client.beta.chat.completions.parse(
                model=settings.DEFAULT_LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are a legal document auditor verifying quotes."},
                    {"role": "user", "content": prompt}
                ],
                response_format=VerifiedEvidence
            )
            result = completion.choices[0].message.parsed
            
            if result.verified and result.exact_quote.lower() in contract_text.lower():
                # Locate case-sensitive match
                start_idx = contract_text.lower().find(result.exact_quote.lower())
                exact_match = contract_text[start_idx:start_idx + len(result.exact_quote)]
                risk["evidence_text"] = exact_match
            else:
                # Fallback to the original evidence if verification fails
                risk["evidence_text"] = f"[Unverified Quote] {raw_evidence}"
        except Exception:
            risk["evidence_text"] = f"[Unverified Quote] {raw_evidence}"
            
        verified_risks.append(risk)

    return {"detected_risks": verified_risks}
