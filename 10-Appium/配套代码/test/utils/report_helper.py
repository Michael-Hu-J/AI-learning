# report_helper.py - 测试报告辅助工具
"""
测试报告辅助工具
功能：生成统一的测试报告，并自动打开报告
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
from utils.logger import Logger

logger = Logger().get_logger()


class ReportHelper:
    """测试报告辅助类"""
    
    @staticmethod
    def open_html_report(report_path: str):
        """
        自动打开HTML测试报告（也支持Markdown等文本文件）
        
        参数：
        - report_path: 报告文件路径（支持HTML、Markdown等）
        """
        if not os.path.exists(report_path):
            logger.error(f"报告文件不存在: {report_path}")
            return
        
        try:
            report_abs_path = os.path.abspath(report_path)
            logger.info(f"打开测试报告: {report_abs_path}")
            
            # 根据操作系统选择打开方式
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", report_abs_path])
            elif sys.platform == "win32":  # Windows
                os.startfile(report_abs_path)
            elif sys.platform.startswith("linux"):  # Linux
                subprocess.run(["xdg-open", report_abs_path])
            else:
                logger.warning(f"不支持的操作系统: {sys.platform}")
                logger.info(f"请手动打开报告: {report_abs_path}")
                
        except Exception as e:
            logger.error(f"打开报告失败: {str(e)}")
            logger.info(f"请手动打开报告: {os.path.abspath(report_path)}")
    
    @staticmethod
    def open_markdown_report(markdown_path: str):
        """
        打开Markdown报告（在默认Markdown查看器中打开）
        
        参数：
        - markdown_path: Markdown文件路径
        """
        ReportHelper.open_html_report(markdown_path)  # 使用相同方法
    
    @staticmethod
    def open_allure_report(allure_results_dir: str = "reports/allure-results", background: bool = False, report_dir: str = None):
        """
        使用Allure serve自动打开Allure报告
        
        参数：
        - allure_results_dir: Allure结果目录
        - background: 是否在后台运行（默认False，会阻塞直到服务器关闭）
        - report_dir: 报告输出目录（如果指定，会在该目录下生成allure-report）
        """
        if not os.path.exists(allure_results_dir):
            logger.error(f"Allure结果目录不存在: {allure_results_dir}")
            return
        
        try:
            # 如果指定了report_dir，先生成HTML报告
            if report_dir:
                allure_report_dir = os.path.join(report_dir, "allure-report")
                logger.info(f"生成Allure HTML报告到: {allure_report_dir}")
                try:
                    subprocess.run(
                        ["allure", "generate", allure_results_dir, "-o", allure_report_dir, "--clean"],
                        check=True,
                        capture_output=True,
                        timeout=60
                    )
                    logger.info(f" Allure报告已生成: {allure_report_dir}")
                except subprocess.TimeoutExpired:
                    logger.warning("生成Allure报告超时，继续使用serve模式")
                except Exception as e:
                    logger.warning(f"生成Allure报告失败: {str(e)}，继续使用serve模式")
            
            logger.info(f"启动Allure报告服务器: {allure_results_dir}")
            
            # 使用allure serve启动报告（会自动打开浏览器）
            if background:
                # 后台运行（非阻塞）
                subprocess.Popen(
                    ["allure", "serve", allure_results_dir],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                logger.info("Allure报告服务器已在后台启动，浏览器应该会自动打开")
            else:
                # 前台运行（阻塞，直到服务器关闭）
                subprocess.run(
                    ["allure", "serve", allure_results_dir],
                    check=True
                )
            
        except subprocess.CalledProcessError as e:
            logger.error(f"启动Allure报告失败: {str(e)}")
            logger.info("请确认已安装Allure: https://docs.qameta.io/allure/")
        except FileNotFoundError:
            logger.error("allure命令未找到，请确认已安装Allure")
            logger.info("安装方法: https://docs.qameta.io/allure/")
    
    @staticmethod
    def open_allure_report_static(allure_report_dir: str = "reports/allure-report"):
        """
        使用Python HTTP服务器打开静态Allure报告（如果allure serve不可用时的备选方案）
        
        参数：
        - allure_report_dir: Allure报告目录（包含index.html）
        """
        if not os.path.exists(allure_report_dir):
            logger.error(f"Allure报告目录不存在: {allure_report_dir}")
            return
        
        index_html = os.path.join(allure_report_dir, "index.html")
        if not os.path.exists(index_html):
            logger.error(f"报告index.html不存在: {index_html}")
            return
        
        try:
            import http.server
            import socketserver
            import webbrowser
            import threading
            import time
            
            # 切换到报告目录
            os.chdir(allure_report_dir)
            
            # 启动HTTP服务器（使用随机可用端口）
            port = 8888
            handler = http.server.SimpleHTTPRequestHandler
            
            # 尝试找到可用端口
            for _ in range(10):
                try:
                    httpd = socketserver.TCPServer(("", port), handler)
                    break
                except OSError:
                    port += 1
            else:
                logger.error("无法找到可用端口启动HTTP服务器")
                return
            
            server_url = f"http://localhost:{port}"
            
            logger.info(f"启动HTTP服务器: {server_url}")
            logger.info(f"报告地址: {server_url}/index.html")
            
            # 在后台线程中启动服务器
            def run_server():
                httpd.serve_forever()
            
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            # 等待服务器启动
            time.sleep(1)
            
            # 打开浏览器
            webbrowser.open(f"{server_url}/index.html")
            
            logger.info(f"报告已打开，服务器运行在: {server_url}")
            logger.info("按 Ctrl+C 停止服务器")
            
            # 保持服务器运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("停止HTTP服务器...")
                httpd.shutdown()
                os.chdir(os.path.dirname(os.path.dirname(allure_report_dir)))
                
        except Exception as e:
            logger.error(f"启动HTTP服务器失败: {str(e)}")
            logger.info("建议使用: allure serve reports/allure-results")
    
    @staticmethod
    def generate_allure_report(
        allure_results_dir: str = "reports/allure-results",
        allure_report_dir: str = "reports/allure-report"
    ):
        """
        生成Allure报告（不自动打开）
        
        参数：
        - allure_results_dir: Allure结果目录
        - allure_report_dir: Allure报告输出目录
        """
        if not os.path.exists(allure_results_dir):
            logger.error(f"Allure结果目录不存在: {allure_results_dir}")
            return
        
        try:
            logger.info(f"生成Allure报告: {allure_results_dir} -> {allure_report_dir}")
            
            # 创建报告目录
            os.makedirs(allure_report_dir, exist_ok=True)
            
            # 生成报告
            subprocess.run(
                ["allure", "generate", allure_results_dir, "-o", allure_report_dir, "--clean"],
                check=True
            )
            
            report_index = os.path.join(allure_report_dir, "index.html")
            logger.info(f"Allure报告生成成功: {report_index}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"生成Allure报告失败: {str(e)}")
        except FileNotFoundError:
            logger.error("allure命令未找到，请确认已安装Allure")

