import { test, expect } from '@playwright/test';
import fs from 'fs';

const API_URL = 'http://127.0.0.1:8000';

test('measure real campaign runtime', async ({ request }) => {
  const email = `real-${Date.now()}@test.com`;
  const password = 'RealPass123!';
  
  const regResp = await request.post(`${API_URL}/auth/register`, {
    data: { email, password, full_name: 'Real User' },
  });
  expect(regResp.ok()).toBe(true);
  const { access_token } = await regResp.json();
  const headers = { Authorization: `Bearer ${access_token}` };
  
  // Read the actual verification dataset
  const csv = fs.readFileSync('D:/roopank/internship/infotact/EconoCausal_Fixed/econocausal/data/raw/verification_dataset.csv', 'utf8');
  const lines = csv.split(/\r?\n/);
  const headers_line = lines[0].split(',').map(h => h.trim());
  console.log('CSV headers:', headers_line);
  
  const rows = [];
  for (let i = 1; i < lines.length && rows.length < 2000; i++) {
    const vals = lines[i].split(',').map(v => v.trim());
    if (vals.length < 7) continue;
    
    const features = {};
    headers_line.forEach(h => {
      if (h !== 'treatment' && h !== 'outcome') {
        features[h] = parseFloat(vals[headers_line.indexOf(h)]) || 0;
      }
    });
    
    const treatmentIdx = headers_line.indexOf('treatment');
    const outcomeIdx = headers_line.indexOf('outcome');
    
    rows.push({
      features,
      treatment: parseFloat(vals[treatmentIdx]) || 0,
      outcome: parseInt(vals[outcomeIdx]) || 0,
    });
  }
  
  console.log('Rows parsed:', rows.length);
  console.log('Sample row:', JSON.stringify(rows[0]));
  
  const dsResp = await request.post(`${API_URL}/datasets`, {
    data: { name: 'real-verification', rows },
    headers,
  });
  expect(dsResp.ok()).toBe(true);
  const { dataset_id } = await dsResp.json();
  
  const startTime = Date.now();
  const runResp = await request.post(`${API_URL}/runs`, {
    data: {
      dataset_id,
      budget: 4000,
      base_estimator: 'RandomForest',
      campaign_name: 'Real Verification',
      discount_levels: [0, 5, 10, 15, 20, 25, 30],
      treatment_column: 'treatment',
      outcome_column: 'outcome',
    },
    headers,
  });
  expect(runResp.ok()).toBe(true);
  const { run_id } = await runResp.json();
  
  for (let i = 0; i < 600; i++) {
    await new Promise(r => setTimeout(r, 1000));
    const statusResp = await request.get(`${API_URL}/runs/${run_id}`, { headers });
    const statusData = await statusResp.json();
    if (statusData.status === 'complete') {
      const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
      console.log(`REAL campaign completed in ${totalTime}s`);
      break;
    }
    if (statusData.status === 'failed') {
      console.log('Campaign FAILED');
      const runData = await statusResp.json();
      console.log('Error:', JSON.stringify(runData).substring(0, 500));
      break;
    }
    if (i % 15 === 0) {
      const statusResp2 = await request.get(`${API_URL}/runs/${run_id}`, { headers });
      const statusData2 = await statusResp2.json();
      console.log(`  ${i}s: ${statusData2.status}`);
    }
  }
});
