# 方法 1：一直盯着日志
adb logcat -v time | grep -E "FATAL|CRASH|ANR|Exception"

# 方法 2：先清空，崩溃后查看
adb logcat -c
# ... 操作 App 直到崩溃 ...
adb logcat -d | grep -E "FATAL|CRASH|ANR" > crash.log

# 方法 3：过滤某个 App
adb logcat -v time | grep $(adb shell ps | grep "com.example.app" | awk '{print $2}')
