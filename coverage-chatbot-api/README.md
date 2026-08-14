# Coverage Chatbot API

A minimal FastAPI service with a health check endpoint.

## Run locally

1. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

2. Activate the virtual environment:

   - Windows:
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```

   - macOS/Linux:
     ```bash
     source .venv/bin/activate
     ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the app:

   ```bash
   python main.py
   ```

5. Open `http://127.0.0.1:8000/health` in your browser or use curl:

   ```bash
   curl http://127.0.0.1:8000/health
   ```

## Endpoint

- `GET /health` — returns `{ "status": "ok" }`
