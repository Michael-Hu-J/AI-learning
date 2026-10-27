# 安装
sudo apt install k6 -y

# 验证
k6 version

# 跑一个快速测试
k6 run - <<EOF
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  vus: 10,
  duration: '10s',
};

export default function () {
  const res = http.get('https://httpbin.org/get');
  check(res, {
    '状态码是 200': (r) => r.status === 200,
    '响应时间 < 500ms': (r) => r.timings.duration < 500,
  });
}
EOF
