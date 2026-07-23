import os
import pandas as pd
import requests
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

DUMMY_RATES = pd.DataFrame({
    "worker_id": ["W001", "W002"],
    "worker_name": ["Alice Smith", "Bob Jones"],
    "rate": [25.0, 30.0]
})

def extract_rate_from_pdf(pdf_path: str) -> pd.DataFrame:
    """
    Extract structured rate data from a rate agreement PDF.
    Uses DeepSeek‑v4‑flash if an API key is set; otherwise returns dummy data.
    The extraction prompt forces the primary entity to be Worker Name.
    """
    if not DEEPSEEK_API_KEY or PdfReader is None:
        # Fallback for demo (runs offline, under 10 s)
        return DUMMY_RATES.copy()

    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""

    prompt = (
        "Extract the following from the rate agreement document. "
        "The primary entity the buyer tracks is: Worker Name. "
        "Output a JSON array of objects with keys: worker_id, worker_name, rate_per_hour. "
        "Rate must be a number. Keep the worker name exactly as it appears.\n\n"
        f"Document:\n{text[:3000]}"
    )

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0
    }

    resp = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    # Simple JSON extraction: assume it's a clean array
    import json
    start = content.find('[')
    end = content.rfind(']') + 1
    json_str = content[start:end] if start != -1 else content
    records = json.loads(json_str)
    df = pd.DataFrame(records)
    df.rename(columns={"rate_per_hour": "rate"}, inplace=True)
    return df[["worker_id", "worker_name", "rate"]]

def load_rate_agreement(path: str) -> pd.DataFrame:
    """
    Load rate data from CSV or PDF.
    CSV expected columns: worker_id, worker_name, rate
    """
    if path.endswith('.csv'):
        df = pd.read_csv(path)
        return df[["worker_id", "worker_name", "rate"]]
    elif path.endswith('.pdf'):
        return extract_rate_from_pdf(path)
    else:
        raise ValueError("Unsupported rate agreement format. Use CSV or PDF.")
