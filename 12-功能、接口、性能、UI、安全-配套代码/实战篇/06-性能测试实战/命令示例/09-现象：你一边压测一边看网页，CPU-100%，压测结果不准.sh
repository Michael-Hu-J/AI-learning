# CLI 模式跑，别开 GUI
jmeter -n -t test_plan.jmx -l result.jtl

# 如果并发数很大，用分布式压测
# 1台机器跑 JMeter Controller，多台机器跑 JMeter Server
