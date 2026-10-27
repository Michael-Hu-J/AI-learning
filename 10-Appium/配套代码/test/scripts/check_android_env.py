#!/usr/bin/env python3
# check_android_env.py - Android测试环境检查脚本
"""
Android测试环境检查脚本
检查所有必需的软件和依赖是否已安装
"""
import os
import subprocess
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import Logger

logger = Logger().get_logger()


def check_command(command, name, version_flag="--version"):
    """检查命令是否可用"""
    try:
        result = subprocess.run([command, version_flag], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip() or result.stderr.strip()
            return True, version.split('\n')[0] if version else "已安装"
        return False, None
    except FileNotFoundError:
        return False, None
    except Exception as e:
        return False, f"检查出错: {str(e)}"


def check_python_package(package_name):
    """检查Python包是否已安装"""
    try:
        import_name = package_name.replace("-", "_")
        __import__(import_name)
        return True
    except ImportError:
        return False


def check_adb_devices():
    """检查ADB设备连接"""
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]
            devices = [line for line in lines if line.strip() and 'device' in line]
            authorized = [d for d in devices if 'device' in d and 'unauthorized' not in d]
            return len(authorized), len(devices) - len(authorized)
        return 0, 0
    except Exception:
        return 0, 0


def main():
    """主函数"""
    print("=" * 70)
    print(" Android测试环境检查")
    print("=" * 70)
    print()
    
    results = {}
    
    # 1. 检查ADB
    print("1  检查ADB（Android Debug Bridge）...")
    success, version = check_command("adb", "ADB")
    if success:
        print(f"    ADB已安装: {version}")
        results["ADB"] = True
    else:
        print("    ADB未安装")
        print("     安装方法: 安装Android Studio或Android SDK Platform Tools")
        results["ADB"] = False
    print()
    
    # 2. 检查Android SDK
    print("2  检查Android SDK...")
    sdk_paths = [
        os.getenv("ANDROID_HOME"),
        os.getenv("ANDROID_SDK_ROOT"),
        os.path.expanduser("~/Library/Android/sdk"),
        os.path.expanduser("~/Android/Sdk"),
    ]
    sdk_found = False
    for sdk_path in sdk_paths:
        if sdk_path and os.path.exists(sdk_path):
            print(f"    Android SDK路径: {sdk_path}")
            results["Android SDK"] = True
            sdk_found = True
            break
    if not sdk_found:
        print("    Android SDK未找到")
        print("     安装方法: 安装Android Studio（会自动安装SDK）")
        print("     或单独下载: https://developer.android.com/studio")
        results["Android SDK"] = False
    print()
    
    # 3. 检查Java
    print("3  检查Java/JDK...")
    success, version = check_command("java", "Java", "-version")
    if success:
        print(f"    Java已安装")
        print(f"      {version}")
        results["Java"] = True
    else:
        print("    Java/JDK未安装")
        print("     安装方法: brew install openjdk@11")
        print("     或下载: https://www.oracle.com/java/technologies/downloads/")
        results["Java"] = False
    print()
    
    # 4. 检查Node.js
    print("4  检查Node.js...")
    success, version = check_command("node", "Node.js")
    if success:
        print(f"    Node.js已安装: {version}")
        results["Node.js"] = True
        
        # 检查npm
        npm_success, npm_version = check_command("npm", "npm")
        if npm_success:
            print(f"    npm已安装: {npm_version}")
        else:
            print("     npm未安装（Node.js通常自带npm）")
    else:
        print("    Node.js未安装")
        print("     安装方法: brew install node")
        print("     或下载: https://nodejs.org/")
        results["Node.js"] = False
    print()
    
    # 5. 检查Appium
    print("5  检查Appium Server...")
    success, version = check_command("appium", "Appium")
    if success:
        print(f"    Appium已安装: {version}")
        results["Appium"] = True
    else:
        print("    Appium未安装")
        print("     安装方法: npm install -g appium")
        print("     安装UiAutomator2驱动: appium driver install uiautomator2")
        results["Appium"] = False
    print()
    
    # 6. 检查Python环境
    print("6  检查Python环境...")
    python_version = sys.version.split()[0]
    print(f"    Python版本: {python_version}")
    results["Python"] = True
    print()
    
    # 7. 检查Python依赖
    print("7  检查Python依赖包...")
    required_packages = {
        "pytest": "pytest",
        "appium": "Appium-Python-Client",
        "selenium": "selenium",
        "allure-pytest": "allure-pytest",
        "requests": "requests",
        "pyyaml": "PyYAML",
        "xmindparser": "xmindparser",
        "opencv-python": "opencv-python",
        "Pillow": "Pillow",
        "scikit-image": "scikit-image",
        "numpy": "numpy",
        "python-dotenv": "python-dotenv",
    }
    
    missing_packages = []
    for import_name, package_name in required_packages.items():
        if check_python_package(import_name):
            print(f"    {package_name}")
        else:
            print(f"    {package_name} (未安装)")
            missing_packages.append(package_name)
    
    if missing_packages:
        print()
        print(f"     缺少 {len(missing_packages)} 个依赖包")
        print(f"   安装命令: pip install {' '.join(missing_packages)}")
        results["Python依赖"] = False
    else:
        print()
        print("    所有Python依赖已安装")
        results["Python依赖"] = True
    print()
    
    # 8. 检查设备连接
    print("8  检查Android设备连接...")
    authorized, unauthorized = check_adb_devices()
    if authorized > 0:
        print(f"    发现 {authorized} 个已授权设备")
        results["设备连接"] = True
    elif unauthorized > 0:
        print(f"     发现 {unauthorized} 个未授权设备")
        print("     提示: 请在手机上点击'允许USB调试'")
        results["设备连接"] = False
    else:
        print("    未检测到已连接的设备")
        print("     提示: 请确认手机已连接并启用USB调试")
        results["设备连接"] = False
    print()
    
    # 总结
    print("=" * 70)
    print(" 环境检查总结")
    print("=" * 70)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    for name, status in results.items():
        icon = "" if status else ""
        print(f"{icon} {name}: {'已就绪' if status else '未就绪'}")
    
    print()
    print(f"总计: {passed}/{total} 项检查通过")
    print()
    
    if failed > 0:
        print("  还有未就绪的项，请根据上述提示进行安装")
        print()
        print(" 安装建议:")
        print()
        
        if not results.get("ADB"):
            print("1. 安装ADB:")
            print("   方式1: 安装Android Studio（推荐）")
            print("   方式2: 单独安装Android SDK Platform Tools")
            print("         下载: https://developer.android.com/tools/releases/platform-tools")
            print()
        
        if not results.get("Node.js"):
            print("2. 安装Node.js:")
            print("   brew install node")
            print()
        
        if not results.get("Appium"):
            print("3. 安装Appium:")
            print("   npm install -g appium")
            print("   appium driver install uiautomator2")
            print()
        
        if not results.get("Python依赖"):
            print("4. 安装Python依赖:")
            print("   pip install -r requirements.txt")
            print()
        
        if not results.get("设备连接"):
            print("5. 配置设备连接:")
            print("   - 在手机上启用'开发者选项'")
            print("   - 启用'USB调试'")
            print("   - 连接电脑时选择'允许USB调试'")
            print()
        
        return 1
    else:
        print(" 所有环境检查通过！可以开始测试")
        return 0


if __name__ == "__main__":
    sys.exit(main())

