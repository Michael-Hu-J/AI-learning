# 加一个敏感路径爆破功能
for path in admin debug test api-docs swagger .git .env backup; do
  curl -s -o /dev/null -w "%{http_code} %{url_effective}\n" "$BASE/$path"
done
# 如果返回 200 而不是 404，说明这个路径可以被访问
