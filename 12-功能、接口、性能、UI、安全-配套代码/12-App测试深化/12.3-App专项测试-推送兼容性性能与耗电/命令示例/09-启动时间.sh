# 冷启动（App 被杀死后打开）
adb shell am start -W com.example.app/.MainActivity
# ThisTime: 320ms  ← 启动到第一个页面显示
# TotalTime: 320ms
# WaitTime: 335ms

# 热启动（App 在后台，切回前台）
adb shell input keyevent 3  # Home 键
# ... 等几秒 ...
adb shell am start -W com.example.app/.MainActivity

# 行业标准
# 冷启动：< 1.5 秒
# 热启动：< 500ms
