from crewai.tools import BaseTool
from typing import Dict, Any, Optional, List
from datetime import datetime
import os


class UITestTool(BaseTool):
    """UI 测试工具类"""
    
    name: str = "ui_test"
    description: str = """执行 Selenium UI 测试，用于测试 Web 界面。
    参数包括：url(页面地址), action(操作类型), selector(CSS 选择器), 
    value(输入值), expected_text(期望文本)"""
    
    def _run(
        self,
        url: str,
        action: str = "navigate",
        selector: Optional[str] = None,
        value: Optional[str] = None,
        expected_text: Optional[str] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """执行 UI 测试"""
        start_time = datetime.now()
        
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException, NoSuchElementException
        except ImportError:
            return {
                "success": False,
                "error": "Selenium 未安装，请运行：pip install selenium webdriver-manager"
            }
        
        # 初始化 Chrome WebDriver
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # 无头模式
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(timeout)
        
        result = {
            "success": False,
            "action": action,
            "url": url,
            "steps": []
        }
        
        try:
            # 导航到页面
            if action == "navigate":
                driver.get(url)
                result["success"] = True
                result["current_url"] = driver.current_url
                result["title"] = driver.title
                result["steps"].append(f"导航到 {url} 成功")
            
            # 点击元素
            elif action == "click":
                driver.get(url)
                element = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                element.click()
                result["success"] = True
                result["steps"].append(f"点击 {selector} 成功")
            
            # 输入文本
            elif action == "input":
                driver.get(url)
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                element.clear()
                element.send_keys(value or "")
                result["success"] = True
                result["steps"].append(f"在 {selector} 输入 {value} 成功")
            
            # 检查文本
            elif action == "check_text":
                driver.get(url)
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                actual_text = element.text
                result["success"] = expected_text is None or expected_text in actual_text
                result["actual_text"] = actual_text
                result["expected_text"] = expected_text
                result["steps"].append(f"检查文本：期望 '{expected_text}', 实际 '{actual_text}'")
            
            # 截图
            elif action == "screenshot":
                driver.get(url)
                screenshot_path = f"/tmp/ui_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                driver.save_screenshot(screenshot_path)
                result["success"] = True
                result["screenshot_path"] = screenshot_path
                result["steps"].append(f"截图保存到 {screenshot_path}")
            
            else:
                result["error"] = f"未知的操作类型：{action}"
            
        finally:
            driver.quit()
        
        end_time = datetime.now()
        result["response_time_ms"] = round((end_time - start_time).total_seconds() * 1000, 2)
        result["timestamp"] = start_time.isoformat()
        
        return result

result = tool._run(
    url="http://your-server:port",
    action="navigate"
)

# 输出：
{
    "success": True,
    "current_url": "http://your-server:port",
    "title": "CrewAI 测试平台",
    "steps": ["导航到 http://your-server:port 成功"]
}

result = tool._run(
    url="http://your-server:port",
    action="click",
    selector="#start-test-btn"  # CSS 选择器
)

# 输出：
{
    "success": True,
    "steps": ["点击 #start-test-btn 成功"]
}

result = tool._run(
    url="http://your-server:port",
    action="input",
    selector="#requirement-input",
    value="秒杀系统需求：\n1. 用户可以在指定时间参与秒杀"
)

# 输出：
{
    "success": True,
    "steps": ["在 #requirement-input 输入 '秒杀系统需求...' 成功"]
}

result = tool._run(
    url="http://your-server:port",
    action="check_text",
    selector=".status-text",
    expected_text="测试完成"
)

# 输出：
{
    "success": True,
    "actual_text": "测试完成",
    "expected_text": "测试完成",
    "steps": ["检查文本：期望 '测试完成', 实际 '测试完成'"]
}

result = tool._run(
    url="http://your-server:port",
    action="screenshot"
)

# 输出：
{
    "success": True,
    "screenshot_path": "/tmp/ui_screenshot_20260419_143025.png"
}

from crewai import Agent
from app.tools.ui_test_tool import UITestTool

ui_tester = Agent(
    role="UI 测试工程师",
    goal="执行 UI 自动化测试",
    backstory="你有 3 年 Selenium 测试经验",
    tools=[UITestTool()],
    verbose=True
)

from crewai import Task

ui_task = Task(
    description="""
请测试以下页面功能：

1. 导航到首页 http://your-server:port
2. 检查页面标题是否包含"CrewAI"
3. 点击"开始测试"按钮
4. 在需求输入框输入测试内容
5. 截图保存

记录每一步的执行结果。
""",
    expected_output="UI 测试报告",
    agent=ui_tester
)

from crewai import Crew

crew = Crew(agents=[ui_tester], tasks=[ui_task], verbose=True)
result = crew.kickoff()
print(result)

# 1. 检查选择器是否正确
#  错误
selector = ".btn"  # 太模糊

#  正确
selector = "#start-test-btn"  # 使用 ID

# 2. 增加等待时间
result = tool._run(
    url=url,
    action="click",
    selector="#start-test-btn",
    timeout=60  # 增加到 60 秒
)

# 3. 使用显式等待
WebDriverWait(driver, 30).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
)

# 增加超时时间
result = tool._run(
    url=url,
    action="navigate",
    timeout=60  # 增加到 60 秒
)

# 或者设置页面加载超时
driver.set_page_load_timeout(60)

#  最佳：使用 ID
selector = "#start-test-btn"

#  次佳：使用 Class
selector = ".btn-primary"

#  谨慎：使用 XPath
selector = "//button[@id='start-test-btn']"

driver.implicitly_wait(10)  # 全局等待 10 秒

WebDriverWait(driver, 30).until(
    EC.element_to_be_clickable((By.ID, "start-test-btn"))
)

options.add_argument('--headless')  # 无界面运行

# 注释掉无头模式，可以看到浏览器
# options.add_argument('--headless')
