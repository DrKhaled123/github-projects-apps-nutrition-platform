import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
export let errorRate = new Rate('errors');

// Test configuration
export let options = {
  stages: [
    { duration: '2m', target: 10 }, // Ramp up to 10 users
    { duration: '5m', target: 10 }, // Stay at 10 users
    { duration: '2m', target: 50 }, // Ramp up to 50 users
    { duration: '5m', target: 50 }, // Stay at 50 users
    { duration: '2m', target: 100 }, // Ramp up to 100 users
    { duration: '5m', target: 100 }, // Stay at 100 users
    { duration: '2m', target: 0 }, // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests under 500ms
    http_req_failed: ['rate<0.1'], // Error rate under 10%
    errors: ['rate<0.1'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8081';

export default function () {
  // Test health endpoint
  let healthResponse = http.get(`${BASE_URL}/health`);
  let healthCheck = check(healthResponse, {
    'health endpoint status is 200': (r) => r.status === 200,
    'health response time < 200ms': (r) => r.timings.duration < 200,
  });
  errorRate.add(!healthCheck);

  // Test main page
  let mainPageResponse = http.get(`${BASE_URL}/`);
  let mainPageCheck = check(mainPageResponse, {
    'main page status is 200': (r) => r.status === 200,
    'main page response time < 500ms': (r) => r.timings.duration < 500,
  });
  errorRate.add(!mainPageCheck);

  // Test API endpoints
  let apiHealthResponse = http.get(`${BASE_URL}/api/v1/health`, {
    headers: { 'Content-Type': 'application/json' },
  });
  let apiHealthCheck = check(apiHealthResponse, {
    'API health status is 200': (r) => r.status === 200,
    'API health response time < 300ms': (r) => r.timings.duration < 300,
  });
  errorRate.add(!apiHealthCheck);

  // Test diet page
  let dietResponse = http.get(`${BASE_URL}/diet.html`);
  let dietCheck = check(dietResponse, {
    'diet page status is 200': (r) => r.status === 200,
    'diet page response time < 500ms': (r) => r.timings.duration < 500,
  });
  errorRate.add(!dietCheck);

  // Test workouts page
  let workoutsResponse = http.get(`${BASE_URL}/workouts.html`);
  let workoutsCheck = check(workoutsResponse, {
    'workouts page status is 200': (r) => r.status === 200,
    'workouts page response time < 500ms': (r) => r.timings.duration < 500,
  });
  errorRate.add(!workoutsCheck);

  // Test recipes page
  let recipesResponse = http.get(`${BASE_URL}/recipes.html`);
  let recipesCheck = check(recipesResponse, {
    'recipes page status is 200': (r) => r.status === 200,
    'recipes page response time < 500ms': (r) => r.timings.duration < 500,
  });
  errorRate.add(!recipesCheck);

  // Test detailed health endpoint
  let detailedHealthResponse = http.get(`${BASE_URL}/health/detailed`);
  let detailedHealthCheck = check(detailedHealthResponse, {
    'detailed health status is 200': (r) => r.status === 200,
    'detailed health response time < 1000ms': (r) => r.timings.duration < 1000,
  });
  errorRate.add(!detailedHealthCheck);

  // Simulate user think time
  sleep(Math.random() * 3 + 1); // Random sleep between 1-4 seconds
}

export function handleSummary(data) {
  return {
    'performance-summary.json': JSON.stringify(data, null, 2),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, options) {
  const indent = options.indent || '';
  const enableColors = options.enableColors || false;
  
  let summary = `${indent}Performance Test Summary\n`;
  summary += `${indent}========================\n\n`;
  
  summary += `${indent}Total Requests: ${data.metrics.http_reqs.count}\n`;
  summary += `${indent}Failed Requests: ${data.metrics.http_req_failed.count}\n`;
  summary += `${indent}Request Rate: ${data.metrics.http_reqs.rate.toFixed(2)}/s\n`;
  summary += `${indent}Average Response Time: ${data.metrics.http_req_duration.avg.toFixed(2)}ms\n`;
  summary += `${indent}95th Percentile: ${data.metrics.http_req_duration['p(95)'].toFixed(2)}ms\n`;
  summary += `${indent}Error Rate: ${(data.metrics.http_req_failed.rate * 100).toFixed(2)}%\n\n`;
  
  summary += `${indent}Response Time Percentiles:\n`;
  summary += `${indent}  50th: ${data.metrics.http_req_duration['p(50)'].toFixed(2)}ms\n`;
  summary += `${indent}  90th: ${data.metrics.http_req_duration['p(90)'].toFixed(2)}ms\n`;
  summary += `${indent}  95th: ${data.metrics.http_req_duration['p(95)'].toFixed(2)}ms\n`;
  summary += `${indent}  99th: ${data.metrics.http_req_duration['p(99)'].toFixed(2)}ms\n`;
  
  return summary;
}
