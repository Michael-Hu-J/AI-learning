# 按平均查询时间排序，取前 10 条
mysqldumpslow -s at -t 10 /var/lib/mysql/slow.log

# 按查询次数排序，取前 10 条（找到最常被调用的慢 SQL）
mysqldumpslow -s c -t 10 /var/lib/mysql/slow.log

# 按总耗时排序
mysqldumpslow -s t -t 10 /var/lib/mysql/slow.log
