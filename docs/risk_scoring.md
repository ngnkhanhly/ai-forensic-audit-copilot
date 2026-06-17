# 🔢 Risk Scoring Engine

Unlike standard extraction tools, the AI Forensic Audit Copilot calculates an explainable risk score rather than letting an LLM generate an arbitrary "high/low" risk string.

## Formula

The Final Risk Score (0-100) is calculated via a Weighted Sum Rule based on concrete cross-document evidence:

```text
Final Risk Score = 
  (35% * Duplicate Similarity Risk) 
+ (25% * Contract Mismatch Risk) 
+ (15% * Amount Anomaly Risk) 
+ (10% * Vendor Risk) 
+ (10% * Missing Required Fields Risk) 
+ ( 5% * LLM Confidence Penalty)
```

## Factor Details

1. **Duplicate Similarity (0-100):** Calculated using Jaro-Winkler string similarity on Vendor Names combined with Date and Amount matching.
2. **Contract Mismatch (0 or 100):** Checks if the payment terms (e.g. Net 7 vs Net 30) or banking details on the invoice violate the master contract.
3. **Amount Anomaly (0 or 100):** Flags unusual round numbers (e.g., exactly $10,000) or values exceeding PO limits.
4. **Vendor Risk (0 or 100):** Flags new or untrusted vendors.
5. **Missing Required Fields (0 or 100):** Flags missing Tax IDs or missing Purchase Order references.
6. **LLM Confidence Penalty:** `100 - LLM_Confidence_Score`

## Action Thresholds

| Score Range | Risk Level | System Action |
| :--- | :--- | :--- |
| **0 – 30** | Low | Auto approve (Proceed to ERP integration) |
| **31 – 60** | Medium | Review recommended |
| **61 – 85** | High | Manual approval required |
| **86 – 100** | Critical | Block payment (Trigger fraud investigation) |
