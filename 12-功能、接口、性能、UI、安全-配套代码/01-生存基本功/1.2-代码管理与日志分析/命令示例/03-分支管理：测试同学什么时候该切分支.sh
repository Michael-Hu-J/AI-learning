# 看看有哪些分支
git branch

# 创建新分支
git branch feature/login-test

# 切换到新分支
git checkout feature/login-test

# 或者一步到位
git checkout -b feature/login-test

# 改完代码后，切回主分支
git checkout main

# 合并你的分支
git merge feature/login-test
