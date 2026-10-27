import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 50,
  duration: '30s',
  thresholds: {
    http_req_duration: ['p(95)<1000'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const res = http.post('http://localhost:5000/api/seckill/order', JSON.stringify({
    seckillId: 1,
    quantity: 1
  }), {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer <token>'
    }
  });

  check(res, {
    '状态码是200': (r) => r.status === 200,
    '响应时间 < 1000ms': (r) => r.timings.duration < 1000,
  });

  sleep(1);
}
