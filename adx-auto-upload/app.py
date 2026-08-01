# -*- coding: utf-8 -*-
"""
Flask 应用工厂模块

本模块是 ADX Auto 平台的入口文件，负责：
- 创建 Flask 应用实例
- 加载配置
- 初始化扩展（数据库等）
- 注册蓝图（页面路由、API 路由）
- 创建数据库表
- 初始化默认管理员账号

使用方式：
    python app.py
    或在 WSGI 服务器中导入 create_app 工厂函数。
"""

import logging

from flask import Flask
from werkzeug.security import generate_password_hash

from config import config_map
from models import db, User, Tenant

logger = logging.getLogger(__name__)


def get_config(config_name="development"):
    """
    根据配置名称获取对应的配置类

    Args:
        config_name: 配置名称，支持 development / testing / production / default

    Returns:
        对应的配置类
    """
    return config_map.get(config_name, config_map["default"])


def _create_default_admin(app):
    """
    创建默认管理员账号（如果不存在）

    默认管理员信息：
    - 租户名称: 默认租户
    - 用户名: admin
    - 密码: admin123
    - 角色: admin

    仅在 users 表为空时创建，避免重复创建。
    """
    # 检查是否已有用户
    if User.query.first() is not None:
        logger.info("已存在用户记录，跳过默认管理员创建")
        return

    # 创建默认租户（User 模型的 tenant_id 为非空外键）
    default_tenant = Tenant(
        name="默认租户",
        slug="default",
        plan="free",
        is_active=True,
    )
    db.session.add(default_tenant)
    db.session.flush()  # 获取 tenant.id 供后续使用

    # 创建默认管理员
    admin_user = User(
        tenant_id=default_tenant.id,
        username="admin",
        email="admin@adx-auto.local",
        password_hash=generate_password_hash("admin123"),
        role="admin",
        is_active=True,
    )
    db.session.add(admin_user)
    db.session.commit()

    logger.info("已创建默认管理员: admin / admin123")


def create_app(config_name="development"):
    """
    Flask 应用工厂函数

    根据配置名称创建并配置 Flask 应用实例，完成所有初始化工作。

    Args:
        config_name: 配置环境名称，默认为 development

    Returns:
        Flask: 配置完成的应用实例
    """
    app = Flask(__name__)

    # 加载配置
    app.config.from_object(get_config(config_name))

    # 初始化数据库扩展
    db.init_app(app)

    # 注册蓝图
    from routes import main_bp, api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    # 创建数据库表并初始化默认数据
    with app.app_context():
        db.create_all()
        # 创建默认管理员（如果不存在）
        _create_default_admin(app)

    return app


if __name__ == "__main__":
    import os
    app = create_app(os.getenv("FLASK_ENV", "development"))
    host = os.getenv("HOST", app.config.get("HOST", "0.0.0.0"))
    port = int(os.getenv("PORT", app.config.get("PORT", 5000)))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug, host=host, port=port)