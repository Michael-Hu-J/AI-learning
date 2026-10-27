import requests

# GET
r = requests.get("http://localhost:5001/api/products", params={"page": 1})

# POST
r = requests.post("http://localhost:5001/api/auth/login",
                  json={"username": "admin", "password": "admin123"})

# PUT
r = requests.put("http://localhost:5001/api/products/1",
                 json={"name": "手机-已修改"})

# DELETE
r = requests.delete("http://localhost:5001/api/products/1")
