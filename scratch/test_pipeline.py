import requests
import time
import sqlite3
import os

print("=== STARTING PIPELINE END-TO-END VERIFICATION ===")

# 1. Wait a bit for server to start up
print("Waiting for server to be ready...")
time.sleep(3)

def upload_and_verify(file_path):
    url = "http://localhost:8000/api/documents/upload"
    if not os.path.exists(file_path):
        print(f"Error: Sample file not found at {file_path}")
        return None
    
    print(f"\nUploading file: {file_path}")
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "application/pdf")}
        res = requests.post(url, files=files)
        
    if res.status_code != 200:
        print(f"Upload failed with status {res.status_code}: {res.text}")
        return None
        
    doc_info = res.json()
    doc_id = doc_info["id"]
    print(f"Document uploaded successfully! ID: {doc_id}")
    
    # Poll status
    print("Polling document status until completed...")
    for i in range(15):
        time.sleep(2)
        status_res = requests.get(f"http://localhost:8000/api/documents/{doc_id}")
        if status_res.status_code == 200:
            data = status_res.json()
            status = data["status"]
            print(f"Current status: {status}")
            if status == "completed":
                return data
            elif status == "failed":
                print(f"Pipeline failed! Logs: {data.get('validation_logs')}")
                return None
        else:
            print(f"Failed to fetch status: {status_res.text}")
    return None

# Upload Contract first so vendor and contract profile are saved
contract_data = upload_and_verify("sample_contract.pdf")
# Upload Invoice next to trigger cross-doc checks against contract
invoice_data = upload_and_verify("sample_invoice.pdf")

# Connect to database and show records
db_path = "documents.db"
if not os.path.exists(db_path):
    db_path = "documents.db"

if os.path.exists(db_path):
    print(f"\nDatabase found at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    def print_table_records(table_name):
        print(f"\n--- Records in '{table_name}' table ---")
        try:
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            pragma_info = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
            cols = [c[1] for c in pragma_info]
            print(f"Columns: {cols}")
            for r in rows:
                print(r)
        except Exception as e:
            print(f"Error reading {table_name}: {e}")
            
    print_table_records("documents")
    print_table_records("vendors")
    print_table_records("invoices")
    print_table_records("contracts")
    print_table_records("validation_results")
    conn.close()
else:
    print("Error: Database file not found!")

print("\n=== PIPELINE END-TO-END VERIFICATION COMPLETED ===")
