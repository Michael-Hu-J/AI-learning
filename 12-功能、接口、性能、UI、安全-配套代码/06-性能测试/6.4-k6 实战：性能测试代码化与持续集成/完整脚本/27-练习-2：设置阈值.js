export const options = {
  vus: 100,
  duration: '30s',
  thresholds: {
    http_req_duration: ['p(95)<500'],  // P95 必须 < 500ms
    http_req_failed: ['rate<0.001'],   // 错误率必须 < 0.1%
  },
};
