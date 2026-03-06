# UniGuru Live Service Runbook

## 1. Install Dependencies
```powershell
python -m pip install -r uniguru/requirements.txt
```

## 2. Optional Environment Setup
Copy `uniguru/.env.example` to `.env` and set:
- `UNIGURU_HOST`
- `UNIGURU_PORT`

## 3. Start Service
```powershell
.\scripts\start_uniguru_service.ps1
```

Default: `http://0.0.0.0:8010`

## 4. Quick Verification
```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8010/ask" -ContentType "application/json" -Body '{"user_query":"What is a qubit?","session_id":"demo-1","allow_web_retrieval":false}'
```

## 5. Deterministic Test Execution
```powershell
python -m pytest uniguru/tests/test_live_service.py -q
```

