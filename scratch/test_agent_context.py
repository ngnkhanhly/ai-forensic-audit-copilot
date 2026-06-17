import requests
import sqlite3
import os
import time

db_path = "documents.db"
if not os.path.exists(db_path):
    db_path = "documents.db"

# Find a completed document in SQLite database
doc_id = None
filename = None
doc_type = None

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, filename, document_type FROM documents WHERE status = 'completed' LIMIT 1")
        row = cursor.fetchone()
        if row:
            doc_id, filename, doc_type = row
            print(f"Found completed document in DB: ID {doc_id}, Filename '{filename}', Type '{doc_type}'")
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

if not doc_id:
    # If no completed document, upload one
    print("No completed document found. Uploading 'sample_contract.pdf'...")
    url_upload = "http://localhost:8000/api/documents/upload"
    file_path = "sample_contract.pdf"
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/pdf")}
            res = requests.post(url_upload, files=files)
            if res.status_code == 200:
                doc_id = res.json()["id"]
                filename = res.json()["filename"]
                doc_type = "contract"
                print(f"Uploaded successfully! ID: {doc_id}. Polling status...")
                for i in range(10):
                    time.sleep(2)
                    status_res = requests.get(f"http://localhost:8000/api/documents/{doc_id}")
                    if status_res.status_code == 200 and status_res.json()["status"] == "completed":
                        print("Document ingestion completed!")
                        break
            else:
                print(f"Failed to upload: {res.text}")
    else:
        print("Sample contract file not found to upload.")

if doc_id:
    url_agent = "http://localhost:8000/api/documents/agent"
    
    # Test 1: Chatting with active_document_id and active_document_context
    payload = {
        "messages": [
            {"role": "user", "content": "Hãy tóm tắt các thông tin quan trọng của tài liệu này."}
        ],
        "active_document_context": filename,
        "active_document_id": doc_id
    }
    
    print(f"\nSending agent chat query targeting active_document_id {doc_id}...")
    res = requests.post(url_agent, json=payload)
    if res.status_code == 200:
        print("\n--- Agent Response ---")
        answer = res.json()["answer"]
        with open("scratch_agent_response.txt", "w", encoding="utf-8") as f:
            f.write(answer)
        print("Saved response to scratch_agent_response.txt")
        print("SUCCESS: Context parsed successfully!")
    else:
        print(f"FAILED with status {res.status_code}: {res.text}")
else:
    print("Could not retrieve or ingest a document to test agent context.")
