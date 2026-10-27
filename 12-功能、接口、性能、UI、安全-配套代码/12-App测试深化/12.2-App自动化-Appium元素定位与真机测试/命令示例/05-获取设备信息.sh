# 连接 Android 真机/模拟器
adb devices
# 输出: 0123456789ABCDEF  device

# 查看 Android 版本
adb shell getprop ro.build.version.release
# 输出: 14

# 查看 App 包名和启动 Activity
adb shell dumpsys window | grep mCurrentFocus
# 输出类似: mCurrentFocus=Window{... com.example.app/.MainActivity}
# 包名: com.example.app
# Activity: .MainActivity
