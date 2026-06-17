from openai import OpenAI
from typing import Dict, Any, List
from backend.app.config import settings
from backend.app.schemas import ExtractedClausesOutput

def run_extraction_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent node to extract key clauses from the contract text.
    """
    contract_text = state.get("contract_text", "")
    if not contract_text:
        return {"errors": state.get("errors", []) + ["No contract text found for extraction"]}

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    prompt = f"""
    You are an expert legal counsel. Extract the following clauses from the contract:
    1. Payment Terms
    2. Termination
    3. Confidentiality
    4. Liability (including limitations of liability, indemnification, etc.)
    5. Governing Law
    
    For each clause, provide the exact or most relevant text from the contract. 
    If a clause type is not present in the contract, do not include it.

    Contract Text:
    {contract_text}
    """

    try:
        completion = client.beta.chat.completions.parse(
            model=settings.DEFAULT_LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional legal contract extractor."},
                {"role": "user", "content": prompt}
            ],
            response_format=ExtractedClausesOutput
        )
        result = completion.choices[0].message.parsed
        
        extracted_clauses = [
            {"clause_type": clause.clause_type, "text": clause.text}
            for clause in result.clauses
        ]
        
        return {"extracted_clauses": extracted_clauses}
    except Exception as e:
        return {"errors": state.get("errors", []) + [f"Extraction Agent error: {str(e)}"]}
