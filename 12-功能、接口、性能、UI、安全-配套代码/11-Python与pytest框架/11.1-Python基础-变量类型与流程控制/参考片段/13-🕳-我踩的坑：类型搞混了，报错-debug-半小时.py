data = api_response.json()
print(type(data["count"]))   # <class 'str'>？那你得转成 int 再计算
