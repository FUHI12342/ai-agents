#!/usr/bin/env pwsh

# Test script for speckit

Write-Host "Running tests for speckit..."

# Run pytest
pytest tests/

Write-Host "Tests completed."