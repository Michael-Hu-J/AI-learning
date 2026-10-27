#!/usr/bin/env python3
"""
Agent评测 Dashboard 服务器 — 轻量级，零依赖（仅需 Flask）

功能：
  - 列出所有历史评测结果
  - 查看单次评测详情
  - 触发新评测（后台运行，WebSocket 推送进度）
  - serve 前端 Dashboard 页面

启动：
    python dashboard_server.py --port 8080
    # 自动扫描 reports/ 目录下的 full_eval_*.json 文件
"""
import os
import sys
import json
import glob
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import argparse

# 尝试导入 flask，如果不可用则回退到纯静态 serve
try:
    from flask import Flask, jsonify, request, send_from_directory
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


# ============================================================
#  工具函数
# ============================================================

def get_project_root():
    """获取项目根目录"""
    return Path(__file__).parent


def get_reports_dir():
    """获取 reports 目录"""
    reports = get_project_root() / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    return reports


def scan_results():
    """扫描所有评测结果文件，返回按时间排序的列表"""
    reports_dir = get_reports_dir()
    pattern = str(reports_dir / "full_eval_*.json")
    files = sorted(glob.glob(pattern), reverse=True)

    results = []
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            ts = data.get('timestamp', '')
            # 从文件名提取时间戳用于排序
            fname = Path(f).stem.replace('full_eval_', '')
            results.append({
                "id": fname,
                "file": str(f),
                "timestamp": ts,
                "agent": data.get('agent', 'unknown'),
                "overall_score": data.get('overall', {}).get('overall_score', 0),
                "grade": data.get('overall', {}).get('grade', 'N/A'),
                "dimensions": {
                    k: v.get('overall', 0)
                    for k, v in data.get('dimension_scores', {}).items()
                }
            })
        except Exception:
            continue
    return results


def load_result(result_id):
    """加载单个评测结果"""
    reports_dir = get_reports_dir()
    f = reports_dir / f"full_eval_{result_id}.json"
    if not f.exists():
        return None
    with open(f, 'r', encoding='utf-8') as fh:
        return json.load(fh)


# ============================================================
#  Flask 版本
# ============================================================

if HAS_FLASK:
    app = Flask(__name__, static_folder='dashboard', static_url_path='/dashboard')

    @app.route('/')
    def index():
        """重定向到 Dashboard"""
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/api/results')
    def api_results():
        """列出所有评测结果"""
        results = scan_results()
        return jsonify({"count": len(results), "results": results})

    @app.route('/api/health')
    def api_health():
        """健康检查"""
        return jsonify({"status": "ok", "results_count": len(scan_results())})

    @app.route('/api/results/<result_id>')
    def api_result_detail(result_id):
        """获取单个评测结果详情"""
        data = load_result(result_id)
        if data is None:
            return jsonify({"error": "Result not found"}), 404
        return jsonify(data)

    @app.route('/api/run', methods=['POST'])
    def api_run():
        """触发新评测"""
        # 检查是否已有评测在运行
        if hasattr(api_run, '_running') and api_run._running:
            return jsonify({"status": "already_running"}), 409

        provider = request.json.get('provider', 'tongyi') if request.json else 'tongyi'
        model = request.json.get('model', 'qwen-plus') if request.json else 'qwen-plus'

        api_run._running = True
        api_run._progress = {"status": "starting", "step": 0, "total": 5}

        def run_eval():
            try:
                script = get_project_root() / "scripts" / "run_full_eval.py"
                proc = subprocess.Popen(
                    [sys.executable, str(script), f"--provider={provider}", f"--model={model}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(get_project_root()),
                    env={**os.environ}
                )

                steps = ["task_planning", "tool_use", "dialogue", "coding", "knowledge"]
                api_run._progress = {"status": "running", "step": 0, "total": 5, "current": "initializing"}

                for line in proc.stdout:
                    line = line.strip()
                    # 解析进度
                    for i, step in enumerate(steps):
                        if step.replace('_', ' ') in line.lower() or step in line.lower():
                            if "评测维度" in line or "benchmark" in line.lower():
                                api_run._progress = {
                                    "status": "running",
                                    "step": i + 1,
                                    "total": 5,
                                    "current": step
                                }

                proc.wait()
                api_run._progress = {"status": "completed", "step": 5, "total": 5}
            except Exception as e:
                api_run._progress = {"status": "error", "error": str(e)}
            finally:
                api_run._running = False

        threading.Thread(target=run_eval, daemon=True).start()
        return jsonify({"status": "started", "progress": api_run._progress})

    @app.route('/api/progress')
    def api_progress():
        """获取评测进度"""
        if hasattr(api_run, '_progress'):
            return jsonify(api_run._progress)
        return jsonify({"status": "idle"})

    def start_flask(port):
        print(f"\n Dashboard 已启动: http://localhost:{port}")
        print(f"📁 结果目录: {get_reports_dir()}")
        print(f" 历史结果: {len(scan_results())} 条\n")
        app.run(host='0.0.0.0', port=port, debug=False)


# ============================================================
#  回退版本：纯静态 HTTP 服务器（无 Flask 时）
# ============================================================

def start_simple(port):
    """无 Flask 时的回退方案：仅 serve 静态文件"""
    dashboard_dir = str(get_project_root() / "dashboard")
    os.chdir(dashboard_dir)

    # 注入一个简化的 API handler
    class APIHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/api/results' or self.path == '/api/health':
                self._send_json(scan_results() if self.path == '/api/results' else {"status": "ok"})
            elif self.path.startswith('/api/results/'):
                result_id = self.path.split('/')[-1]
                data = load_result(result_id)
                self._send_json(data if data else {"error": "not found"})
            else:
                super().do_GET()

        def _send_json(self, data):
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass  # 静默日志

    print(f"\n Dashboard 已启动 (静态模式): http://localhost:{port}")
    print(f"   注意: Flask 未安装，API 功能受限")
    print(f"   安装 Flask: pip install flask\n")
    HTTPServer(('0.0.0.0', port), APIHandler).serve_forever()


# ============================================================
#  入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Agent评测 Dashboard")
    parser.add_argument('--port', type=int, default=8080, help='服务端口 (默认: 8080)')
    args = parser.parse_args()

    if HAS_FLASK:
        start_flask(args.port)
    else:
        start_simple(args.port)


if __name__ == '__main__':
    main()
