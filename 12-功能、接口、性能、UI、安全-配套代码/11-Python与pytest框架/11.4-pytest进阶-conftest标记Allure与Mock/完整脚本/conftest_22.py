"ERROR: file not found"
→ 检查文件名是不是 test_ 开头

"fixture 'xxx' not found"
→ 检查 conftest.py 路径对不对，拼写对不对

"ModuleNotFoundError: No module named 'xxx'"
→ pip install xxx 安装缺失的包

"DeprecationWarning: ..."
→ 版本不兼容，pip install --upgrade pytest
