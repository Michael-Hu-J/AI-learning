# 查看 App CPU 占用
adb shell top -n 1 | grep com.example.app

# 行业标准
# 静止状态：< 5%
# 操作状态：< 30%
# 动画/加载：< 50%
