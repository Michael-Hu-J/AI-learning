# test_gesture_operations.py - 手势操作测试用例
"""
手势操作测试用例
覆盖：滑动、点击、滚动、捏合、扩张、长按、轻拂

运行方式：
  pytest tests/test_gesture_operations.py -v --tb=short
  pytest tests/test_gesture_operations.py -v -k "swipe or pinch"

注意：
- 部分手势在华为设备上可能因安全限制失败（如向右轻拂）
- 拖拽操作需要特定参数格式，建议使用 driver.swipe() 替代
"""
import pytest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import Logger

logger = Logger().get_logger()


class TestGestureOperations:
    """手势操作测试类"""

    def test_swipe_up(self, driver):
        """测试：向上滑动一屏"""
        logger.info("=== 测试：向上滑动 ===")
        size = driver.get_window_size()
        driver.swipe(
            start_x=size['width']//2,
            start_y=int(size['height'] * 0.8),
            end_x=size['width']//2,
            end_y=int(size['height'] * 0.2),
            duration=1000
        )
        logger.info("✅ 向上滑动完成")
        time.sleep(1)

    def test_swipe_down(self, driver):
        """测试：向下滑动一屏"""
        logger.info("=== 测试：向下滑动 ===")
        size = driver.get_window_size()
        driver.swipe(
            start_x=size['width']//2,
            start_y=int(size['height'] * 0.2),
            end_x=size['width']//2,
            end_y=int(size['height'] * 0.8),
            duration=1000
        )
        logger.info("✅ 向下滑动完成")
        time.sleep(1)

    def test_flick_up(self, driver):
        """测试：快速向上轻拂"""
        logger.info("=== 测试：快速向上轻拂 ===")
        size = driver.get_window_size()
        driver.execute_script('mobile: flingGesture', {
            'left': size['width'] // 2,
            'top': int(size['height'] * 0.8),
            'width': size['width'] // 2,
            'height': int(size['height'] * 0.2),
            'direction': 'up',
            'speed': 5000
        })
        logger.info("✅ 向上轻拂完成")
        time.sleep(0.5)

    def test_flick_left(self, driver):
        """测试：向左轻拂（翻页/删除场景）"""
        logger.info("=== 测试：向左轻拂 ===")
        size = driver.get_window_size()
        driver.swipe(
            start_x=int(size['width'] * 0.8),
            start_y=size['height']//2,
            end_x=int(size['width'] * 0.2),
            end_y=size['height']//2,
            duration=100
        )
        logger.info("✅ 向左轻拂完成")
        time.sleep(0.5)

    def test_tap(self, driver):
        """测试：点击（Tap）"""
        logger.info("=== 测试：点击 ===")
        size = driver.get_window_size()
        driver.tap([(size['width']//2, size['height']//2)], 100)
        logger.info("✅ 点击完成")
        time.sleep(0.5)

    def test_pinch_in(self, driver):
        """测试：双指向内捏合（缩小）"""
        logger.info("=== 测试：双指向内捏合（缩小）===")
        size = driver.get_window_size()
        center_x = size['width'] // 2
        center_y = size['height'] // 2
        offset = 200
        driver.execute_script('mobile: pinchCloseGesture', {
            'left': center_x - offset,
            'top': center_y - offset,
            'width': offset * 2,
            'height': offset * 2,
            'percent': 1.0,
            'speed': 1000
        })
        logger.info("✅ 捏合完成")
        time.sleep(1)

    def test_pinch_out(self, driver):
        """测试：双指向外扩张（放大）"""
        logger.info("=== 测试：双指向外扩张（放大）===")
        size = driver.get_window_size()
        center_x = size['width'] // 2
        center_y = size['height'] // 2
        offset = 200
        driver.execute_script('mobile: pinchOpenGesture', {
            'left': center_x - offset,
            'top': center_y - offset,
            'width': offset * 2,
            'height': offset * 2,
            'percent': 1.0,
            'speed': 1000
        })
        logger.info("✅ 扩张完成")
        time.sleep(1)

    def test_long_press(self, driver):
        """测试：长按（Long Press）"""
        logger.info("=== 测试：长按 ===")
        size = driver.get_window_size()
        driver.execute_script('mobile: longClickGesture', {
            'x': size['width'] // 2,
            'y': size['height'] // 2,
            'duration': 2000
        })
        logger.info("✅ 长按完成")
        time.sleep(1)

    def test_scroll(self, driver):
        """测试：滚动"""
        logger.info("=== 测试：滚动 ===")
        size = driver.get_window_size()
        driver.execute_script('mobile: scrollGesture', {
            'left': size['width']//2,
            'top': int(size['height'] * 0.8),
            'width': size['width']//2,
            'height': int(size['height'] * 0.2),
            'direction': 'down',
            'percent': 1.0,
            'speed': 1000
        })
        logger.info("✅ 滚动完成")
        time.sleep(1)
