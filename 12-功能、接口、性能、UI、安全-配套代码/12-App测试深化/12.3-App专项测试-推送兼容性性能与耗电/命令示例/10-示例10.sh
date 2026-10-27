# 查看 App 内存占用
adb shell dumpsys meminfo com.example.app

# 重点关注：
# 1. Native Heap / Dalvik Heap — 堆内存
# 2. Total PSS — 实际物理内存占用
# 3. 反复操作（列表滑动、图片加载），看内存是否持续增长

# 行业标准
# 普通 App：< 200MB
# 大型 App（地图/视频）：< 400MB
# 退出页面后内存应该回落到正常水平
