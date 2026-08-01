"""
Flask 应用配置模块

本模块定义了 ADX Auto 平台的所有配置项，包括：
- 数据库连接
- 密钥管理
- Google Ads API 凭证
- AI 服务配置
- 代理（Proxy）配置

所有配置均通过环境变量读取，并提供合理的默认值。
"""

import os
import secrets


class Config:
    """基础配置类，包含所有通用配置项"""

    # ============================================================
    # Flask 基础配置
    # ============================================================

    # 密钥，用于会话加密和 CSRF 保护，未设置时自动生成随机密钥
    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))

    # 是否开启调试模式，默认关闭（生产环境必须关闭）
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    # ============================================================
    # 数据库配置
    # ============================================================

    # SQLAlchemy 数据库连接 URI，默认使用 SQLite 本地文件
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI", "sqlite:///adx_auto.db"
    )

    # 是否跟踪对象的修改，默认关闭以节省内存
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ============================================================
    # Google Ads API 配置
    # ============================================================

    # Google Ads 开发者令牌
    GOOGLE_ADS_DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")

    # Google Ads OAuth2 客户端 ID
    GOOGLE_ADS_CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID", "")

    # Google Ads OAuth2 客户端密钥
    GOOGLE_ADS_CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")

    # Google Ads OAuth2 刷新令牌（用于获取访问令牌）
    GOOGLE_ADS_REFRESH_TOKEN = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")

    # Google Ads API 版本号，默认使用 v18
    GOOGLE_ADS_API_VERSION = os.getenv("GOOGLE_ADS_API_VERSION", "v18")

    # Google Ads 登录客户 ID（MCC 层级操作时使用）
    GOOGLE_ADS_LOGIN_CUSTOMER_ID = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")

    # ============================================================
    # AI 服务配置（OpenAI）
    # ============================================================

    # OpenAI API 密钥
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

    # AI 默认使用的模型，默认 gpt-4o-mini（轻量、高性价比）
    AI_DEFAULT_MODEL = os.getenv("AI_DEFAULT_MODEL", "gpt-4o-mini")

    # AI 请求超时时间（秒），默认 60 秒
    AI_REQUEST_TIMEOUT = int(os.getenv("AI_REQUEST_TIMEOUT", "60"))

    # AI 最大生成令牌数，默认 2048
    AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "2048"))

    # ============================================================
    # 代理（Proxy）配置
    # ============================================================

    # 代理提供商列表，JSON 字符串格式，默认为空列表
    # 示例：[{"name":"brightdata","provider_type":"brightdata","api_endpoint":"...","api_key":"..."}]
    PROXY_PROVIDERS = os.getenv("PROXY_PROVIDERS", "[]")

    # 全局代理地址（可选，如需统一走代理可配置）
    GLOBAL_PROXY_URL = os.getenv("GLOBAL_PROXY_URL", "")

    # ============================================================
    # 应用运行配置
    # ============================================================

    # 应用监听的主机地址，默认所有接口
    HOST = os.getenv("HOST", "0.0.0.0")

    # 应用监听的端口，默认 5000
    PORT = int(os.getenv("PORT", "5000"))

    # 日志级别，默认 INFO
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class DevelopmentConfig(Config):
    """开发环境配置"""

    DEBUG = True
    LOG_LEVEL = "DEBUG"


class TestingConfig(Config):
    """测试环境配置，使用内存数据库"""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key-for-testing-only"


class ProductionConfig(Config):
    """生产环境配置"""

    DEBUG = False
    LOG_LEVEL = "WARNING"


# ============================================================
# 配置映射表：根据环境变量 FLASK_ENV 自动选择配置类
# ============================================================
config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": Config,
}


def get_config():
    """
    根据环境变量获取配置实例

    优先读取 FLASK_ENV 环境变量，未设置时默认使用 production 配置。

    Returns:
        Config: 对应环境的配置类实例
    """
    env = os.getenv("FLASK_ENV", "production")
    return config_map.get(env, Config)
