用 Python+requests 写了抢购链路自动化脚本。
接口返回数据后，用 pymysql 直接查 seckill_orders 和 orders 两张表做双重验证。
发现接口返回成功 ≠ 数据库正确，这是很多接口测试会漏的环节。
