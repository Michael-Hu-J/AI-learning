import allure

@allure.feature("登录模块")
@allure.story("正常登录")
@allure.title("管理员可以正常登录")
@allure.severity(allure.severity_level.BLOCKER)
def test_admin_login(base_url):
    ...

@allure.feature("商品管理")
@allure.story("创建商品")
@allure.title("创建商品后能正确查询到")
@pytest.mark.parametrize("name", ["手机", "电脑", "平板"])
def test_create_and_query(name, base_url, admin_token):
    with allure.step("创建商品"):
        ...
    with allure.step("查询商品列表"):
        ...
    with allure.step("验证新商品在列表中"):
        ...
    with allure.step("清理测试数据"):
        ...
