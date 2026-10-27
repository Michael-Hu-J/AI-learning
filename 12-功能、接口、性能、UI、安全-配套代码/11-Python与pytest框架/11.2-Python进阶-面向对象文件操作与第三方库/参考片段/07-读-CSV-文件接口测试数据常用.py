import csv

with open("test_cases.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(f"用例：{row['name']}")
        print(f"  请求：{row['method']} {row['url']}")
        print(f"  期望状态码：{row['expect_code']}")
