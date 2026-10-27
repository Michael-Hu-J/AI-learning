# 安装 App
adb install app-release.apk

# 卸载 App
adb uninstall com.example.app

# 看当前前台 Activity（你在测哪个页面）
adb shell dumpsys window | grep mCurrentFocus

# 看日志（实时输出，加过滤）
adb logcat -v time | grep "ERROR\|Exception"
adb logcat -v time | grep "com.example.app"

# 清空日志（重新开始看）
adb logcat -c

# 截图
adb shell screencap /sdcard/screenshot.png
adb pull /sdcard/screenshot.png .

# 录屏
adb shell screenrecord /sdcard/test.mp4   # Ctrl+C 停止
adb pull /sdcard/test.mp4 .

# 模拟点击
adb shell input tap 500 1000              # 点击坐标 (500, 1000)

# 模拟滑动
adb shell input swipe 500 1500 500 500    # 从(500,1500)滑到(500,500)

# 模拟输入
adb shell input text "hello"

# 按返回键
adb shell input keyevent 4

# 按 Home 键
adb shell input keyevent 3

# 打开某个页面
adb shell am start -n com.example.app/.MainActivity
