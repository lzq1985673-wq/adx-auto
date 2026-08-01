#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ADX-Auto 跨平台启动脚本

支持 Windows / macOS / Linux。
自动检测虚拟环境并启动 Flask 应用。

用法：
    python start.py              # 默认开发模式
    python start.py --prod       # 生产模式 (gunicorn/waitress)
    python start.py --port 8080  # 自定义端口
    python start.py --host 0.0.0.0 --port 5000
"""

import os
import sys
import platform
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    VENV_PYTHON = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
else:
    VENV_PYTHON = os.path.join(BASE_DIR, "venv", "bin", "python")


def check_venv():
    """检查虚拟环境是否已创建"""
    if not os.path.exists(VENV_PYTHON):
        print("x 未检测到虚拟环境，请先运行安装：")
        if IS_WINDOWS:
            print("    python install.py  或  双击 install.bat")
        else:
            print("    python3 install.py  或  ./install.sh")
        sys.exit(1)


def parse_args():
    """解析命令行参数"""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    prod = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--prod":
            prod = True
        elif args[i] == "--host" and i + 1 < len(args):
            host = args[i + 1]
            i += 1
        elif args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 1
        i += 1

    return host, port, prod


def run_dev(host, port):
    """开发模式启动"""
    print("=" * 56)
    print("  ADX-Auto Google Ads 自动化管理系统")
    print("  模式: 开发模式 (debug)")
    print("  地址: http://{}:{}".format(host, port))
    print("  账号: admin / admin123")
    print("=" * 56)
    print()

    env = os.environ.copy()
    env["PYTHONPATH"] = BASE_DIR
    env["FLASK_DEBUG"] = "1"

    cmd = [
        VENV_PYTHON, "-c",
        "import sys; sys.path.insert(0, '.'); "
        "from app import create_app; "
        "app = create_app(); "
        "app.run(debug=True, host='{}', port={})".format(host, port),
    ]
    subprocess.call(cmd, cwd=BASE_DIR, env=env)


def run_prod(host, port):
    """生产模式启动 — 使用 gunicorn (Linux/Mac) 或 waitress (Windows)"""
    print("=" * 56)
    print("  ADX-Auto Google Ads 自动化管理系统")
    print("  模式: 生产模式")
    print("  地址: http://{}:{}".format(host, port))
    print("  账号: admin / admin123")
    print("=" * 56)
    print()

    env = os.environ.copy()
    env["PYTHONPATH"] = BASE_DIR
    env["FLASK_ENV"] = "production"

    if IS_WINDOWS:
        # Windows 使用 waitress
        try:
            subprocess.check_call(
                [VENV_PYTHON, "-m", "pip", "install", "waitress", "-q"],
                cwd=BASE_DIR,
            )
        except subprocess.CalledProcessError:
            pass
        cmd = [
            VENV_PYTHON, "-c",
            "import sys; sys.path.insert(0, '.'); "
            "from app import create_app; "
            "from waitress import serve; "
            "app = create_app('production'); "
            "serve(app, host='{}', port={})".format(host, port),
        ]
    else:
        # Linux/Mac 使用 gunicorn
        try:
            subprocess.check_call(
                [VENV_PYTHON, "-m", "pip", "install", "gunicorn", "-q"],
                cwd=BASE_DIR,
            )
        except subprocess.CalledProcessError:
            pass
        cmd = [
            VENV_PYTHON, "-m", "gunicorn",
            "--bind", "{}:{}".format(host, port),
            "--workers", "4",
            "--chdir", BASE_DIR,
            "app:create_app('production')",
        ]

    subprocess.call(cmd, cwd=BASE_DIR, env=env)


def main():
    check_venv()
    host, port, prod = parse_args()
    if prod:
        run_prod(host, port)
    else:
        run_dev(host, port)


if __name__ == "__main__":
    main()
