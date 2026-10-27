# 你 rebase 之后发现乱了，想回到 rebase 之前
git rebase --abort
# 直接取消 rebase，回到 rebase 之前的状态

# 如果已经 rebase 完了，想找回原来的分支
git reflog
# 你会看到 rebase 之前的 commit hash
# 然后：
git reset --hard <那个hash>
