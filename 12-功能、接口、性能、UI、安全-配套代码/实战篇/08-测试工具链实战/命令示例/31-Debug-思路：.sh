# 1. 看 Actions 的完整日志
# 点进失败的步骤，展开看详细输出

# 2. 本地复现
# 在本地跑同样的步骤，看能不能复现
python test_main_flow.py

# 3. 常见原因：
#    - schema.sql 没有初始化成功 → 检查 database initialize 步骤的日志
#    - 应用启动后还没完全就绪，测试就开始跑了 → 加 sleep
#    - 环境变量不对 → 检查 env 里的值
