# 轮询等待异步任务完成，最长等 30 秒
import time

max_retry = 10  # 最多等 10 次
retry = 0

while retry < max_retry:
    status = check_task_status()
    if status == "completed":
        print("✅ 任务完成")
        break
    retry += 1
    time.sleep(3)  # 等 3 秒再查

if retry == max_retry:
    print("❌ 任务超时")
