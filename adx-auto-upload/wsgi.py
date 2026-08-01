"""
ADX-Auto WSGI 入口文件

用于 Gunicorn 等生产环境 WSGI 服务器启动。
Render 等云平台通过此文件加载应用。

用法：
    gunicorn wsgi:app
"""
import os
from app import create_app

# 强制使用生产环境配置
app = create_app("production")

if __name__ == "__main__":
    app.run()
