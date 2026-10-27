# 开启 GPU 渲染分析
adb shell setprop debug.hwui.profile true

# 用自动化操作 App，然后拉取数据
adb shell dumpsys gfxinfo com.example.app > gfx_info.txt
