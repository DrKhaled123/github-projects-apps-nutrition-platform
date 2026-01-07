const puppeteer = require('puppeteer');
const chalk = require('chalk');

const BASE_URL = process.env.BASE_URL || 'http://localhost:8081';

// Test configuration
const TEST_TIMEOUT = 30000; // 30 seconds
const RETRY_ATTEMPTS = 3;
const RETRY_DELAY = 2000; // 2 seconds

// Test results
let testResults = {
  passed: 0,
  failed: 0,
  skipped: 0,
  total: 0,
  details: []
};

async function runTest(testName, testFunction, retries = RETRY_ATTEMPTS) {
  testResults.total++;
  
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      console.log(chalk.blue(`Running ${testName} (attempt ${attempt}/${retries})...`));
      await testFunction();
      console.log(chalk.green(`✓ ${testName} passed`));
      testResults.passed++;
      testResults.details.push({ name: testName, status: 'passed', attempt });
      return true;
    } catch (error) {
      console.log(chalk.yellow(`✗ ${testName} failed (attempt ${attempt}): ${error.message}`));
      if (attempt === retries) {
        console.log(chalk.red(`✗ ${testName} failed after ${retries} attempts`));
        testResults.failed++;
        testResults.details.push({ 
          name: testName, 
          status: 'failed', 
          error: error.message, 
          attempts: retries 
        });
        return false;
      }
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
    }
  }
}

async function testHomePage(browser) {
  const page = await browser.newPage();
  try {
    await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
    
    // Check if page loads successfully
    const title = await page.title();
    if (!title) throw new Error('Page title not found');
    
    // Check for key elements
    const navElements = await page.$$('nav a');
    if (navElements.length === 0) throw new Error('Navigation elements not found');
    
    // Check if the page is responsive
    const viewport = page.viewport();
    if (!viewport) throw new Error('Viewport not set');
    
    console.log(`Page title: ${title}`);
    console.log(`Navigation elements found: ${navElements.length}`);
    
  } finally {
    await page.close();
  }
}

async function testHealthEndpoints(browser) {
  const page = await browser.newPage();
  try {
    // Test basic health endpoint
    const healthResponse = await page.goto(`${BASE_URL}/health`);
    if (!healthResponse.ok()) throw new Error(`Health endpoint returned ${healthResponse.status()}`);
    
    const healthData = await page.evaluate(() => {
      try {
        return JSON.parse(document.body.innerText);
      } catch {
        return null;
      }
    });
    
    if (!healthData) throw new Error('Health endpoint returned invalid JSON');
    
    // Test detailed health endpoint
    const detailedHealthResponse = await page.goto(`${BASE_URL}/health/detailed`);
    if (!detailedHealthResponse.ok()) throw new Error(`Detailed health endpoint returned ${detailedHealthResponse.status()}`);
    
    // Test readiness endpoint
    const readyResponse = await page.goto(`${BASE_URL}/ready`);
    if (!readyResponse.ok()) throw new Error(`Readiness endpoint returned ${readyResponse.status()}`);
    
    console.log('All health endpoints are responding correctly');
    
  } finally {
    await page.close();
  }
}

async function testStaticPages(browser) {
  const pages = [
    '/diet.html',
    '/workouts.html',
    '/recipes.html',
    '/lifestyle.html',
    '/pricing.html',
    '/home.html'
  ];
  
  for (const pagePath of pages) {
    const page = await browser.newPage();
    try {
      const response = await page.goto(`${BASE_URL}${pagePath}`, { waitUntil: 'networkidle2' });
      if (!response.ok()) throw new Error(`Page ${pagePath} returned ${response.status()}`);
      
      // Check if page has content
      const hasContent = await page.evaluate(() => {
        return document.body.innerText.length > 100;
      });
      
      if (!hasContent) throw new Error(`Page ${pagePath} appears to be empty`);
      
      console.log(`✓ Static page ${pagePath} loaded successfully`);
      
    } finally {
      await page.close();
    }
  }
}

async function testAPIEndpoints(browser) {
  const page = await browser.newPage();
  try {
    // Test API health endpoint
    const apiResponse = await page.goto(`${BASE_URL}/api/v1/health`, {
      waitUntil: 'networkidle2'
    });
    
    if (!apiResponse.ok()) throw new Error(`API health endpoint returned ${apiResponse.status()}`);
    
    const apiData = await page.evaluate(() => {
      try {
        return JSON.parse(document.body.innerText);
      } catch {
        return null;
      }
    });
    
    if (!apiData) throw new Error('API health endpoint returned invalid JSON');
    
    console.log('✓ API health endpoint is responding correctly');
    
  } finally {
    await page.close();
  }
}

