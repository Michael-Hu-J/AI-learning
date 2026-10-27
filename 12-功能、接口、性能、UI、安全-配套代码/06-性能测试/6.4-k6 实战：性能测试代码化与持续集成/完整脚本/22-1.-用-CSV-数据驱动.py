import { check, sleep } from 'k6';
import http from 'k6/http';
import { SharedArray } from 'k6/data';

// 加载 CSV 数据
const users = new SharedArray('users', function() {
    return CSV.open('/data/users.csv');
});

export const options = {
    vus: 50,
    duration: '1m',
};

export default function () {
    // 每个 VU 随机取一个用户
    const user = users[Math.floor(Math.random() * users.length)];
    
    const res = http.post('http://test-api.example.com/api/login', JSON.stringify({
        username: user.username,
        password: user.password
    }), {
        headers: { 'Content-Type': 'application/json' }
    });
    
    check(res, {
        '登录成功': (r) => r.status === 200,
    });
    
    sleep(1);
}
