# MARKETBOT — RUN ALL VALIDATION TRACKS
# Run from the MarketBot root:
# C:\Users\pavan\Documents\Python\Marketbot
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\RUN_VALIDATION.ps1

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "===================================================================="
Write-Host "MARKETBOT — MULTI-TRACK VALIDATION RUN"
Write-Host "===================================================================="

function Run-Step($title, $command) {
    Write-Host ""
    Write-Host "--------------------------------------------------------------------"
    Write-Host $title
    Write-Host "--------------------------------------------------------------------"
    Invoke-Expression $command
    if ($LASTEXITCODE -ne 0) {
        Write-Host "STATUS : FAIL ($LASTEXITCODE)" -ForegroundColor Red
    } else {
        Write-Host "STATUS : PASS" -ForegroundColor Green
    }
}

Run-Step "TRACK 1 — PCR CONTRACT" "python -m tests.test_pcr_engine_contract"
Run-Step "TRACK 2 — MAX PAIN CONTRACT" "python -m tests.test_max_pain_engine_contract"
Run-Step "TRACK 3 — OI REGRESSION CONTRACT" "python -m tests.test_oi_engine_contract"
Run-Step "TRACK 4 — OPTION INTELLIGENCE SEMANTIC TEST" "python .\option_intelligence_semantic_test.py"

Write-Host ""
Write-Host "===================================================================="
Write-Host "VALIDATION RUN COMPLETE"
Write-Host "===================================================================="
