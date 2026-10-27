# 查自己的用户信息
curl http://localhost:5000/api/users/1 \
  -H "Authorization: Bearer ***"

# 查其他用户的信息
curl http://localhost:5000/api/users/2 \
  -H "Authorization: Bearer ***"
