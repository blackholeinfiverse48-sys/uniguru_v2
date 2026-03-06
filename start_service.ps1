# UniGuru Service Startup Script
Write-Host "--- UniGuru Live Reasoning Service ---" -ForegroundColor Green
$env:PYTHONPATH = "c:\Users\Yass0\OneDrive\Desktop\TASK14"
python -m uvicorn uniguru.service.api:app --host 127.0.0.1 --port 8000 --reload