async function testPagePerformance(browser) {
  const page = await browser.newPage();
  try {
    // Enable performance monitoring
    await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
    
    const metrics = await page.metrics();
    
    // Check key performance metrics
    if (metrics.LayoutDuration > 100) {
      throw new Error(`Layout duration too high: ${metrics.LayoutDuration}ms`);
    }
    
    if (metrics.ScriptDuration > 500) {
      throw new Error(`Script duration too high: ${metrics.ScriptDuration}ms`);
    }
    
    // Get page load time
    const navigationTiming = await page.evaluate(() => {
      const timing = window.performance.timing;
      return {
        loadTime: timing.loadEventEnd - timing.navigationStart,
        domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
        firstPaint: performance.getEntriesByType('paint')[0]?.startTime || 0
      };
    });
    
    if (navigationTiming.loadTime > 3000) {
      throw new Error(`Page load time too high: ${navigationTiming.loadTime}ms`);
    }
    
    console.log(`Page load time: ${navigationTiming.loadTime}ms`);
    console.log(`DOM content loaded: ${navigationTiming.domContentLoaded}ms`);
    console.log(`First paint: ${navigationTiming.firstPaint}ms`);
    
  } finally {
    await page.close();
  }
}

async function testErrorHandling(browser) {
  const page = await browser.newPage();
  try {
    // Test 404 handling
    const response = await page.goto(`${BASE_URL}/non-existent-page`);
    if (response.status() !== 404 && response.status() !== 200) {
      throw new Error(`Unexpected status for non-existent page: ${response.status()}`);
    }
    
    // Test malformed API endpoint
    const apiResponse = await page.goto(`${BASE_URL}/api/v1/non-existent-endpoint`);
    if (apiResponse.status() !== 404 && apiResponse.status() !== 200) {
      throw new Error(`Unexpected status for non-existent API endpoint: ${apiResponse.status()}`);
    }
    
    console.log('✓ Error handling is working correctly');
    
  } finally {
    await page.close();
  }
}

async function runSmokeTests() {
  console.log(chalk.blue('🚀 Starting smoke tests...'));
  console.log(chalk.gray(`Target URL: ${BASE_URL}`));
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    defaultViewport: { width: 1920, height: 1080 }
  });
  
  try {
    // Run all tests
    await runTest('Home Page', () => testHomePage(browser));
    await runTest('Health Endpoints', () => testHealthEndpoints(browser));
    await runTest('Static Pages', () => testStaticPages(browser));
    await runTest('API Endpoints', () => testAPIEndpoints(browser));
    await runTest('Page Performance', () => testPagePerformance(browser));
    await runTest('Error Handling', () => testErrorHandling(browser));
    
  } finally {
    await browser.close();
  }
  
  // Print results
  console.log('\n' + chalk.blue('📊 Test Results Summary'));
  console.log(chalk.blue('======================='));
  console.log(`Total tests: ${testResults.total}`);
  console.log(chalk.green(`Passed: ${testResults.passed}`));
  console.log(chalk.red(`Failed: ${testResults.failed}`));
  console.log(chalk.yellow(`Skipped: ${testResults.skipped}`));
  
  if (testResults.failed > 0) {
    console.log('\n' + chalk.red('❌ Failed Tests:'));
    testResults.details
      .filter(test => test.status === 'failed')
      .forEach(test => {
        console.log(chalk.red(`  - ${test.name}: ${test.error}`));
      });
  }
  
  // Exit with appropriate code
  if (testResults.failed > 0) {
    console.log('\n' + chalk.red('🚨 Smoke tests failed!'));
    process.exit(1);
  } else {
    console.log('\n' + chalk.green('✅ All smoke tests passed!'));
    process.exit(0);
  }
}

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

// Handle timeout
const timeout = setTimeout(() => {
  console.error(chalk.red('⏰ Smoke tests timed out!'));
  process.exit(1);
}, TEST_TIMEOUT);

// Run tests
runSmokeTests().then(() => {
  clearTimeout(timeout);
}).catch(error => {
  clearTimeout(timeout);
  console.error(chalk.red('💥 Smoke tests crashed:'), error);
  process.exit(1);
});
