# reflog 长这样：
git reflog
# abc1234 HEAD@{0}: rebase finished: returning to refs/heads/feature
# def5678 HEAD@{1}: rebase: 你的提交 2
# ghi9012 HEAD@{2}: rebase: 你的提交 1
# jkl3456 HEAD@{3}: checkout: moving from main to feature

# 想回到 rebase 之前？
git reset --hard jkl3456
