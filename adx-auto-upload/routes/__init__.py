# -*- coding: utf-8 -*-
"""
路由包初始化模块

导出页面路由蓝图和 API 路由蓝图，供 app.py 注册使用。
"""

from routes.main import main_bp
from routes.api import api_bp

__all__ = ["main_bp", "api_bp"]