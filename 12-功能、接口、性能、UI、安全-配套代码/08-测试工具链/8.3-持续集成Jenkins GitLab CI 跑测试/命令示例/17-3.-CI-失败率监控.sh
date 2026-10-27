# 每周跑一次，统计 CI 失败率
# 失败率 = 失败构建数 / 总构建数

#!/bin/bash
# ci_health_check.sh

TOTAL_BUILDS=$(curl -s "http://jenkins/api/json?tree=jobs[name,lastBuild[result]]" | \
  jq '.jobs | length')
FAILED_BUILDS=$(curl -s "http://jenkins/api/json?tree=jobs[name,lastBuild[result]]" | \
  jq '[.jobs[] | select(.lastBuild.result == "FAILURE")] | length')

FAILURE_RATE=$(echo "scale=2; $FAILED_BUILDS * 100 / $TOTAL_BUILDS" | bc)

echo "总构建数: $TOTAL_BUILDS"
echo "失败构建数: $FAILED_BUILDS"
echo "失败率: ${FAILURE_RATE}%"

if (( $(echo "$FAILURE_RATE > 10" | bc -l) )); then
    echo "⚠️ 失败率超过 10%，需要排查！"
    # 发送告警通知
fi
