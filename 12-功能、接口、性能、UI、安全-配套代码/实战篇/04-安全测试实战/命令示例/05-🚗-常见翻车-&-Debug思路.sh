# 错误写法：用了双引号包 JSON，里面又有双引号
curl -X POST ... -d "{'username': \"' OR 1=1 --\"}"
# 这样 json 解析会失败

# 正确写法：外面单引号，里面双引号
curl -X POST ... -d '{"username": "'\'' OR 1=1 --"}'
