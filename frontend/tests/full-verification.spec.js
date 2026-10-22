import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';
const API_URL = 'http://127.0.0.1:8000';

test.describe('EconoCausal Full Browser Functional Audit', () => {
  test.describe.configure({ mode: 'serial' });

  let authToken = '';
  let runId = null;
  let campaignStartTime = 0;
  let campaignEndTime = 0;
  const TEST_EMAIL = `audit-${Date.now()}@test.com`;
  const TEST_PASSWORD = 'AuditPass123!';

  test.beforeAll(async ({ request }) => {
    const response = await request.get(`${API_URL}/health`);
    expect(response.ok()).toBe(true);
  });

  test.afterAll(async ({ request }) => {
    if (runId && authToken) {
      const headers = { Authorization: `Bearer ${authToken}` };
      try {
        await request.get(`${API_URL}/runs/${runId}`, { headers });
      } catch (e) {
        // ignore cleanup errors
      }
    }
  });

  async function login(page) {
    await page.goto(`${BASE_URL}/login`);
    await page.waitForURL('**/login');
    await page.waitForSelector('input[type="email"]', { timeout: 10000 });
    
    await page.fill('input[type="email"]', TEST_EMAIL);
    await page.fill('input[type="password"]', TEST_PASSWORD);
    await page.click('button[type="submit"]');
    
    await page.waitForTimeout(2000);
    await page.waitForURL('**/', { timeout: 15000 });
  }

  test('1. Register and login', async ({ page }) => {
    const regResp = await page.request.post(`${API_URL}/auth/register`, {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD, full_name: 'Audit User' },
    });
    expect(regResp.ok()).toBe(true);
    const regData = await regResp.json();
    authToken = regData.access_token;
    expect(authToken).toBeDefined();

    await login(page);
  });

  test('2. Upload dataset and run campaign', async ({ page }) => {
    test.setTimeout(900000);
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForURL('**/', { timeout: 15000 });
    
    // Upload the verification dataset
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('D:/roopank/internship/infotact/EconoCausal_Fixed/econocausal/data/raw/verification_dataset_50.csv');
    
    // Wait for preview to appear
    await page.waitForSelector('text=Rows:', { timeout: 15000 });
    await page.waitForSelector('text=Columns:', { timeout: 15000 });
    
    // Verify preview shows correct data
    const rowsText = await page.locator('text=Rows:').first().textContent();
    expect(rowsText).toContain('50');
    
    // Map columns (the label is a sibling <label> of the <select>, not inside it,
    // so select by the labelled-by association: label + select)
    await page.selectOption('label:has-text("Customer ID column") + select', 'customer_id');
    await page.selectOption('label:has-text("Treatment column") + select', 'treatment');
    await page.selectOption('label:has-text("Outcome column") + select', 'outcome');
    
    // Set budget
    const budgetInput = page.locator('input[type="number"]').first();
    await budgetInput.fill('4000');
    
    // Verify discount levels include 0%
    const discountText = await page.locator('text=0% control level included').textContent();
    expect(discountText).toBeDefined();
    
    // Submit campaign
    const submitBtn = page.locator('button:has-text("Run campaign")');
    await expect(submitBtn).toBeEnabled();
    
    campaignStartTime = Date.now();
    await submitBtn.click();

    // The backend runs campaigns synchronously and may take several minutes.
    // The frontend axios client has its own 30s timeout, so we poll the API
    // directly for the authoritative completion signal.
    const headers = { Authorization: `Bearer ${authToken}` };

    // Locate the newly created run via the campaign history endpoint.
    let found = false;
    for (let attempt = 0; attempt < 30; attempt++) {
      await page.waitForTimeout(2000);
      const historyResp = await page.request.get(`${API_URL}/campaigns`, { headers });
      if (historyResp.ok()) {
        const historyData = await historyResp.json();
        const match = historyData.campaigns.find(
          (c) => c.campaign_name === 'verification_dataset_50',
        );
        if (match && match.run_id) {
          runId = match.run_id;
          found = true;
          break;
        }
      }
    }

    if (!found || !runId) {
      throw new Error('Could not locate the created campaign via /campaigns');
    }

    // Poll for completion with generous timeout and diagnostics.
    const maxPolls = 180;
    const pollIntervalMs = 5000;
    let lastStatus = 'unknown';
    let completed = false;

    for (let i = 0; i < maxPolls; i++) {
      await page.waitForTimeout(pollIntervalMs);
      let statusResp;
      let retries = 0;
      while (retries < 3) {
        try {
          statusResp = await page.request.get(`${API_URL}/runs/${runId}`, { headers });
          break;
        } catch (err) {
          retries++;
          if (retries >= 3) throw err;
          await page.waitForTimeout(2000);
        }
      }
      if (!statusResp.ok()) {
        throw new Error(`Failed to fetch run ${runId} status: HTTP ${statusResp.status()}`);
      }
      const statusData = await statusResp.json();
      lastStatus = statusData.status;

      if (i % 6 === 0) {
        console.log(`Campaign ${runId} poll ${i}: status=${lastStatus}`);
      }

      if (lastStatus === 'complete') {
        campaignEndTime = Date.now();
        completed = true;
        break;
      }
      if (lastStatus === 'failed') {
        throw new Error(`Campaign ${runId} failed with status: ${lastStatus}`);
      }
    }

    if (!completed) {
      const elapsed = ((Date.now() - campaignStartTime) / 1000).toFixed(1);
      throw new Error(
        `Campaign ${runId} did not complete within timeout. ` +
          `Elapsed: ${elapsed}s. Last status: ${lastStatus}. ` +
          `Verify backend logs for run ${runId}.`,
      );
    }

    const runtime = ((campaignEndTime - campaignStartTime) / 1000).toFixed(1);
    console.log(`Campaign runtime: ${runtime}s`);

    // Navigate to dashboard and verify the UI reflects the completed state.
    await page.goto(`${BASE_URL}/dashboard/${runId}`);
    await page.waitForURL(`**/dashboard/${runId}`, { timeout: 15000 });
  });

  test('3. Dashboard Overview', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/dashboard/${runId}`);
    await page.waitForURL(`**/dashboard/${runId}`, { timeout: 15000 });
    // SPA: data loads after React mounts via fetchAll -> getRun first, then a
    // Promise.all of 9 endpoints gates the KPI cards. Use waitForSelector
    // (active polling) rather than networkidle, which resolves before the
    // app's runtime fetches and is unreliable with the Vite HMR websocket.
    await page.waitForSelector(`text=Run #${runId}`, { timeout: 60000 });
    await page.waitForSelector('text=Budget Utilization', { timeout: 60000 });
    await page.waitForSelector('text=ROI Improvement', { timeout: 60000 });
    await expect(page.locator('text=Budget Utilization')).toBeVisible();
    await expect(page.locator('text=ROI Improvement')).toBeVisible();
    
    const bodyText = await page.locator('body').textContent();
    expect(bodyText.length).toBeGreaterThan(100);
    
    const hasNaN = bodyText.includes('NaN');
    const hasUndefined = bodyText.includes('undefined');
    const hasNull = bodyText.includes('null');
    expect(hasNaN).toBe(false);
    expect(hasUndefined).toBe(false);
    expect(hasNull).toBe(false);
  });

  test('4. Analytics page', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/dashboard/${runId}/analytics`);
    await page.waitForURL(`**/dashboard/${runId}/analytics`, { timeout: 15000 });
    expect(page.url()).toContain('/analytics');
    await page.waitForFunction(() => (document.body.textContent || '').length > 100, { timeout: 60000 });
    const bodyText = await page.locator('body').textContent();
    expect(bodyText.length).toBeGreaterThan(100);
  });

  test('5. Propensity page', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/dashboard/${runId}/propensity`);
    await page.waitForURL(`**/dashboard/${runId}/propensity`, { timeout: 15000 });
    expect(page.url()).toContain('/propensity');
    await page.waitForFunction(() => (document.body.textContent || '').length > 100, { timeout: 60000 });
    const bodyText = await page.locator('body').textContent();
    expect(bodyText.length).toBeGreaterThan(100);
  });

  test('6. Explainability page', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/dashboard/${runId}/explainability`);
    await page.waitForURL(`**/dashboard/${runId}/explainability`, { timeout: 15000 });
    expect(page.url()).toContain('/explainability');
    await page.waitForFunction(() => (document.body.textContent || '').length > 100, { timeout: 60000 });
    const bodyText = await page.locator('body').textContent();
    expect(bodyText.length).toBeGreaterThan(100);
  });

  test('7. Refutation page', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/dashboard/${runId}/refutation`);
    await page.waitForURL(`**/dashboard/${runId}/refutation`, { timeout: 15000 });
    expect(page.url()).toContain('/refutation');
    await page.waitForFunction(() => (document.body.textContent || '').length > 100, { timeout: 60000 });
    const bodyText = await page.locator('body').textContent();
    expect(bodyText.length).toBeGreaterThan(100);
  });

  test('8. Drift page', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/dashboard/${runId}/drift`);
    await page.waitForURL(`**/dashboard/${runId}/drift`, { timeout: 15000 });
    expect(page.url()).toContain('/drift');
    await page.waitForFunction(() => (document.body.textContent || '').length > 100, { timeout: 60000 });
    const bodyText = await page.locator('body').textContent();
    expect(bodyText.length).toBeGreaterThan(100);
  });

  test('9. Recommendations page', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/dashboard/${runId}/recommendations`);
    await page.waitForURL(`**/dashboard/${runId}/recommendations`, { timeout: 15000 });
    expect(page.url()).toContain('/recommendations');
    await page.waitForFunction(() => (document.body.textContent || '').length > 100, { timeout: 60000 });
    const bodyText = await page.locator('body').textContent();
    expect(bodyText.length).toBeGreaterThan(100);
  });

  test('10. Allocation page', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/dashboard/${runId}/allocation`);
    await page.waitForURL(`**/dashboard/${runId}/allocation`, { timeout: 15000 });
    expect(page.url()).toContain('/allocation');
    await page.waitForFunction(() => (document.body.textContent || '').length > 100, { timeout: 60000 });
    const bodyText = await page.locator('body').textContent();
    expect(bodyText.length).toBeGreaterThan(100);
  });

  test('11. ITE page', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/dashboard/${runId}/ite`);
    await page.waitForURL(`**/dashboard/${runId}/ite`, { timeout: 15000 });
    expect(page.url()).toContain('/ite');
    await page.waitForFunction(() => (document.body.textContent || '').length > 100, { timeout: 60000 });
    const bodyText = await page.locator('body').textContent();
    expect(bodyText.length).toBeGreaterThan(100);
  });

  test('12. Scenario page', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/dashboard/${runId}/scenario`);
    await page.waitForURL(`**/dashboard/${runId}/scenario`, { timeout: 15000 });
    expect(page.url()).toContain('/scenario');
    await page.waitForFunction(() => (document.body.textContent || '').length > 100, { timeout: 60000 });
    const bodyText = await page.locator('body').textContent();
    expect(bodyText.length).toBeGreaterThan(100);
  });

  test('13. Reports page', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/dashboard/${runId}/reports`);
    await page.waitForURL(`**/dashboard/${runId}/reports`, { timeout: 15000 });
    expect(page.url()).toContain('/reports');
    await page.waitForFunction(() => (document.body.textContent || '').length > 100, { timeout: 60000 });
    const bodyText = await page.locator('body').textContent();
    expect(bodyText.length).toBeGreaterThan(100);
  });

  test('14. Assistant page', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/dashboard/${runId}/assistant`);
    await page.waitForURL(`**/dashboard/${runId}/assistant`, { timeout: 15000 });
    expect(page.url()).toContain('/assistant');
    await page.waitForFunction(() => (document.body.textContent || '').length > 100, { timeout: 60000 });
    const bodyText = await page.locator('body').textContent();
    expect(bodyText.length).toBeGreaterThan(100);
  });

  test('15. History page', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/history`);
    await page.waitForURL('**/history', { timeout: 15000 });
    await page.waitForFunction(() => (document.body.textContent || '').length > 100, { timeout: 60000 });
    const bodyText = await page.locator('body').textContent();
    expect(bodyText.length).toBeGreaterThan(100);
  });

  test('16. Sidebar navigation', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/dashboard/${runId}`);
    await page.waitForURL(`**/dashboard/${runId}`, { timeout: 15000 });
    
    const sidebarItems = [
      { name: 'Dashboard', path: `/dashboard/${runId}` },
      { name: 'Analytics', path: `/dashboard/${runId}/analytics` },
      { name: 'Propensity', path: `/dashboard/${runId}/propensity` },
      { name: 'Explainability', path: `/dashboard/${runId}/explainability` },
      { name: 'Refutation', path: `/dashboard/${runId}/refutation` },
      { name: 'Drift', path: `/dashboard/${runId}/drift` },
      { name: 'Recommendations', path: `/dashboard/${runId}/recommendations` },
      { name: 'Allocation', path: `/dashboard/${runId}/allocation` },
      { name: 'ITE', path: `/dashboard/${runId}/ite` },
      { name: 'Scenario', path: `/dashboard/${runId}/scenario` },
      { name: 'Reports', path: `/dashboard/${runId}/reports` },
      { name: 'Assistant', path: `/dashboard/${runId}/assistant` },
    ];
    
    for (const item of sidebarItems) {
      const link = page.locator(`a:has-text("${item.name}"), [href*="${item.path}"]`).first();
      if (await link.count() > 0) {
        await link.click();
        await page.waitForURL(`**${item.path}`, { timeout: 15000 });
        expect(page.url()).toContain(item.path);
        const bodyText = await page.locator('body').textContent();
        expect(bodyText.length).toBeGreaterThan(50);
      }
    }
  });

  test('17. Logout and protected route', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/dashboard/${runId}`);
    await page.waitForURL(`**/dashboard/${runId}`, { timeout: 15000 });
    
    const logoutBtn = page.locator('button:has-text("Logout"), a:has-text("Logout")');
    if (await logoutBtn.count() > 0) {
      await logoutBtn.click();
      await page.waitForURL('**/login', { timeout: 10000 });
      await page.goto(`${BASE_URL}/dashboard/${runId}`);
      await page.waitForURL('**/login', { timeout: 15000 });
    }
  });

  test('18. Browser console check', async ({ page }) => {
    await login(page);
    const consoleErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    page.on('pageerror', error => {
      consoleErrors.push(`PageError: ${error.message}`);
    });
    
    await page.goto(`${BASE_URL}/dashboard/${runId}`);
    await page.waitForTimeout(3000);
    
    const realErrors = consoleErrors.filter(err => 
      !err.includes('React Router') &&
      !err.includes('Warning') &&
      !err.includes('devtools') &&
      !err.includes('Extension')
    );
    
    expect(realErrors.length).toBe(0);
  });

  test('19. API endpoint verification', async ({ request }) => {
    const email = `api-test-${Date.now()}@test.com`;
    const regResp = await request.post(`${API_URL}/auth/register`, {
      data: { email, password: 'ApiTest123!', full_name: 'API Test' },
    });
    expect(regResp.ok()).toBe(true);
    const { access_token } = await regResp.json();
    const headers = { Authorization: `Bearer ${access_token}` };
    
    const rows = [];
    for (let i = 0; i < 2000; i++) {
      const loyalty = Math.random();
      const treatment = [0, 5, 10, 15, 20, 25, 30][Math.floor(Math.random() * 7)];
      const outcome = Math.random() < (0.3 + loyalty * 0.5 + treatment * 0.005) ? 1 : 0;
      rows.push({
        features: {
          customer_id: i + 1,
          tenure_months: Math.floor(Math.random() * 60),
          past_purchase_frequency: Math.floor(Math.random() * 20),
          loyalty_score: loyalty,
          avg_order_value: 20 + Math.random() * 180,
        },
        treatment,
        outcome,
      });
    }
    
    const dsResp = await request.post(`${API_URL}/datasets`, {
      data: { name: 'api-verification', rows },
      headers,
    });
    expect(dsResp.ok()).toBe(true);
    const { dataset_id } = await dsResp.json();
    
    const runResp = await request.post(`${API_URL}/runs`, {
      data: {
        dataset_id,
        budget: 4000,
        base_estimator: 'RandomForest',
        campaign_name: 'API Verification',
        discount_levels: [0, 5, 10, 15, 20, 25, 30],
        treatment_column: 'treatment',
        outcome_column: 'outcome',
      },
      headers,
    });
    expect(runResp.ok()).toBe(true);
    const { run_id } = await runResp.json();
    
    for (let i = 0; i < 120; i++) {
      await new Promise(r => setTimeout(r, 1000));
      const statusResp = await request.get(`${API_URL}/runs/${run_id}`, { headers });
      const statusData = await statusResp.json();
      if (statusData.status === 'complete') break;
      if (statusData.status === 'failed') throw new Error('API verification run failed');
    }
    
    const endpoints = [
      `/runs/${run_id}`,
      `/runs/${run_id}/summary`,
      `/runs/${run_id}/analytics`,
      `/runs/${run_id}/propensity`,
      `/runs/${run_id}/explainability`,
      `/runs/${run_id}/refutation`,
      `/runs/${run_id}/drift`,
      `/runs/${run_id}/recommendations`,
      `/runs/${run_id}/allocation`,
      `/runs/${run_id}/ite`,
      `/runs/${run_id}/report.csv`,
      `/runs/${run_id}/report.pdf`,
    ];
    
    for (const endpoint of endpoints) {
      const resp = await request.get(`${API_URL}${endpoint}`, { headers });
      expect(resp.ok()).toBe(true);
    }
    
    const simResp = await request.post(`${API_URL}/runs/${run_id}/simulate`, {
      data: { budget: 3000, discount_levels: [0, 10, 20] },
      headers,
    });
    expect(simResp.ok()).toBe(true);
    
    const assistResp = await request.post(`${API_URL}/runs/${run_id}/assistant`, {
      data: { question: 'What is the ROI?' },
      headers,
    });
    expect(assistResp.ok()).toBe(true);
    const assistData = await assistResp.json();
    expect(assistData.answer).toBeDefined();
    expect(assistData.answer.length).toBeGreaterThan(10);
  });
});
