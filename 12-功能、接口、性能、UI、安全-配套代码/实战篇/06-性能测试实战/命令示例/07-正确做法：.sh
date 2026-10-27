# 1. 在 JMeter GUI 里添加 "Simple Data Writer" 或 "Save Responses to a file"
# 2. 或者运行 CLI 模式（非 GUI），自动保存结果
jmeter -n -t seckill_test.jmx -l results.jtl -e -o reports/
# -n: 非GUI模式
# -t: 测试计划文件
# -l: 结果文件
# -e: 生成HTML报告
# -o: 报告输出目录
