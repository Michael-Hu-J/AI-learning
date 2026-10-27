# gesture_helper.py - 手势操作工具类
"""
手势操作工具类
功能：封装高级手势操作（拖拽、捏合、轻拂、滚动到文本等）
通俗理解：这是一个"指尖舞蹈"工具，包含了所有复杂的多点触控手势操作

W3C Actions API说明：
- 基于W3C WebDriver规范的标准手势API
- 使用 PointerInput + ActionChains 构建精确的手势序列
- 支持多指触控（Multi-touch）
- 兼容 Selenium 4.11+ 和 Appium 2.x
"""
from typing import Tuple, Optional, List
import time
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.mouse_button import MouseButton
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from utils.logger import Logger

logger = Logger().get_logger()


class GestureHelper:
    """
    手势操作工具类
    
    作用：
    1. 封装高级多指触控手势（拖拽、捏合等）
    2. 基于W3C Actions API实现，替代已废弃的TouchAction
    3. 提供便捷的高频手势方法
    
    使用方式：
    gesture = GestureHelper(driver)
    gesture.drag_and_drop(source, target)
    gesture.pinch_in()    # 双指捏合（缩小）
    gesture.pinch_out()   # 双指外扩（放大）
    gesture.flick()       # 快速轻拂
    gesture.scroll_to_text("登录")  # 滚动到指定文本
    """

    def __init__(self, driver):
        """
        初始化手势工具
        
        参数说明：
        - driver: Appium WebDriver实例
        
        通俗理解：创建一个"手指"，准备在屏幕上做各种手势操作
        """
        self.driver = driver
        self._screen_size = None  # 屏幕尺寸缓存
    
    def _get_screen_size(self) -> dict:
        """
        获取屏幕尺寸（带缓存）
        
        返回：
        - dict: {'width': int, 'height': int}
        """
        if self._screen_size is None:
            self._screen_size = self.driver.get_window_size()
            logger.debug(f"获取屏幕尺寸: {self._screen_size}")
        return self._screen_size
    
    def _create_pointer_input(self, name: str = "finger") -> PointerInput:
        """
        创建一个触控指针输入设备
        
        参数说明：
        - name: 指针名称（多指操作时用于区分不同手指）
        
        返回：
        - PointerInput: 指针输入设备实例
        
        通俗理解：创建一根"手指"，指定它的名字
        """
        return PointerInput(interaction.POINTER_TOUCH, name)

    # ==================== 拖拽操作 ====================

    def drag_and_drop(self, source_element, target_element=None,
                      start_x: int = None, start_y: int = None,
                      end_x: int = None, end_y: int = None,
                      duration: int = 500):
        """
        拖拽操作（将一个元素拖到另一个元素或指定坐标位置）
        
        参数说明：
        - source_element: 要拖拽的源元素（WebElement对象）
        - target_element: 目标元素（拖到该元素上，可选，与坐标二选一）
        - start_x: 起始X坐标（省略则使用源元素的中心点）
        - start_y: 起始Y坐标（省略则使用源元素的中心点）
        - end_x: 目标X坐标（省略则使用目标元素的中心点）
        - end_y: 目标Y坐标（省略则使用目标元素的中心点）
        - duration: 拖拽持续时间（毫秒），值越大拖拽越慢
        
        通俗理解：按住一个东西把它拖到另一个地方，像把桌面图标拖到文件夹里
        
        使用示例：
        # 方式1：元素拖到元素
        gesture.drag_and_drop(source_btn, target_area)
        
        # 方式2：元素拖到坐标
        gesture.drag_and_drop(source_btn, end_x=500, end_y=800)
        
        # 方式3：指定坐标拖到坐标
        gesture.drag_and_drop(start_x=200, start_y=300, end_x=500, end_y=800)
        """
        try:
            # 确定起始坐标
            if source_element is not None and start_x is None and start_y is None:
                rect = source_element.rect
                start_x = rect['x'] + rect['width'] // 2
                start_y = rect['y'] + rect['height'] // 2
                logger.debug(f"源元素中心坐标: ({start_x}, {start_y})")
            elif start_x is None or start_y is None:
                raise ValueError("起始坐标不完整，请提供 source_element 或完整的 start_x/start_y")

            # 确定目标坐标
            if target_element is not None and end_x is None and end_y is None:
                rect = target_element.rect
                end_x = rect['x'] + rect['width'] // 2
                end_y = rect['y'] + rect['height'] // 2
                logger.debug(f"目标元素中心坐标: ({end_x}, {end_y})")
            elif end_x is None or end_y is None:
                raise ValueError("目标坐标不完整，请提供 target_element 或完整的 end_x/end_y")

            # 使用 W3C Actions API 构建拖拽动作
            finger = self._create_pointer_input("drag_finger")
            actions = ActionChains(self.driver)
            actions.w3c_actions.add_pointer_input(finger)
            
            # 第一步：移动到起始位置并按住
            finger.pointer_move(x=start_x, y=start_y)
            finger.pointer_down(button=MouseButton.LEFT)
            finger.pause(duration / 1000.0)

            # 第二步：平滑移动到目标位置（拆分为多步）
            steps = max(1, duration // 100)
            for i in range(1, steps + 1):
                progress = i / steps
                current_x = int(start_x + (end_x - start_x) * progress)
                current_y = int(start_y + (end_y - start_y) * progress)
                finger.pointer_move(x=current_x, y=current_y)

            # 第三步：松开
            finger.pointer_up(button=MouseButton.LEFT)

            actions.perform()
            logger.info(f"拖拽操作完成: ({start_x}, {start_y}) -> ({end_x}, {end_y}), 耗时{duration}ms")
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"拖拽操作失败: {str(e)}")
            raise

    def drag_and_drop_fast(self, source_element, target_element=None,
                           start_x: int = None, start_y: int = None,
                           end_x: int = None, end_y: int = None):
        """
        快速拖拽操作（使用 ActionChains 简化版）
        
        参数说明：同 drag_and_drop
        
        通俗理解：快速把东西拖到另一个地方，适合简单的拖拽场景
        
        注意：此方法适用于简单的拖拽，复杂场景请使用 drag_and_drop
        """
        try:
            if source_element is not None and start_x is None and start_y is None:
                rect = source_element.rect
                start_x = rect['x'] + rect['width'] // 2
                start_y = rect['y'] + rect['height'] // 2

            if target_element is not None and end_x is None and end_y is None:
                rect = target_element.rect
                end_x = rect['x'] + rect['width'] // 2
                end_y = rect['y'] + rect['height'] // 2

            # ActionChains 链式调用
            actions = ActionChains(self.driver)
            actions \
                .w3c_actions \
                .pointer_action \
                .move_to_location(start_x, start_y) \
                .pointer_down() \
                .move_to_location(end_x, end_y) \
                .release()
            actions.perform()

            logger.info(f"快速拖拽完成: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"快速拖拽失败: {str(e)}")
            raise

    # ==================== 捏合操作 ====================

    def pinch_in(self, start_x: int = None, start_y: int = None,
                 distance: int = 200, duration: int = 500):
        """
        双指向内捏合（缩小画面/缩小视图）
        
        参数说明：
        - start_x: 捏合中心X坐标（默认屏幕中心）
        - start_y: 捏合中心Y坐标（默认屏幕中心）
        - distance: 两指移动距离（像素），越大缩得越多
        - duration: 捏合持续时间（毫秒）
        
        通俗理解：两个手指往中间捏，像把图片缩小
        
        手势原理：
        - 手指1：从中心左上方往中心移动
        - 手指2：从中心右下方往中心移动
        """
        try:
            size = self._get_screen_size()
            center_x = start_x if start_x is not None else size['width'] // 2
            center_y = start_y if start_y is not None else size['height'] // 2
            
            offset = distance // 2
            
            # 手指1起始位置：中心左上方，结束位置：中心
            f1_start_x = center_x - offset
            f1_start_y = center_y - offset
            f1_end_x = center_x
            f1_end_y = center_y
            
            # 手指2起始位置：中心右下方，结束位置：中心
            f2_start_x = center_x + offset
            f2_start_y = center_y + offset
            f2_end_x = center_x
            f2_end_y = center_y
            
            # 创建两根手指
            finger1 = self._create_pointer_input("pinch_finger_1")
            finger2 = self._create_pointer_input("pinch_finger_2")
            
            # 手指1：从外围移动到中心
            finger1.pointer_move(x=f1_start_x, y=f1_start_y)
            finger1.pointer_down(button=MouseButton.LEFT)
            finger1.pause(duration / 2000.0)
            
            # 手指2：从外围移动到中心
            finger2.pointer_move(x=f2_start_x, y=f2_start_y)
            finger2.pointer_down(button=MouseButton.LEFT)
            finger2.pause(duration / 2000.0)
            
            # 同时移动到中心
            steps = max(1, duration // 100)
            for i in range(1, steps + 1):
                progress = i / steps
                fx1 = int(f1_start_x + (f1_end_x - f1_start_x) * progress)
                fy1 = int(f1_start_y + (f1_end_y - f1_start_y) * progress)
                finger1.pointer_move(x=fx1, y=fy1)
                
                fx2 = int(f2_start_x + (f2_end_x - f2_start_x) * progress)
                fy2 = int(f2_start_y + (f2_end_y - f2_start_y) * progress)
                finger2.pointer_move(x=fx2, y=fy2)
            
            # 同时松开
            finger1.pointer_up(button=MouseButton.LEFT)
            finger2.pointer_up(button=MouseButton.LEFT)
            
            # 执行动作（按顺序 perform）
            action1 = ActionChains(self.driver)
            action1.w3c_actions.add_pointer_input(finger1)
            action2 = ActionChains(self.driver)
            action2.w3c_actions.add_pointer_input(finger2)
            action1.perform()
            action2.perform()
            
            logger.info(f"向内捏合完成: 中心({center_x}, {center_y}), 距离{distance}px")
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"向内捏合失败: {str(e)}")
            raise

    def pinch_out(self, start_x: int = None, start_y: int = None,
                  distance: int = 200, duration: int = 500):
        """
        双指向外扩张（放大画面/放大视图）
        
        参数说明：
        - start_x: 扩张中心X坐标（默认屏幕中心）
        - start_y: 扩张中心Y坐标（默认屏幕中心）
        - distance: 两指移动距离（像素），越大放得越多
        - duration: 扩张持续时间（毫秒）
        
        通俗理解：两个手指往外扩，像把图片放大
        
        手势原理：
        - 手指1：从中心往左上方移动
        - 手指2：从中心往右下方移动
        """
        try:
            size = self._get_screen_size()
            center_x = start_x if start_x is not None else size['width'] // 2
            center_y = start_y if start_y is not None else size['height'] // 2
            
            offset = distance // 2
            
            # 两根手指都从中心开始
            f_start_x = center_x
            f_start_y = center_y
            
            # 手指1结束位置：中心左上方
            f1_end_x = center_x - offset
            f1_end_y = center_y - offset
            
            # 手指2结束位置：中心右下方
            f2_end_x = center_x + offset
            f2_end_y = center_y + offset
            
            # 创建两根手指
            finger1 = self._create_pointer_input("pinch_out_finger_1")
            finger2 = self._create_pointer_input("pinch_out_finger_2")
            
            # 两根手指都从中心开始
            finger1.pointer_move(x=f_start_x, y=f_start_y)
            finger1.pointer_down(button=MouseButton.LEFT)
            finger1.pause(duration / 2000.0)
            
            finger2.pointer_move(x=f_start_x, y=f_start_y)
            finger2.pointer_down(button=MouseButton.LEFT)
            finger2.pause(duration / 2000.0)
            
            # 同时向外移动
            steps = max(1, duration // 100)
            for i in range(1, steps + 1):
                progress = i / steps
                fx1 = int(f_start_x + (f1_end_x - f_start_x) * progress)
                fy1 = int(f_start_y + (f1_end_y - f_start_y) * progress)
                finger1.pointer_move(x=fx1, y=fy1)
                
                fx2 = int(f_start_x + (f2_end_x - f_start_x) * progress)
                fy2 = int(f_start_y + (f2_end_y - f_start_y) * progress)
                finger2.pointer_move(x=fx2, y=fy2)
            
            # 同时松开
            finger1.pointer_up(button=MouseButton.LEFT)
            finger2.pointer_up(button=MouseButton.LEFT)
            
            # 执行动作
            action1 = ActionChains(self.driver)
            action1.w3c_actions.add_pointer_input(finger1)
            action2 = ActionChains(self.driver)
            action2.w3c_actions.add_pointer_input(finger2)
            action1.perform()
            action2.perform()
            
            logger.info(f"向外扩张完成: 中心({center_x}, {center_y}), 距离{distance}px")
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"向外扩张失败: {str(e)}")
            raise

    # ==================== 轻拂操作 ====================

    def flick(self, start_x: int = None, start_y: int = None,
              end_x: int = None, end_y: int = None,
              direction: str = None, distance: int = 200,
              duration: int = 100):
        """
        轻拂操作（快速滑动）
        
        参数说明：
        - start_x: 起始X坐标（默认根据方向自动计算）
        - start_y: 起始Y坐标（默认根据方向自动计算）
        - end_x: 结束X坐标（与 direction 二选一）
        - end_y: 结束Y坐标（与 direction 二选一）
        - direction: 轻拂方向（"up", "down", "left", "right"，与坐标二选一）
        - distance: 轻拂距离（像素，仅 direction 模式使用）
        - duration: 轻拂持续时间（毫秒），值越小越快，默认100ms快速拂动
        
        通俗理解：在屏幕上快速一划，像翻书页或滑动删除
        
        使用示例：
        # 方式1：指定方向
        gesture.flick(direction="up")         # 向上轻拂
        gesture.flick(direction="left")        # 向左轻拂
        
        # 方式2：指定坐标
        gesture.flick(start_x=100, start_y=500, end_x=300, end_y=500)  # 向右轻拂
        """
        try:
            size = self._get_screen_size()
            
            # 如果指定了方向，自动计算起止坐标
            if direction is not None:
                if direction == "up":
                    start_x = size['width'] // 2
                    start_y = int(size['height'] * 0.6)
                    end_x = size['width'] // 2
                    end_y = start_y - distance
                elif direction == "down":
                    start_x = size['width'] // 2
                    start_y = int(size['height'] * 0.4)
                    end_x = size['width'] // 2
                    end_y = start_y + distance
                elif direction == "left":
                    start_x = int(size['width'] * 0.7)
                    start_y = size['height'] // 2
                    end_x = start_x - distance
                    end_y = size['height'] // 2
                elif direction == "right":
                    start_x = int(size['width'] * 0.3)
                    start_y = size['height'] // 2
                    end_x = start_x + distance
                    end_y = size['height'] // 2
                else:
                    raise ValueError(f"不支持的方向: {direction}，可选: up/down/left/right")
            elif start_x is None or start_y is None or end_x is None or end_y is None:
                raise ValueError("请提供 direction 或完整的 start/end 坐标")
            
            # 使用 W3C Actions API 构建快速轻拂动作
            finger = self._create_pointer_input("flick_finger")
            actions = ActionChains(self.driver)
            actions.w3c_actions.add_pointer_input(finger)
            
            # 移动到起始位置按下
            finger.pointer_move(x=start_x, y=start_y)
            finger.pointer_down(button=MouseButton.LEFT)
            finger.pause(0.05)  # 短暂停顿，确保按下
            
            # 快速移动到目标位置
            finger.pointer_move(x=end_x, y=end_y)
            finger.pause(duration / 1000.0)
            
            # 松开
            finger.pointer_up(button=MouseButton.LEFT)
            
            actions.perform()
            
            logger.info(f"轻拂操作完成: ({start_x}, {start_y}) -> ({end_x}, {end_y}), "
                       f"耗时{duration}ms")
            time.sleep(0.3)
            
        except Exception as e:
            logger.error(f"轻拂操作失败: {str(e)}")
            raise

    def flick_element(self, element, direction: str = "left", distance: int = 150,
                      duration: int = 100):
        """
        在元素上轻拂（适用于列表项滑动删除等场景）
        
        参数说明：
        - element: 要轻拂的元素（WebElement对象）
        - direction: 轻拂方向（"left", "right", "up", "down"）
        - distance: 轻拂距离（像素）
        - duration: 持续时间（毫秒）
        
        通俗理解：在某个元素上快速滑动，比如在列表项上左滑删除
        
        使用示例：
        gesture.flick_element(list_item, direction="left")  # 左滑删除
        """
        try:
            rect = element.rect
            element_center_x = rect['x'] + rect['width'] // 2
            element_center_y = rect['y'] + rect['height'] // 2
            
            if direction == "left":
                start_x = element_center_x + rect['width'] // 4
                start_y = element_center_y
                end_x = start_x - distance
                end_y = element_center_y
            elif direction == "right":
                start_x = element_center_x - rect['width'] // 4
                start_y = element_center_y
                end_x = start_x + distance
                end_y = element_center_y
            elif direction == "up":
                start_x = element_center_x
                start_y = element_center_y + rect['height'] // 4
                end_x = start_x
                end_y = start_y - distance
            elif direction == "down":
                start_x = element_center_x
                start_y = element_center_y - rect['height'] // 4
                end_x = start_x
                end_y = start_y + distance
            else:
                raise ValueError(f"不支持的方向: {direction}")
            
            finger = self._create_pointer_input("flick_element_finger")
            actions = ActionChains(self.driver)
            actions.w3c_actions.add_pointer_input(finger)
            
            finger.pointer_move(x=start_x, y=start_y)
            finger.pointer_down(button=MouseButton.LEFT)
            finger.pause(0.05)
            finger.pointer_move(x=end_x, y=end_y)
            finger.pause(duration / 1000.0)
            finger.pointer_up(button=MouseButton.LEFT)
            
            actions.perform()
            logger.info(f"元素轻拂完成: {direction}, 距离{distance}px")
            time.sleep(0.3)
            
        except Exception as e:
            logger.error(f"元素轻拂失败: {str(e)}")
            raise

    # ==================== 滚动到文本 ====================

    def scroll_to_text(self, text: str, max_swipes: int = 10):
        """
        滚动到包含指定文本的元素
        
        参数说明：
        - text: 要查找的文本内容
        - max_swipes: 最大滑动次数，防止无限循环
        
        返回：
        - WebElement: 找到的元素，未找到返回 None
        
        通俗理解：一直滑动页面，直到找到包含指定文字的那个元素
        
        使用示例：
        element = gesture.scroll_to_text("设置")
        if element:
            element.click()
        """
        try:
            # 优先使用 Android UiScrollable（最快最精准）
            try:
                scrollable_selector = (
                    f'new UiScrollable('
                    f'new UiSelector().scrollable(true).instance(0))'
                    f'.scrollIntoView('
                    f'new UiSelector().textContains("{text}").instance(0))'
                )
                element = self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, scrollable_selector)
                logger.info(f"通过 UiScrollable 找到文本: {text}")
                return element
            except Exception:
                logger.debug("UiScrollable 方式失败，尝试 W3C Actions 滚动")
            
            # 降级方案：W3C Actions 滚动查找
            for i in range(max_swipes):
                try:
                    # 尝试通过文本查找元素
                    elements = self.driver.find_elements(AppiumBy.XPATH, f"//*[@text='{text}']")
                    if elements:
                        logger.info(f"滚动{i+1}次后找到文本: {text}")
                        return elements[0]
                    
                    # 向上滑动一屏
                    self._swipe_up()
                    time.sleep(0.3)
                except Exception:
                    continue
            
            logger.warning(f"滚动{max_swipes}次后仍未找到文本: {text}")
            return None
            
        except Exception as e:
            logger.error(f"滚动到文本失败: {str(e)}")
            return None

    def _swipe_up(self):
        """内部方法：向上滑动一屏"""
        size = self._get_screen_size()
        width = size['width']
        height = size['height']
        
        start_x = width // 2
        start_y = int(height * 0.8)
        end_y = int(height * 0.2)
        
        finger = self._create_pointer_input("swipe_finger")
        actions = ActionChains(self.driver)
        actions.w3c_actions.add_pointer_input(finger)
        
        finger.pointer_move(x=start_x, y=start_y)
        finger.pointer_down(button=MouseButton.LEFT)
        finger.pause(0.1)
        finger.pointer_move(x=start_x, y=end_y)
        finger.pause(0.3)
        finger.pointer_up(button=MouseButton.LEFT)
        
        actions.perform()
