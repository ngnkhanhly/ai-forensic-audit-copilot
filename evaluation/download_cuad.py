import os
import requests

def download_cuad_samples():
    """
    Downloads additional sample legal contracts from Atticus Project (CUAD) public repository
    to show real-world data sourcing pipelines.
    """
    dataset_dir = os.path.join(os.path.dirname(__file__), "dataset", "test_contracts")
    os.makedirs(dataset_dir, exist_ok=True)
    
    # We will fetch a couple of real contracts from the Atticus CUAD repo on GitHub
    samples = {
        "cuad_sample_1.txt": "https://raw.githubusercontent.com/TheAtticusProject/cuad/main/NDA/CleanNDA/CleanNDA.txt",
    }
    
    print("=== Sourcing CUAD Dataset Samples ===")
    for filename, url in samples.items():
        dest = os.path.join(dataset_dir, filename)
        if os.path.exists(dest):
            print(f"File {filename} already exists at {dest}. Skipping download.")
            continue
            
        print(f"Downloading {filename} from Atticus Project GitHub...")
        try:
            res = requests.get(url, timeout=15)
            if res.status_code == 200:
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(res.text)
                print(f"Successfully downloaded and saved {filename}.")
            else:
                print(f"Failed to download {filename} (HTTP Status {res.status_code}).")
        except Exception as e:
            print(f"Network error downloading {filename}: {str(e)}")
            
    print("\nNote: Standard benchmark contracts (NDA, SaaS, Service) are already pre-packaged in the evaluation folder for offline-friendly execution.")

if __name__ == "__main__":
    download_cuad_samples()
