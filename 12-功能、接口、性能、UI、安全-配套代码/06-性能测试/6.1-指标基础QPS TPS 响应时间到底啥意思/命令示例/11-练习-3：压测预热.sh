# 先预热（让缓存生效）
for i in {1..50}; do
  curl -s http://test-api.example.com/api/products > /dev/null
done

# 再记录数据
echo "预热完成，可以开始压测了"
