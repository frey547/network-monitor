FROM python:3.12-slim

WORKDIR /app

# 先复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制整个 app 文件夹
COPY app/ ./app/       

# 暴露端口
EXPOSE 8000

# 启动命令，注意模块路径
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
