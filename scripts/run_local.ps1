$ErrorActionPreference = "Stop"

Write-Host "Starting Rebot local stack..."

if (-not (Test-Path ".\\backend\\.venv")) {
  Write-Host "Creating venv..."
  python -m venv .\backend\.venv
}

Write-Host "Installing backend requirements..."
& .\backend\.venv\Scripts\pip install -r .\backend\requirements.txt

Write-Host "Starting backend..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\.venv\Scripts\activate; python -m app.main"

Write-Host "Starting worker..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\.venv\Scripts\activate; python -m app.worker"

if (Test-Path ".\\frontend\\package.json") {
  Write-Host "Starting frontend..."
  Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm install; npm run dev"
} else {
  Write-Host "Frontend not found. Generate a workspace first."
}
