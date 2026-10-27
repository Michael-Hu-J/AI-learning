import requests

# 错误写法
response = requests.post(url, data={"userId": 100})

# 正确写法
response = requests.post(url, json={"userId": 100})
# 或者
response = requests.post(url, data=json.dumps({"userId": 100}), 
                         headers={"Content-Type": "application/json"})
