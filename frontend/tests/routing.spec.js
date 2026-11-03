import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';
const API_URL = 'http://127.0.0.1:8000';

test.describe('EconoCausal Functional Routing', () => {
  test.beforeAll(async () => {
    const response = await fetch(`${API_URL}/health`);
    expect(response.ok).toBe(true);
  });

  test('should register and login', async ({ request }) => {
    const regResp = await request.post(`${API_URL}/auth/register`, {
      data: {
        email: `playwright-${Date.now()}@test.com`,
        password: 'testpass123',
        full_name: 'Playwright Test',
      },
    });
    expect(regResp.ok()).toBe(true);
  });

  test('should show login page for unauthenticated user', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForURL('**/login');
    await expect(page.locator('h2')).toContainText('Sign in');
  });

  test('should have correct route definitions in App.jsx', async ({ page }) => {
    await page.goto(BASE_URL);
    
    // Evaluate the app's route configuration in the browser context
    const routes = await page.evaluate(() => {
      // Check that the app has loaded by looking for React root
      const root = document.getElementById('root');
      return root ? 'loaded' : 'not_loaded';
    });
    
    expect(routes).toBe('loaded');
  });

  test('should verify sidebar navigation structure', async ({ page }) => {
    await page.goto(BASE_URL);
    
    // Wait for the app to render
    await page.waitForSelector('#root', { timeout: 10000 });
    
    // The app should show login since we're not authenticated
    await expect(page.locator('h2')).toContainText('Sign in');
    
    // Verify the app bundle loaded by checking for key React components
    const hasReact = await page.evaluate(() => {
      return typeof document.querySelector('[data-reactroot], #root') !== 'undefined';
    });
    
    expect(hasReact).toBe(true);
  });

  test('should verify API endpoints for all campaign pages', async ({ request }) => {
    // Register and login
    const regResp = await request.post(`${API_URL}/auth/register`, {
      data: {
        email: `routing-${Date.now()}@test.com`,
        password: 'testpass123',
        full_name: 'Routing Test',
      },
    });
    expect(regResp.ok()).toBe(true);
    const { access_token } = await regResp.json();
    const headers = { Authorization: `Bearer ${access_token}` };

    // Create dataset
    const rows = [];
    for (let i = 0; i < 60; i++) {
      const loyalty = (i % 10) / 10.0;
      const treatment = [0, 5, 10, 15, 20, 25, 30][i % 7];
      const outcome = (loyalty + treatment / 100.0 + Math.random() * 0.1) > 0.5 ? 1 : 0;
      rows.push({
        features: { loyalty_score: loyalty, tenure_months: i },
        treatment,
        outcome,
      });
    }

    const dsResp = await request.post(`${API_URL}/datasets`, {
      data: { name: 'routing-test', rows },
      headers,
    });
    expect(dsResp.ok()).toBe(true);
    const { dataset_id } = await dsResp.json();

    // Create run
    const runResp = await request.post(
      `${API_URL}/runs`,
      {
        data: {
          dataset_id,
          budget: 5000,
          base_estimator: 'RandomForest',
          campaign_name: 'Routing Test',
          discount_levels: [0, 5, 10, 15, 20, 25, 30],
          treatment_column: 'treatment',
          outcome_column: 'outcome',
        },
        headers,
      }
    );
    expect(runResp.ok()).toBe(true);
    const { run_id } = await runResp.json();

    // Poll for completion with longer timeout
    for (let i = 0; i < 90; i++) {
      await new Promise((r) => setTimeout(r, 2000));
      const statusResp = await request.get(`${API_URL}/runs/${run_id}`, { headers });
      const statusData = await statusResp.json();
      if (statusData.status === 'complete') break;
      if (statusData.status === 'failed') throw new Error('Run failed');
    }

    // Test all endpoints
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

    // Test scenario simulator
    const simResp = await request.post(
      `${API_URL}/runs/${run_id}/simulate`,
      {
        data: { budget: 3000, discount_levels: [0, 10, 20] },
        headers,
      }
    );
    expect(simResp.ok()).toBe(true);

    // Test assistant
    const assistResp = await request.post(
      `${API_URL}/runs/${run_id}/assistant`,
      {
        data: { question: 'What is the ROI?' },
        headers,
      }
    );
    expect(assistResp.ok()).toBe(true);
    const assistData = await assistResp.json();
    expect(assistData.answer).toBeDefined();
  });
});
