# 📊 Evaluation Protocol & Fraud Metrics

To prove the enterprise value of the **AI Forensic Audit Copilot**, we evaluate the system against real-world and synthetic fraud injection datasets.

## Benchmark Datasets
- **SROIE & CORD (Clean):** Used to establish base OCR and extraction F1 metrics.
- **Synthetic Fraud Injection Dataset:** We inject controlled variations into clean documents (e.g., fuzzing vendor names, duplicating amounts, altering dates by +/- 1 day, missing POs) to test the Fraud Detection Engine.

## Fraud Detection Metrics
We track precise metrics for the Copilot's ability to act as an auditor:

| Module | Metric | Description | Target Result |
| :--- | :--- | :--- | :---: |
| **Invoice Extraction** | Field-level F1 | Standard structured extraction accuracy. | > 0.90 |
| **Contract Extraction** | Field-level F1 | Contract clause and entity extraction. | > 0.85 |
| **Near-Duplicate Detection** | Precision | Ratio of correctly flagged duplicates vs total flagged. | > 0.90 |
| **Near-Duplicate Detection** | Recall | Ratio of caught duplicates vs actual injected duplicates. | > 0.85 |
| **Cross-document Audit** | Accuracy | Accuracy of detecting term mismatches (e.g. Net 7 vs Net 30). | > 0.80 |
| **Risk Classification** | Accuracy | Correct categorization into Low/Medium/High/Critical. | > 0.85 |
| **Human Review Reduction** | % workload reduced | Percentage of documents safely auto-approved. | ~75% |

## How to Run

Execute the evaluation script locally:
```bash
python evaluation/evaluate.py
```
*(Results are written to `evaluation/dataset/eval_results.json` and loaded into the dashboard).*
