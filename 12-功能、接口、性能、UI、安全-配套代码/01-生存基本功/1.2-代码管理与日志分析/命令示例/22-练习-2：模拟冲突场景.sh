# 1. 创建一个测试目录
mkdir git-conflict-test && cd git-conflict-test
git init

# 2. 创建文件
echo "第一行代码" > test.py
git add . && git commit -m "初始提交"

# 3. 创建两个分支
git checkout -b branch-a
echo "分支A的修改" >> test.py
git add . && git commit -m "A的提交"

git checkout main
git checkout -b branch-b
echo "分支B的修改" >> test.py   # 同一行
git add . && git commit -m "B的提交"

# 4. 合并（会冲突）
git checkout main
git merge branch-a
git merge branch-b
# → 你会看到 CONFLICT
