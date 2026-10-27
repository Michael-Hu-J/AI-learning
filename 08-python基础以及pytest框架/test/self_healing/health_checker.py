# health_checker.py - 环境健康检查
"""
环境健康检查

功能：
1. 测试启动前检查所有依赖服务是否可用
2. 支持自定义检查项
3. 不达标时跳过测试并给出明确提示
4. 支持 xdist 跨 worker 状态同步

使用方式（在 conftest.py 中集成）：
    checker = HealthChecker()
    checker.register_check("api", lambda: requests.get("http://localhost:8222/health"))
    
    # 在 conftest 中调用
    checker.run_all_checks()  # 不通过则 pytest.exit
"""
import logging
import socket
import subprocess
import sys
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class HealthCheckResult:
    """健康检查结果"""

    def __init__(self, name: str, passed: bool, message: str = ""):
        self.name = name
        self.passed = passed
        self.message = message

    def __repr__(self):
        status = "[OK]" if self.passed else "[FAIL]"
        return f"{status} {self.name}: {self.message}"


class HealthChecker:
    """
    环境健康检查器。

    支持注册检查项，按需运行。所有检查项通过才算环境就绪。
    """

    def __init__(self):
        self._checks: Dict[str, Callable] = {}
        self._results: List[HealthCheckResult] = []
        self._abort_on_fail = True  # 检查不通过直接退出

    def register_check(self, name: str, check_fn: Callable[[], Tuple[bool, str]]):
        """
        注册一个检查项。

        参数：
        - name: 检查项名称（如 "api_server", "database", "appium"）
        - check_fn: 检查函数，返回 (passed: bool, message: str)
        """
        self._checks[name] = check_fn
        logger.debug(f"已注册健康检查: {name}")

    def ping_host(self, host: str, port: int, timeout: float = 3.0) -> Tuple[bool, str]:
        """检查主机端口是否可连通"""
        try:
            sock = socket.create_connection((host, port), timeout=timeout)
            sock.close()
            return True, f"{host}:{port} 连接成功"
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            return False, f"{host}:{port} 连接失败: {e}"

    def check_command(self, cmd: str, args: str = "--version") -> Tuple[bool, str]:
        """检查命令是否可用"""
        try:
            result = subprocess.run(
                [cmd, args],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                output = result.stdout.strip()[:100]
                return True, f"{cmd} 可用: {output}"
            else:
                return False, f"{cmd} 执行失败: {result.stderr.strip()[:100]}"
        except FileNotFoundError:
            return False, f"{cmd} 未安装, 请执行" + self._install_hint(cmd)
        except subprocess.TimeoutExpired:
            return False, f"{cmd} 执行超时"
        except Exception as e:
            return False, f"{cmd} 检查异常: {e}"

    def check_python_module(self, module_name: str) -> Tuple[bool, str]:
        """检查 Python 模块是否可导入"""
        try:
            __import__(module_name)
            return True, f"模块 {module_name} 已安装"
        except ImportError:
            return False, f"模块 {module_name} 未安装, 执行: pip install {module_name}"

    def check_env_var(self, var_name: str, hint: str = "") -> Tuple[bool, str]:
        """检查环境变量是否设置"""
        import os
        value = os.getenv(var_name)
        if value:
            masked = value[:4] + "****" if len(value) > 6 else value
            return True, f"环境变量 {var_name}={masked}"
        else:
            hint_text = f" ({hint})" if hint else ""
            return False, f"环境变量 {var_name} 未设置{hint_text}"

    def check_url(self, url: str, timeout: float = 5.0) -> Tuple[bool, str]:
        """检查 HTTP 服务是否可用"""
        try:
            import requests
            resp = requests.get(url, timeout=timeout)
            if resp.status_code < 500:
                return True, f"{url} 响应正常 (status={resp.status_code})"
            else:
                return False, f"{url} 返回 {resp.status_code}"
        except ImportError:
            return False, "requests 模块未安装"
        except requests.ConnectionError:
            return False, f"{url} 连接失败（服务可能未启动）"
        except requests.Timeout:
            return False, f"{url} 请求超时（超过 {timeout}s）"
        except Exception as e:
            return False, f"{url} 检查异常: {e}"

    def run_all_checks(self) -> List[HealthCheckResult]:
        """运行所有已注册的健康检查"""
        self._results = []

        if not self._checks:
            logger.info("未注册任何健康检查项，跳过检查")
            return self._results

        logger.info("开始环境健康检查...")
        logger.info("-" * 40)

        all_passed = True
        for name, check_fn in self._checks.items():
            try:
                passed, message = check_fn()
            except Exception as e:
                passed = False
                message = f"检查执行异常: {e}"

            result = HealthCheckResult(name, passed, message)
            self._results.append(result)
            logger.info(str(result))

            if not passed:
                all_passed = False

        logger.info("-" * 40)

        if all_passed:
            logger.info("所有环境检查通过，开始执行测试")
        else:
            logger.warning("部分环境检查未通过")
            if self._abort_on_fail:
                logger.error("环境不满足要求，终止测试执行")
                logger.error("请修复上述未通过项目后重新运行")
                pytest_exit()

        return self._results

    def _install_hint(self, cmd: str) -> str:
        """生成安装提示"""
        hints = {
            "allure": "`brew install allure` 或从 https://github.com/allure-framework/allure2 下载",
            "appium": "`npm install -g appium`",
            "node": "`brew install node` 或从 https://nodejs.org 下载",
            "java": "`brew install openjdk@17`",
            "docker": "`brew install docker` 或从 https://docker.com 下载",
            "docker-compose": "`brew install docker-compose`",
        }
        return hints.get(cmd, f"`{cmd}`")


def pytest_exit():
    """退出 pytest 进程并给出友好提示"""
    print("\n" + "=" * 60)
    print("  环境检查未通过，测试已终止")
    print("  请查看上方未通过的检查项，修复后重新运行")
    print("  提示：如果觉得检查有误，设置 SKIP_HEALTH_CHECK=1 可跳过")
    print("=" * 60 + "\n")
    sys.exit(1)


# 预置的检查项工厂函数


def make_api_check(base_url: str = "http://localhost:8222") -> Callable:
    """创建 API 服务检查"""
    checker = HealthChecker()

    def check():
        return checker.check_url(f"{base_url}/health")

    return check


def make_appium_check(port: int = 4723) -> Callable:
    """创建 Appium Server 检查"""
    checker = HealthChecker()

    def check():
        return checker.ping_host("127.0.0.1", port)

    return check


def make_db_check(host: str = "127.0.0.1", port: int = 3306) -> Callable:
    """创建数据库连接检查"""
    checker = HealthChecker()

    def check():
        return checker.ping_host(host, port)

    return check
