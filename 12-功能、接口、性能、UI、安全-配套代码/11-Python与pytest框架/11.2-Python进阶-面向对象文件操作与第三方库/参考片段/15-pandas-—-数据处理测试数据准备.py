import pandas as pd

# 从 CSV 读测试数据
df = pd.read_csv("test_cases.csv")

# 筛选
failed_cases = df[df["status"] == "FAIL"]
print(f"失败用例：{len(failed_cases)} 条")

# 导出结果
df.to_excel("test_report.xlsx", index=False)
