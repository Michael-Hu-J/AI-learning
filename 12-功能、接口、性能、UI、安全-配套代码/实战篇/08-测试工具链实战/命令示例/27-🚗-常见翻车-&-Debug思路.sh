# 1. 检查文件路径对不对
# .github/workflows/test.yml 必须在仓库根目录下
# 注意：.github 前面有个点！

# 2. 检查 YAML 格式
# 缩进必须用空格，不能用 Tab
# on / jobs / steps 层级对不对

# 3. 检查分支名
# on.push.branches 写的是 [main] 还是 [master]？
# GitHub 新建仓库默认分支是 main，老仓库可能是 master
