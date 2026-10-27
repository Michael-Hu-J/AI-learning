#!/usr/bin/env python3
# check_test_ready.py - 检查测试准备情况
"""
检查测试准备情况脚本
功能：检查所有测试所需的必要条件是否都已就绪
"""
import sys
import os
import subprocess
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import Logger

logger = Logger().get_logger()


def check_command(command: str, description: str) -> tuple[bool, str]:
    """检查命令是否可用"""
    try:
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True, result.stdout.strip() or "已安装"
        else:
            return False, result.stderr.strip() or "未安装"
    except FileNotFoundError:
        return False, "命令不存在"
    except Exception as e:
        return False, str(e)


def check_adb_device() -> tuple[bool, str]:
    """检查ADB设备连接"""
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # 跳过第一行"List of devices attached"
            devices = [line for line in lines if line.strip() and 'device' in line]
            if devices:
                device_id = devices[0].split()[0]
                return True, f"设备已连接: {device_id}"
            else:
                return False, "未检测到已连接的设备"
        else:
            return False, "ADB命令执行失败"
    except Exception as e:
        return False, str(e)


def check_appium_server() -> tuple[bool, str]:
    """检查Appium服务器是否运行"""
    try:
        # 先检查端口是否在监听
        result = subprocess.run(
            ["lsof", "-i", ":4723"],
            capture_output=True,
            text=True,
            timeout=3
        )
        if result.returncode == 0 and result.stdout.strip():
            # 端口在监听，再检查HTTP状态
            try:
                import requests
                response = requests.get("http://localhost:4723/wd/hub/status", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    version = data.get('value', {}).get('build', {}).get('version', 'unknown')
                    return True, f"Appium服务器运行中 (版本: {version}, 端口: 4723)"
                else:
                    return True, "Appium服务器运行中 (端口: 4723，但状态检查失败)"
            except:
                return True, "Appium服务器运行中 (端口: 4723)"
        
        return False, "Appium服务器未运行（请启动: appium）"
    except FileNotFoundError:
        # lsof命令不存在，使用requests直接检查
        try:
            import requests
            response = requests.get("http://localhost:4723/wd/hub/status", timeout=2)
            if response.status_code == 200:
                return True, "Appium服务器运行中 (端口: 4723)"
            else:
                return False, "Appium服务器未运行"
        except:
            return False, "Appium服务器未运行（请启动: appium）"
    except Exception as e:
        return False, f"检查Appium服务器失败: {str(e)}"


def check_python_package(package_name: str, import_name: str = None) -> tuple[bool, str]:
    """检查Python包是否安装"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        return True, "已安装"
    except ImportError:
        return False, "未安装"


def check_env_file() -> tuple[bool, str]:
    """检查.env文件是否存在"""
    env_file = Path(".env")
    if env_file.exists():
        return True, f".env文件存在 ({env_file.absolute()})"
    else:
        return False, ".env文件不存在"


def check_test_cases() -> tuple[bool, str]:
    """检查测试用例是否存在"""
    yaml_dir = Path("testcases/yaml")
    if yaml_dir.exists():
        yaml_files = list(yaml_dir.rglob("*.yaml"))
        if yaml_files:
            return True, f"找到 {len(yaml_files)} 个YAML测试用例文件"
        else:
            return False, "testcases/yaml目录下没有YAML文件"
    else:
        return False, "testcases/yaml目录不存在"


def check_pages_dir() -> tuple[bool, str]:
    """检查pages目录是否存在"""
    pages_dir = Path("pages")
    if pages_dir.exists():
        page_files = list(pages_dir.glob("*_page.py"))
        if page_files:
            return True, f"找到 {len(page_files)} 个Page Object文件"
        else:
            return True, "pages目录存在（但还没有Page Object文件，会在需要时自动生成）"
    else:
        return False, "pages目录不存在"


def check_tests_dir() -> tuple[bool, str]:
    """检查tests目录是否存在"""
    tests_dir = Path("tests")
    if tests_dir.exists():
        test_files = list(tests_dir.glob("test_*.py"))
        if test_files:
            return True, f"找到 {len(test_files)} 个测试文件"
        else:
            return True, "tests目录存在（但还没有测试文件，会在需要时自动生成）"
    else:
        return False, "tests目录不存在"


def get_app_package_info() -> tuple[bool, str]:
    """获取当前运行的应用包信息"""
    try:
        # 获取当前前台应用
        result = subprocess.run(
            ["adb", "shell", "dumpsys", "window", "windows"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            output = result.stdout
            # 查找当前焦点窗口
            for line in output.split('\n'):
                if 'mCurrentFocus' in line or 'mFocusedApp' in line:
                    # 提取包名
                    if '/' in line:
                        package = line.split('/')[0].split()[-1]
                        if package and '.' in package:
                            return True, f"当前应用: {package}"
            return False, "无法获取当前应用信息"
        else:
            return False, "无法获取应用信息"
    except Exception as e:
        return False, str(e)


def main():
    """主函数"""
    print("=" * 70)
    print(" 检查测试准备情况")
    print("=" * 70)
    print()
    
    checks = []
    
    # 1. 检查ADB
    print("1 检查ADB...")
    adb_ok, adb_msg = check_command("adb version", "ADB")
    status = "" if adb_ok else ""
    print(f"   {status} {adb_msg}")
    checks.append(("ADB", adb_ok))
    print()
    
    # 2. 检查设备连接
    print("2 检查Android设备连接...")
    device_ok, device_msg = check_adb_device()
    status = "" if device_ok else ""
    print(f"   {status} {device_msg}")
    checks.append(("设备连接", device_ok))
    
    if device_ok:
        # 获取当前应用信息
        app_ok, app_msg = get_app_package_info()
        if app_ok:
            print(f"   ℹ  {app_msg}")
    print()
    
    # 3. 检查Appium服务器
    print("3 检查Appium服务器...")
    appium_ok, appium_msg = check_appium_server()
    status = "" if appium_ok else ""
    print(f"   {status} {appium_msg}")
    checks.append(("Appium服务器", appium_ok))
    print()
    
    # 4. 检查Python依赖
    print("4 检查Python依赖包...")
    packages = [
        ("appium", "appium"),
        ("selenium", "selenium"),
        ("pytest", "pytest"),
        ("allure", "allure"),
        ("yaml", "yaml"),
        ("requests", "requests"),
    ]
    all_packages_ok = True
    for pkg_name, import_name in packages:
        pkg_ok, pkg_msg = check_python_package(pkg_name, import_name)
        status = "" if pkg_ok else ""
        print(f"   {status} {pkg_name}: {pkg_msg}")
        if not pkg_ok:
            all_packages_ok = False
    checks.append(("Python依赖", all_packages_ok))
    print()
    
    # 5. 检查.env文件
    print("5 检查环境配置...")
    env_ok, env_msg = check_env_file()
    status = "" if env_ok else ""
    print(f"   {status} {env_msg}")
    checks.append(("环境配置", env_ok))
    print()
    
    # 6. 检查测试用例
    print("6 检查测试用例...")
    cases_ok, cases_msg = check_test_cases()
    status = "" if cases_ok else ""
    print(f"   {status} {cases_msg}")
    checks.append(("测试用例", cases_ok))
    print()
    
    # 7. 检查目录结构
    print("7 检查目录结构...")
    pages_ok, pages_msg = check_pages_dir()
    status = "" if pages_ok else ""
    print(f"   {status} pages目录: {pages_msg}")
    
    tests_ok, tests_msg = check_tests_dir()
    status = "" if tests_ok else ""
    print(f"   {status} tests目录: {tests_msg}")
    checks.append(("目录结构", pages_ok and tests_ok))
    print()
    
    # 总结
    print("=" * 70)
    print(" 检查结果总结")
    print("=" * 70)
    
    critical_checks = ["ADB", "设备连接", "Appium服务器", "Python依赖"]
    all_critical_ok = all(
        ok for name, ok in checks if name in critical_checks
    )
    
    for name, ok in checks:
        status = "" if ok else ("" if name in critical_checks else "")
        print(f"{status} {name}")
    
    print()
    print("=" * 70)
    
    if all_critical_ok:
        print(" 所有关键条件都已满足，可以开始测试！")
        print()
        print(" 开始测试：")
        print("   python scripts/run_test.py --type ui --platform android testcases/yaml/xxx.yaml")
        print()
        print("   或者使用pytest：")
        print("   export PLATFORM=android")
        print("   export TEST_TYPE=ui")
        print("   pytest tests/ -v -m android")
        return 0
    else:
        print(" 部分关键条件未满足，请先解决上述问题")
        print()
        if not device_ok:
            print(" 提示：请确认Android设备已通过USB连接并启用USB调试")
        if not appium_ok:
            print(" 提示：请启动Appium服务器: appium")
        if not all_packages_ok:
            print(" 提示：请安装缺失的Python包: pip3 install -r requirements.txt")
        return 1


if __name__ == "__main__":
    sys.exit(main())

