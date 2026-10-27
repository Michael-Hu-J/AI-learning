$ docker ps
CONTAINER ID   IMAGE             STATUS          PORTS                               NAMES
a1b2c3d4e5f6   mysql:8.0         Up 30 seconds   0.0.0.0:3306->3306/tcp              seckill_mysql_1
f6e5d4c3b2a1   redis:7           Up 30 seconds   0.0.0.0:6379->6379/tcp              seckill_redis_1
x9y8z7w6v5u4   seckill_app:latest Up 28 seconds  0.0.0.0:5000->5000/tcp              seckill_app_1

$ curl http://localhost:5000
<!DOCTYPE html><html>...<title>进销存系统 - 登录</title>...</html>
