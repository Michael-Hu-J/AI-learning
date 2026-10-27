# 读文件
with open("文件路径", "r", encoding="utf-8") as f:
    content = f.read()

# 写文件（覆盖）
with open("文件路径", "w", encoding="utf-8") as f:
    f.write("内容")

# 追加写
with open("文件路径", "a", encoding="utf-8") as f:
    f.write("新增内容\n")
