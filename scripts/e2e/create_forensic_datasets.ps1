# Forensic QA Test Data Generator
$base = 'http://127.0.0.1:8000'

# Login
$loginBody = @{email='qa-forensic-2026@test.com'; password='securepass123'} | ConvertTo-Json
$r = Invoke-RestMethod -Uri "$base/auth/login" -Method Post -Body $loginBody -ContentType 'application/json'
$token = $r.access_token
$headers = @{Authorization = "Bearer $token"; "Content-Type" = "application/json"}
Write-Host "Logged in successfully"

# Helper to create dataset
function New-Dataset($name, $rows) {
    $body = @{name=$name; rows=$rows} | ConvertTo-Json -Depth 3
    $r = Invoke-RestMethod -Uri "$base/datasets" -Method Post -Body $body -Headers $headers
    Write-Host "Created dataset '$name' with ID: $($r.dataset_id), rows: $($r.row_count)"
    return $r.dataset_id
}

# Helper to create run
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

# TEST 1: Large dataset (500 rows) for multi-page PDF
Write-Host "`n=== TEST 1: Large dataset (500 rows) ==="
$largeRows = @()
for ($i=1; $i -le 500; $i++) {
    $largeRows += @{
        features = @{age=[double](20 + ($i % 50)); income=[double](30000 + ($i % 70000)); prior_purchases=[double]($i % 15)}
        treatment = [double]($i % 2)
        outcome = [int]($i % 2)  # binary 0/1
    }
}
$largeDsId = New-Dataset "forensic_large_500" $largeRows
$largeRunId = New-Run $largeDsId "Forensic Large 500" 10000

# TEST 2: Long-text dataset
Write-Host "`n=== TEST 2: Long-text dataset ==="
$longRows = @()
for ($i=1; $i -le 20; $i++) {
    $longRows += @{
        features = @{
            age=[double](25 + ($i % 40))
            income=[double](40000 + ($i % 60000))
            prior_purchases=[double]($i % 10)
            campaign_name="Extended Summer Loyalty Promotion 2026 with Enhanced Multi-Channel Engagement Strategy"
            description="This is a deliberately long description designed to test PDF text wrapping behavior under extreme content length conditions that might occur in real production usage with verbose marketing copy"
        }
        treatment = [double]($i % 2)
        outcome = [int]($i % 2)
    }
}
$longDsId = New-Dataset "forensic_long_text" $longRows
$longRunId = New-Run $longDsId "Extended Summer Loyalty Promotion 2026 with Enhanced Multi-Channel Engagement Strategy" 5000

# TEST 3: Missing-data dataset
Write-Host "`n=== TEST 3: Missing-data dataset ==="
$missingRows = @(
    @{features=@{age=30; income=50000.0}; treatment=1; outcome=1}
    @{features=@{age=35; income=60000.0}; treatment=0; outcome=0}
    @{features=@{age=40; income=55000.0}; treatment=1; outcome=1}
)
$missingDsId = New-Dataset "forensic_missing_data" $missingRows
$missingRunId = New-Run $missingDsId "Forensic Missing Data" 2000

# TEST 4: Special-characters dataset
Write-Host "`n=== TEST 4: Special-characters dataset ==="
$specialRows = @()
for ($i=1; $i -le 10; $i++) {
    $specialRows += @{
        features = @{
            age=[double](20 + $i)
            income=[double](30000 + ($i * 1000))
            prior_purchases=[double]$i
            name="José García-Müller"
            notes="Café résumé naïve Zürich £500 ¥1000 €200"
        }
        treatment = [double]($i % 2)
        outcome = [int]($i % 2)
    }
}
$specialDsId = New-Dataset "forensic_special_chars" $specialRows
$specialRunId = New-Run $specialDsId "Café résumé naïve Zürich" 3000

# TEST 5: Small dataset (5 rows) for small PDF
Write-Host "`n=== TEST 5: Small dataset (5 rows) ==="
$smallRows = @()
for ($i=1; $i -le 5; $i++) {
    $smallRows += @{
        features = @{age=[double](20+$i); income=[double](40000+($i*5000)); prior_purchases=[double]$i}
        treatment = [double]($i % 2)
        outcome = [int]($i % 2)
    }
}
$smallDsId = New-Dataset "forensic_small_5" $smallRows
$smallRunId = New-Run $smallDsId "Forensic Small 5" 1000

Write-Host "`n=== All test runs created ==="
Write-Host "Large: $largeRunId"
Write-Host "Long-text: $longRunId"
Write-Host "Missing-data: $missingRunId"
Write-Host "Special-chars: $specialRunId"
Write-Host "Small: $smallRunId"
