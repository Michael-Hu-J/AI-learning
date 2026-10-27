// perf-seckill.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 50 },    // 爬坡：30秒加到50并发
    { duration: '1m', target: 200 },    // 高压：1分钟加到200并发
    { duration: '2m', target: 200 },    // 稳定：保持200并发压2分钟
    { duration: '30s', target: 0 },     // 回收：30秒降到0
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],    // P95必须<500ms
    http_req_failed: ['rate<0.01'],      // 错误率<1%
  },
};

const BASE = 'http://localhost:5001';

export default function () {
  // 1. 登录
  const loginRes = http.post(`${BASE}/api/auth/login`, JSON.stringify({
    username: `test${__VU}`,
    password: 'Test123456'
  }), { headers: { 'Content-Type': 'application/json' } });
  
  const token = loginRes.json('data.token');
  const headers = { 
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  };
  
  // 2. 查商品
  http.get(`${BASE}/api/products`, { headers });
  
  // 3. 抢购
  const seckillRes = http.post(`${BASE}/api/seckill/purchase`, JSON.stringify({
    product_id: 1,
    quantity: 1
  }), { headers });
  
  check(seckillRes, {
    '抢购成功或库存不足': (r) => 
      r.json('code') === 0 || r.json('message') === '库存不足',
    '响应时间<500ms': (r) => r.timings.duration < 500,
  });
  
  sleep(0.5);
}
