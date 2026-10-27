FROM python:3.11-slim

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY:-}

# 默认运行演示模式
CMD ["python", "main.py", "--mode", "demo"]
