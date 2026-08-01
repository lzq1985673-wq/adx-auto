#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ADX-Auto 跨平台一键安装脚本

支持 Windows / macOS / Linux，无需手动操作。
自动完成：
  1. 检测 Python 环境
  2. 创建虚拟环境
  3. 安装所有依赖
  4. 初始化数据库 + 默认管理员

用法：
    python install.py
"""

import os
import sys
import subprocess
import platform

# 项目根目录（本脚本所在目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 虚拟环境目录名
VENV_DIR = os.path.join(BASE_DIR, "venv")

# 虚拟环境中的 Python / pip 可执行文件路径
IS_WINDOWS = platform.system() == "Windows"
if IS_WINDOWS:
    VENV_PYTHON = os.path.join(VENV_DIR, "Scripts", "python.exe")
    VENV_PIP = os.path.join(VENV_DIR, "Scripts", "pip.exe")
else:
    VENV_PYTHON = os.path.join(VENV_DIR, "bin", "python")
    VENV_PIP = os.path.join(VENV_DIR, "bin", "pip")


def print_banner():
    print("=" * 56)
    print("  ADX-Auto Google Ads 自动化管理系统 - 跨平台安装")
    print("  系统: {} {}".format(platform.system(), platform.machine()))
    print("=" * 56)
    print()


def check_python():
    """检查 Python 版本 >= 3.8"""
    print("[1/5] 检查 Python 环境 ...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("      x 需要 Python 3.8+，当前版本: {}.{}.{}".format(
            version.major, version.minor, version.micro))
        print("      请访问 https://www.python.org/downloads/ 下载安装")
        sys.exit(1)
    print("      v Python {}.{}.{}".format(
        version.major, version.minor, version.micro))
    print()


def create_venv():
    """创建虚拟环境"""
    print("[2/5] 创建虚拟环境 ...")
    if os.path.exists(VENV_PYTHON):
        print("      v 虚拟环境已存在，跳过创建")
        return
    subprocess.check_call(
        [sys.executable, "-m", "venv", VENV_DIR],
        cwd=BASE_DIR,
    )
    print("      v 虚拟环境已创建: {}".format(VENV_DIR))
    print()


def upgrade_pip():
    """升级 pip"""
    print("[3/5] 升级 pip ...")
    subprocess.check_call(
        [VENV_PYTHON, "-m", "pip", "install", "--upgrade", "pip", "-q"],
        cwd=BASE_DIR,
    )
    print("      v pip 已升级")
    print()


def install_dependencies():
    """安装项目依赖"""
    print("[4/5] 安装依赖库（可能需要几分钟）...")
    req_file = os.path.join(BASE_DIR, "requirements.txt")
    subprocess.check_call(
        [VENV_PIP, "install", "-r", req_file, "-q"],
        cwd=BASE_DIR,
    )
    print("      v 依赖安装完成")
    print()


def init_database():
    """初始化数据库"""
    print("[5/5] 初始化数据库 ...")
    env = os.environ.copy()
    env["PYTHONPATH"] = BASE_DIR
    subprocess.check_call(
        [VENV_PYTHON, "-c",
         "import sys; sys.path.insert(0, '.'); "
         "from app import create_app; create_app(); "
         "print('      v 数据库初始化完成'); "
         "print('      v 默认管理员: admin / admin123')"],
        cwd=BASE_DIR,
        env=env,
    )
    print()


def main():
    print_banner()
    check_python()
    create_venv()
    upgrade_pip()
    install_dependencies()
    init_database()

    print("=" * 56)
    print("  安装完成！")
    print("=" * 56)
    print()
    print("  启动方式：")
    if IS_WINDOWS:
        print("    双击 run.bat  或  python start.py")
    else:
        print("    ./start.sh  或  python3 start.py")
    print()
    print("  访问地址：http://127.0.0.1:5000")
    print("  默认账号：admin / admin123")
    print()


if __name__ == "__main__":
    main()
