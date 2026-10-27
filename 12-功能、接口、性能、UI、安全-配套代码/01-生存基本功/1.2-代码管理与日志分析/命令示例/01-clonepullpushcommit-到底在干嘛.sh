# 把项目从远程拉下来
git clone https://github.com/xxx/test-project.git

# 看看改了什么
git status

# 把改动的文件加到暂存区
git add test_script.py

# 提交到本地仓库（写清楚改了什么）
git commit -m "修复登录接口自动化脚本的断言逻辑"

# 推送到远程仓库
git push
