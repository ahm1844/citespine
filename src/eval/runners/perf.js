import http from 'k6/http';
import { sleep, check } from 'k6';

export const options = {
  scenarios: {
    steady_usage: {
      executor: 'ramping-arrival-rate',
      startRate: 5,      // requests/min
      timeUnit: '1m',
      preAllocatedVUs: 10,
      maxVUs: 30,
      stages: [
        { duration: '2m', target: 10 },
        { duration: '5m', target: 20 },
        { duration: '3m', target: 10 }
      ],
      tags: { scenario: 'query' }
    }
  },
  thresholds: {
    http_req_duration: [
      'p(50)<2500',  // P50 ≤ 2.5s
      'p(95)<8000'   // P95 ≤ 8s
    ],
    http_req_failed: ['rate<0.01']
  },
  summaryTrendStats: ['avg','min','med','max','p(90)','p(95)']
};

export default function () {
  const url = 'http://api:8000/query'; // service name in Compose network
  const payload = JSON.stringify({
    q: "What does PCAOB require for ICFR audits?",
    filters: { framework: "Other", jurisdiction: "US", doc_type: "standard", authority_level: "authoritative", as_of: "2024-12-31" },
    top_k: 10, probes: 15
  });
  const res = http.post(url, payload, { headers: { 'Content-Type': 'application/json' } });
  check(res, { '200': (r) => r.status === 200 });
  sleep(1);
}
