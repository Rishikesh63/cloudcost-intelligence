# Activate the Poetry virtual environment
# Run this with: .\activate.ps1

Write-Host "Activating CloudCost Intelligence virtual environment..." -ForegroundColor Green

# Activate the .venv
& ".\.venv\Scripts\Activate.ps1"

Write-Host ""
Write-Host "✅ Virtual environment activated!" -ForegroundColor Green
Write-Host ""
Write-Host "You can now run:" -ForegroundColor Yellow
Write-Host "  streamlit run app.py" -ForegroundColor Cyan
Write-Host "  python cli.py" -ForegroundColor Cyan
Write-Host "  python database_manager.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "To deactivate, type: deactivate" -ForegroundColor Yellow
Write-Host ""
