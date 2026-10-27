// test_login.js
import http from 'k6/http';
import { check, sleep } from 'k6';

// 压测配置
export const options = {
  vus: 100,        // 100 个并发用户
  duration: '30s', // 压 30 秒
};

// 压测逻辑
export default function () {
  const res = http.post('http://test-api.example.com/api/v1/user/login', JSON.stringify({
    username: 'admin',
    password: 'Admin1234'
  }), {
    headers: { 'Content-Type': 'application/json' }
  });

  // 断言
  check(res, {
    '状态码是 200': (r) => r.status === 200,
    '响应时间 < 500ms': (r) => r.timings.duration < 500,
    '返回 code=0': (r) => JSON.parse(r.body).code === 0,
  });

  sleep(1); // 每个用户间隔 1 秒
}
