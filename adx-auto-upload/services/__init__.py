"""
ADX Auto 服务层模块

本包提供与外部平台（Google Ads 等）交互的服务类，
封装了 API 调用、数据同步、批量操作等业务逻辑。
"""

from .google_ads_service import GoogleAdsService

__all__ = ["GoogleAdsService"]
