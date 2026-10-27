# 运行测试，生成 allure 结果
pytest --alluredir=./allure-results

# 生成并打开报告
allure serve ./allure-results
