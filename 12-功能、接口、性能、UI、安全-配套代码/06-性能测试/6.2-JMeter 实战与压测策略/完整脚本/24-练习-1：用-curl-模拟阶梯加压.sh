#!/bin/bash
# 模拟 JMeter 的阶梯加压（不需要 GUI）

for concurrent in 10 50 100 200 500; do
  echo "=== 并发数: $concurrent ==="
  total_time=0
  success=0
  
  for i in $(seq 1 $concurrent); do
    start=$(date +%s%N)
    code=$(curl -s -o /dev/null -w "%{http_code}" http://test-api.example.com/api/health)
    end=$(date +%s%N)
    elapsed=$(( (end - start) / 1000000 ))  # ms
    
    if [ "$code" == "200" ]; then
      success=$((success + 1))
    fi
    
    total_time=$((total_time + elapsed))
  done
  
  avg_time=$((total_time / concurrent))
  echo "平均响应时间: ${avg_time}ms"
  echo "成功率: $((success * 100 / concurrent))%"
  echo ""
  sleep 2  # 间隔休息
done
