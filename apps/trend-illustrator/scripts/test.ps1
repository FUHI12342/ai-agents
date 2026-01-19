#!/usr/bin/env pwsh

# Test script for trend-illustrator

Write-Host "Running tests for trend-illustrator..."

# Change to the project root
Set-Location $PSScriptRoot\..

# Run pytest
pytest tests/ -v

if ($LASTEXITCODE -eq 0) {
    Write-Host "All tests passed!"
} else {
    Write-Host "Some tests failed."
    exit 1
}