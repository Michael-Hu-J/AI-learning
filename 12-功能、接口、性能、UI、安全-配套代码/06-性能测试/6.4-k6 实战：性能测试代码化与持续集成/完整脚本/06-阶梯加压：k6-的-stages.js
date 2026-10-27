export const options = {
  stages: [
    { duration: '30s', target: 50 },   // 爬坡：30 秒内加到 50 并发
    { duration: '1m', target: 200 },   // 高压：1 分钟内加到 200 并发
    { duration: '2m', target: 200 },   // 稳定：保持 200 并发压 2 分钟
    { duration: '30s', target: 0 },    // 回收：30 秒内降到 0
  ],
};
