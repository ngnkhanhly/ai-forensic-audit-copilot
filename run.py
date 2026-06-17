import subprocess
import sys
import time
import os
from dotenv import load_dotenv

load_dotenv()

def run_services():
    print("==================================================")
    # Check for OpenAI API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        print("[WARNING] OPENAI_API_KEY is not set or is still a placeholder in .env!")
        print("Please configure your OpenAI API key in the .env file to enable LLM agents.")
        print("==================================================")

    print("Starting AI Auditor Services...")
    
    # 1. Start Backend FastAPI
    print("Starting FastAPI Backend on http://localhost:8000 ...")
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Give backend a moment to start
    time.sleep(2)
    
    # 2. Start Frontend Streamlit
    print("Starting Streamlit Frontend on http://localhost:8501 ...")
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "frontend/app.py", "--server.port", "8501"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Keep main process running and pipe output
    try:
        while True:
            # Check if processes are alive
            b_ret = backend_process.poll()
            f_ret = frontend_process.poll()
            
            if b_ret is not None:
                print(f"[Backend] Terminated with code {b_ret}")
                break
            if f_ret is not None:
                print(f"[Frontend] Terminated with code {f_ret}")
                break
                
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping services...")
    finally:
        backend_process.terminate()
        frontend_process.terminate()
        print("Services stopped successfully.")

if __name__ == "__main__":
    run_services()
