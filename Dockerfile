# ============================================
# ADX-Auto Dockerfile for Render Deployment
# ============================================
FROM node:20-slim AS frontend-builder

WORKDIR /build/frontend
COPY app-source.tar.gz /build/
RUN cd /build && tar xzf app-source.tar.gz

WORKDIR /build/frontend
RUN npm install --no-audit --no-fund --loglevel=error
RUN npm run build

# ============================================
FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制源码包并解压
COPY app-source.tar.gz /tmp/
RUN cd /tmp && tar xzf app-source.tar.gz && \
    cp -r /tmp/backend/* /app/ && \
    rm -rf /tmp/app-source.tar.gz

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制前端构建产物到Flask静态目录（与__init__.py中的static_folder='../frontend/dist'匹配）
RUN mkdir -p frontend/dist
COPY --from=frontend-builder /build/frontend/dist/. frontend/dist/

# 环境变量
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# 暴露端口（Render使用PORT环境变量）
EXPOSE 5000

# 启动命令 - 使用PORT环境变量，单worker避免scheduler冲突
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 --timeout 120 --access-logfile - --error-logfile - run:app"]
