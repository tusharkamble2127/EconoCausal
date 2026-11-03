# Forensic QA Test Data Generator - Part 2 (fixed)
$base = 'http://127.0.0.1:8000'

# Login
$loginBody = @{email='qa-forensic-2026@test.com'; password='securepass123'} | ConvertTo-Json
$r = Invoke-RestMethod -Uri "$base/auth/login" -Method Post -Body $loginBody -ContentType 'application/json'
$token = $r.access_token
$headers = @{Authorization = "Bearer $token"; "Content-Type" = "application/json"}
Write-Host "Logged in successfully"

function New-Dataset($name, $rows) {
    $body = @{name=$name; rows=$rows} | ConvertTo-Json -Depth 3
    $r = Invoke-RestMethod -Uri "$base/datasets" -Method Post -Body $body -Headers $headers
    Write-Host "Created dataset '$name' with ID: $($r.dataset_id), rows: $($r.row_count)"
    return $r.dataset_id
}

function New-Run($datasetId, $name, $budget=5000) {
    $body = @{
        dataset_id = $datasetId
        budget = $budget
        base_estimator = "RandomForest"
        campaign_name = $name
        discount_levels = @(0, 5, 10, 15, 20, 25, 30)
        treatment_column = "treatment"
        outcome_column = "outcome"
    } | ConvertTo-Json -Depth 3
    $r = Invoke-RestMethod -Uri "$base/runs" -Method Post -Body $body -Headers $headers
    Write-Host "Created run '$name' with ID: $($r.run_id), status: $($r.status)"
    return $r.run_id
}

# TEST 2 FIXED: Long-text dataset (long campaign name, not in features)
Write-Host "`n=== TEST 2 FIXED: Long-text dataset ==="
$longRows = @()
for ($i=1; $i -le 20; $i++) {
    $longRows += @{
        features = @{
            age=[double](25 + ($i % 40))
            income=[double](40000 + ($i % 60000))
            prior_purchases=[double]($i % 10)
        }
        treatment = [double]($i % 2)
        outcome = [int]($i % 2)
    }
}
$longDsId = New-Dataset "forensic_long_text" $longRows
$longRunId = New-Run $longDsId "Extended Summer Loyalty Promotion 2026 with Enhanced Multi-Channel Engagement Strategy" 5000

# TEST 4 FIXED: Special-characters dataset
Write-Host "`n=== TEST 4 FIXED: Special-characters dataset ==="
$specialRows = @()
for ($i=1; $i -le 10; $i++) {
    $specialRows += @{
        features = @{
            age=[double](20 + $i)
            income=[double](30000 + ($i * 1000))
            prior_purchases=[double]$i
        }
        treatment = [double]($i % 2)
        outcome = [int]($i % 2)
    }
}
$specialDsId = New-Dataset "forensic_special_chars" $specialRows
$specialRunId = New-Run $specialDsId "Café résumé naïve Zürich £500 ¥1000 €200" 3000

# TEST 6: Missing-data dataset with nulls/NaNs in features
Write-Host "`n=== TEST 6: Missing-data dataset with nulls ==="
$missingRows = @(
    @{features=@{age=30.0; income=50000.0; prior_purchases=2.0}; treatment=1.0; outcome=1}
    @{features=@{age=35.0; income=[double]::NaN; prior_purchases=3.0}; treatment=0.0; outcome=0}
    @{features=@{age=[double]::PositiveInfinity; income=60000.0; prior_purchases=1.0}; treatment=1.0; outcome=1}
    @{features=@{age=40.0; income=55000.0}; treatment=0.0; outcome=0}
)
try {
    $missingDsId = New-Dataset "forensic_missing_nulls" $missingRows
    $missingRunId = New-Run $missingDsId "Forensic Missing Nulls" 2000
} catch {
    Write-Host "Missing data test failed as expected: $_"
}

Write-Host "`n=== All fixed test runs created ==="
Write-Host "Large: $largeRunId"
Write-Host "Long-text: $longRunId"
Write-Host "Special-chars: $specialRunId"
Write-Host "Missing (run 104): 104"
