# ADX-Auto Dockerfile — 跨平台容器化部署
# 构建: docker build -t adx-auto .
# 运行: docker run -d -p 5000:5000 --name adx-auto adx-auto

FROM python:3.11-slim

# 设置时区和工作目录
ENV TZ=Asia/Shanghai
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖清单，利用 Docker 缓存层
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# 复制项目代码
COPY . .

# 初始化数据库
RUN python -c "from app import create_app; create_app(); print('DB initialized')"

# 暴露端口
EXPOSE 5000

# 使用 gunicorn 生产级启动
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--access-logfile", "-", "app:create_app('production')"]
