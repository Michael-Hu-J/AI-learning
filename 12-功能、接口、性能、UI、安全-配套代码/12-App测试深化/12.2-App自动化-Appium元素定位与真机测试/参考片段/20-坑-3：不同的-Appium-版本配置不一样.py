# Appium 1.x（旧写法）
desired_caps = {
    "platformName": "Android",
    "deviceName": "emulator-5554",
    "appPackage": "com.example.app",
    "appActivity": ".MainActivity",
    "noReset": True
}
driver = webdriver.Remote("http://localhost:4723/wd/hub", desired_caps)

# Appium 2.x（新写法，推荐）
options = UiAutomator2Options()
options.platform_name = "Android"
# ...
driver = webdriver.Remote("http://localhost:4723", options=options)
