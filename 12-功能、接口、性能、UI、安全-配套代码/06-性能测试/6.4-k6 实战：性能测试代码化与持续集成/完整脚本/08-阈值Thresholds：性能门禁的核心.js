export const options = {
  vus: 100,
  duration: '1m',
  thresholds: {
    http_req_duration: ['p(95)<500'],     // P95 必须 < 500ms
    http_req_failed: ['rate<0.001'],       // 错误率必须 < 0.1%
    http_req_duration: ['p(99)<1000'],     // P99 必须 < 1 秒
    http_reqs: ['rate>50'],                // TPS 必须 > 50
  },
};
