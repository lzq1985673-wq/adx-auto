"""
Google Ads 自动化管理服务模块

本模块提供合法合规的 Google Ads API 交互能力，封装了账户管理、广告系列管理、
广告组/广告/关键词管理等核心功能。

功能特性：
- 支持 Google Ads API 真实调用模式
- 支持无依赖环境下的 Mock 模拟模式（优雅降级）
- 完整的中文文档注释
- 统一的返回数据结构

使用方式：
    from services.google_ads_service import GoogleAdsService

    tenant_config = {
        "developer_token": "xxx",
        "client_id": "xxx.apps.googleusercontent.com",
        "client_secret": "xxx",
        "refresh_token": "xxx",
        "login_customer_id": "123-456-7890",
    }
    service = GoogleAdsService(tenant_config)
    accounts = service.list_accessible_accounts()
"""

import sys
import time
import uuid
import logging
from typing import Dict, List, Optional, Any

# 确保可以导入上级目录的 config 模块
sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

try:
    from google.ads.google_ads.client import GoogleAdsClient  # type: ignore
    from google.ads.google_ads.errors import GoogleAdsException  # type: ignore
    _GOOGLE_ADS_AVAILABLE = True
except ImportError:
    _GOOGLE_ADS_AVAILABLE = False

logger = logging.getLogger(__name__)


class GoogleAdsService:
    """
    Google Ads 自动化管理服务类

    封装 Google Ads API 的常用操作，包括账户查询、广告系列 CRUD、
    广告组和广告管理、关键词管理等。当 google-ads-python 库不可用时，
    自动进入 Mock 模式，返回逼真的模拟数据，方便开发和测试。

    Attributes:
        mock_mode (bool): 是否处于模拟模式
        tenant_config (dict): 租户配置信息
    """

    def __init__(self, tenant_config: Dict[str, str]):
        """
        初始化 Google Ads 服务实例

        接收租户级别的 Google Ads API 凭证配置，尝试构建 GoogleAdsClient。
        如果 google-ads-python 库不可用，则自动降级到 Mock 模式。

        Args:
            tenant_config: 租户配置字典，包含以下字段：
                - developer_token (str): Google Ads 开发者令牌
                - client_id (str): OAuth2 客户端 ID
                - client_secret (str): OAuth2 客户端密钥
                - refresh_token (str): OAuth2 刷新令牌
                - login_customer_id (str): 登录客户 ID（MCC 账号 ID）

        Example:
            >>> config = {
            ...     "developer_token": "ABcdEF",
            ...     "client_id": "123.apps.googleusercontent.com",
            ...     "client_secret": "secret",
            ...     "refresh_token": "refresh",
            ...     "login_customer_id": "123-456-7890",
            ... }
            >>> service = GoogleAdsService(config)
        """
        self.tenant_config = tenant_config
        self.mock_mode = False
        self._client = None

        if not _GOOGLE_ADS_AVAILABLE:
            self.mock_mode = True
            logger.warning(
                "google-ads-python 库不可用，GoogleAdsService 已进入 Mock 模式。"
                "Mock 模式下所有方法将返回模拟数据，不会调用真实 API。"
                "如需使用真实 API，请安装 google-ads-python 库：pip install google-ads"
            )
            return

        try:
            # 构建 Google Ads API 客户端配置
            credentials = {
                "developer_token": tenant_config.get("developer_token", ""),
                "client_id": tenant_config.get("client_id", ""),
                "client_secret": tenant_config.get("client_secret", ""),
                "refresh_token": tenant_config.get("refresh_token", ""),
                "login_customer_id": tenant_config.get("login_customer_id", ""),
                "use_proto_plus": True,
            }

            self._client = GoogleAdsClient.load_from_dict(credentials)
            logger.info(
                "Google Ads 客户端初始化成功，login_customer_id=%s",
                tenant_config.get("login_customer_id", ""),
            )
        except Exception as e:
            self.mock_mode = True
            logger.warning(
                "Google Ads 客户端初始化失败，已降级到 Mock 模式。错误信息：%s", str(e)
            )

    def get_client(self):
        """
        获取 GoogleAdsClient 实例

        返回已初始化的 Google Ads API 客户端实例。
        在 Mock 模式下返回 None。

        Returns:
            GoogleAdsClient | None: 客户端实例，Mock 模式下为 None

        Example:
            >>> client = service.get_client()
            >>> if client:
            ...     ga_service = client.get_service("GoogleAdsService")
        """
        return self._client

    def list_accessible_accounts(self) -> List[Dict[str, Any]]:
        """
        列出 MCC 账号下所有可访问的子账号

        在真实模式下，调用 CustomerService.ListAccessibleAccounts 获取
        当前认证账号（MCC）下所有可管理的子账户列表。

        在 Mock 模式下，返回预设的模拟账户数据。

        Returns:
            List[Dict[str, Any]]: 可访问账户列表，每个账户包含：
                - id (str): 账户 ID
                - name (str): 账户名称
                - currency_code (str): 币种代码
                - time_zone (str): 时区
                - status (str): 账户状态

        Example:
            >>> accounts = service.list_accessible_accounts()
            >>> for acc in accounts:
            ...     print(acc["id"], acc["name"])
        """
        if self.mock_mode:
            time.sleep(0.1)
            return [
                {
                    "id": "123-456-7890",
                    "name": "测试账户1 - 品牌推广",
                    "currency_code": "CNY",
                    "time_zone": "Asia/Shanghai",
                    "status": "ENABLED",
                    "manager": False,
                },
                {
                    "id": "234-567-8901",
                    "name": "测试账户2 - 效果推广",
                    "currency_code": "USD",
                    "time_zone": "America/Los_Angeles",
                    "status": "ENABLED",
                    "manager": False,
                },
                {
                    "id": "345-678-9012",
                    "name": "测试账户3 - 品牌防御",
                    "currency_code": "EUR",
                    "time_zone": "Europe/London",
                    "status": "PAUSED",
                    "manager": False,
                },
            ]

        try:
            client = self.get_client()
            customer_service = client.get_service("CustomerService")
            accessible_accounts = customer_service.list_accessible_accounts()

            accounts = []
            for account in accessible_accounts:
                accounts.append({
                    "id": account.resource_name.replace("customers/", "").replace("-", ""),
                    "name": account.descriptive_name,
                    "currency_code": account.currency_code,
                    "time_zone": account.time_zone,
                    "status": "ENABLED",
                    "manager": account.manager,
                })

            logger.info("获取到 %d 个可访问账户", len(accounts))
            return accounts

        except GoogleAdsException as e:
            logger.error("获取可访问账户失败: %s", str(e))
            raise
        except Exception as e:
            logger.error("获取可访问账户时发生意外错误: %s", str(e))
            raise

    def sync_account(self, account_id: str) -> Dict[str, Any]:
        """
        同步单个账号的基础信息

        从 Google Ads API 获取指定账户的详细基础信息，包括账户名称、
        币种、时区、状态、创建时间等，用于本地数据同步。

        在 Mock 模式下，返回模拟的账户详细信息。

        Args:
            account_id: 要同步的 Google Ads 账户 ID（如 "123-456-7890"）

        Returns:
            Dict[str, Any]: 账户详情字典，包含：
                - id (str): 账户 ID
                - name (str): 账户名称
                - currency_code (str): 币种代码（如 "CNY"）
                - time_zone (str): 时区（如 "Asia/Shanghai"）
                - status (str): 账户状态（ENABLED / PAUSED / CLOSED）
                - tracking_url_template (str): 追踪 URL 模板
                - auto_tagging_enabled (bool): 是否启用自动标记

        Example:
            >>> info = service.sync_account("123-456-7890")
            >>> print(info["name"], info["currency_code"])
        """
        if self.mock_mode:
            time.sleep(0.1)
            return {
                "id": account_id,
                "name": f"同步测试账户 - {account_id}",
                "currency_code": "CNY",
                "time_zone": "Asia/Shanghai",
                "status": "ENABLED",
                "tracking_url_template": "{lpurl}?utm_source=google&utm_medium=cpc",
                "auto_tagging_enabled": True,
            }

        try:
            client = self.get_client()
            ga_service = client.get_service("GoogleAdsService")
            customer_service = client.get_service("CustomerService")

            # 使用 Search 方法查询客户详细信息
            query = f"""
                SELECT
                    customer.id,
                    customer.descriptive_name,
                    customer.currency_code,
                    customer.time_zone,
                    customer.status,
                    customer.tracking_url_template,
                    customer.auto_tagging_enabled
                FROM customer
                WHERE customer.id = '{account_id.replace("-", "")}'
            """
            response = ga_service.search(
                customer_id=account_id, query=query
            )

            account_info = None
            for row in response:
                customer = row.customer
                account_info = {
                    "id": account_id,
                    "name": customer.descriptive_name,
                    "currency_code": customer.currency_code,
                    "time_zone": customer.time_zone,
                    "status": str(customer.status).split(".")[-1],
                    "tracking_url_template": customer.tracking_url_template,
                    "auto_tagging_enabled": customer.auto_tagging_enabled,
                }

            if account_info is None:
                logger.warning("未找到账户 %s 的信息", account_id)
                return {}

            logger.info("成功同步账户 %s 的基础信息", account_id)
            return account_info

        except GoogleAdsException as e:
            logger.error("同步账户 %s 失败: %s", account_id, str(e))
            raise
        except Exception as e:
            logger.error("同步账户 %s 时发生意外错误: %s", account_id, str(e))
            raise

    def list_campaigns(
        self, account_id: str, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出指定账户下的广告系列

        查询指定 Google Ads 账户下的所有广告系列信息，支持按状态过滤。
        返回每个广告系列的基础信息，包括名称、状态、预算、投放策略等。

        在 Mock 模式下，返回 3-5 条模拟广告系列数据。

        Args:
            account_id: Google Ads 账户 ID
            status: 可选的状态过滤条件，可选值：
                - "ENABLED": 仅返回启用的广告系列
                - "PAUSED": 仅返回暂停的广告系列
                - "REMOVED": 仅返回已移除的广告系列
                - None: 返回所有状态的广告系列

        Returns:
            List[Dict[str, Any]]: 广告系列列表，每项包含：
                - id (str): 广告系列 ID
                - name (str): 广告系列名称
                - status (str): 广告系列状态
                - budget_amount_micros (int): 预算金额（微单位）
                - budget_amount (float): 预算金额（正常单位）
                - bidding_strategy (str): 出价策略类型
                - advertising_channel_type (str): 投放渠道类型
                - start_date (str): 开始日期（YYYY-MM-DD）
                - end_date (str): 结束日期（YYYY-MM-DD，可能为空）

        Example:
            >>> campaigns = service.list_campaigns("123-456-7890", status="ENABLED")
            >>> for c in campaigns:
            ...     print(c["name"], c["budget_amount"])
        """
        if self.mock_mode:
            time.sleep(0.1)
            mock_campaigns = [
                {
                    "id": "1111222233",
                    "name": "品牌搜索推广",
                    "status": "ENABLED",
                    "budget_amount_micros": 5000000000,
                    "budget_amount": 5000.0,
                    "bidding_strategy": "MAXIMIZE_CLICKS",
                    "advertising_channel_type": "SEARCH",
                    "start_date": "2025-01-15",
                    "end_date": "",
                },
                {
                    "id": "2222333344",
                    "name": "产品展示推广",
                    "status": "ENABLED",
                    "budget_amount_micros": 8000000000,
                    "budget_amount": 8000.0,
                    "bidding_strategy": "TARGET_ROAS",
                    "advertising_channel_type": "SHOPPING",
                    "start_date": "2025-02-01",
                    "end_date": "2025-12-31",
                },
                {
                    "id": "3333444455",
                    "name": "应用下载推广",
                    "status": "PAUSED",
                    "budget_amount_micros": 3000000000,
                    "budget_amount": 3000.0,
                    "bidding_strategy": "TARGET_CPA",
                    "advertising_channel_type": "APP",
                    "start_date": "2025-03-10",
                    "end_date": "",
                },
                {
                    "id": "4444555566",
                    "name": "视频推广活动",
                    "status": "ENABLED",
                    "budget_amount_micros": 10000000000,
                    "budget_amount": 10000.0,
                    "bidding_strategy": "MAXIMIZE_CONVERSIONS",
                    "advertising_channel_type": "VIDEO",
                    "start_date": "2025-04-01",
                    "end_date": "2025-06-30",
                },
                {
                    "id": "5555666677",
                    "name": "再营销推广",
                    "status": "PAUSED",
                    "budget_amount_micros": 2000000000,
                    "budget_amount": 2000.0,
                    "bidding_strategy": "MANUAL_CPC",
                    "advertising_channel_type": "DISPLAY",
                    "start_date": "2025-01-01",
                    "end_date": "",
                },
            ]

            if status:
                mock_campaigns = [c for c in mock_campaigns if c["status"] == status]

            return mock_campaigns

        try:
            client = self.get_client()
            ga_service = client.get_service("GoogleAdsService")

            # 构建 GAQL 查询语句
            query = """
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    campaign_budget.amount_micros,
                    campaign.bidding_strategy.type,
                    campaign.advertising_channel_type,
                    campaign.start_date,
                    campaign.end_date
                FROM campaign
            """
            if status:
                query += f" WHERE campaign.status = '{status}'"
            query += " ORDER BY campaign.name"

            response = ga_service.search(customer_id=account_id, query=query)

            campaigns = []
            for row in response:
                campaign = row.campaign
                campaigns.append({
                    "id": str(campaign.id),
                    "name": campaign.name,
                    "status": str(campaign.status).split(".")[-1],
                    "budget_amount_micros": row.campaign_budget.amount_micros,
                    "budget_amount": row.campaign_budget.amount_micros / 1_000_000,
                    "bidding_strategy": str(campaign.bidding_strategy.type).split(".")[-1],
                    "advertising_channel_type": str(campaign.advertising_channel_type).split(".")[-1],
                    "start_date": campaign.start_date,
                    "end_date": campaign.end_date or "",
                })

            logger.info(
                "账户 %s 下获取到 %d 个广告系列（status=%s）",
                account_id, len(campaigns), status or "全部",
            )
            return campaigns

        except GoogleAdsException as e:
            logger.error("获取账户 %s 广告系列失败: %s", account_id, str(e))
            raise
        except Exception as e:
            logger.error("获取广告系列时发生意外错误: %s", str(e))
            raise

    def list_ad_groups(
        self, account_id: str, campaign_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出指定账户（可限定广告系列）下的广告组

        查询广告组的基础信息，包括名称、状态、出价、类型等。
        可通过 campaign_id 参数限定查询范围到特定广告系列。

        在 Mock 模式下，返回模拟的广告组数据。

        Args:
            account_id: Google Ads 账户 ID
            campaign_id: 可选的广告系列 ID，用于限定查询范围。
                         如果不指定，则返回账户下所有广告系列的广告组。

        Returns:
            List[Dict[str, Any]]: 广告组列表，每项包含：
                - id (str): 广告组 ID
                - name (str): 广告组名称
                - campaign_id (str): 所属广告系列 ID
                - campaign_name (str): 所属广告系列名称
                - status (str): 广告组状态（ENABLED / PAUSED / REMOVED）
                - type (str): 广告组类型（SEARCH / DISPLAY 等）
                - cpc_bid_micros (int): CPC 出价（微单位）
                - cpc_bid (float): CPC 出价（正常单位）

        Example:
            >>> ad_groups = service.list_ad_groups("123-456-7890", campaign_id="1111222233")
            >>> for ag in ad_groups:
            ...     print(ag["name"], ag["cpc_bid"])
        """
        if self.mock_mode:
            time.sleep(0.1)
            mock_ad_groups = [
                {
                    "id": "6666777788",
                    "name": "通用关键词组",
                    "campaign_id": campaign_id or "1111222233",
                    "campaign_name": "品牌搜索推广",
                    "status": "ENABLED",
                    "type": "SEARCH",
                    "cpc_bid_micros": 1500000,
                    "cpc_bid": 1.5,
                },
                {
                    "id": "7777888899",
                    "name": "竞品词组",
                    "campaign_id": campaign_id or "1111222233",
                    "campaign_name": "品牌搜索推广",
                    "status": "ENABLED",
                    "type": "SEARCH",
                    "cpc_bid_micros": 2000000,
                    "cpc_bid": 2.0,
                },
                {
                    "id": "8888999900",
                    "name": "长尾关键词组",
                    "campaign_id": campaign_id or "1111222233",
                    "campaign_name": "品牌搜索推广",
                    "status": "PAUSED",
                    "type": "SEARCH",
                    "cpc_bid_micros": 800000,
                    "cpc_bid": 0.8,
                },
                {
                    "id": "9999000011",
                    "name": "再营销受众组",
                    "campaign_id": campaign_id or "2222333344",
                    "campaign_name": "产品展示推广",
                    "status": "ENABLED",
                    "type": "DISPLAY",
                    "cpc_bid_micros": 1200000,
                    "cpc_bid": 1.2,
                },
            ]

            if campaign_id:
                mock_ad_groups = [
                    ag for ag in mock_ad_groups
                    if ag["campaign_id"] == campaign_id
                ]

            return mock_ad_groups

        try:
            client = self.get_client()
            ga_service = client.get_service("GoogleAdsService")

            query = """
                SELECT
                    ad_group.id,
                    ad_group.name,
                    ad_group.campaign,
                    campaign.name,
                    ad_group.status,
                    ad_group.type,
                    ad_group.cpc_bid_micros
                FROM ad_group
            """
            if campaign_id:
                query += f" WHERE campaign.id = '{campaign_id}'"
            query += " ORDER BY ad_group.name"

            response = ga_service.search(customer_id=account_id, query=query)

            ad_groups = []
            for row in response:
                ad_group = row.ad_group
                ad_groups.append({
                    "id": str(ad_group.id),
                    "name": ad_group.name,
                    "campaign_id": ad_group.campaign.replace("customers/", "").split("/")[1],
                    "campaign_name": row.campaign.name,
                    "status": str(ad_group.status).split(".")[-1],
                    "type": str(ad_group.type).split(".")[-1],
                    "cpc_bid_micros": ad_group.cpc_bid_micros,
                    "cpc_bid": ad_group.cpc_bid_micros / 1_000_000,
                })

            logger.info(
                "账户 %s 下获取到 %d 个广告组（campaign_id=%s）",
                account_id, len(ad_groups), campaign_id or "全部",
            )
            return ad_groups

        except GoogleAdsException as e:
            logger.error("获取广告组失败: %s", str(e))
            raise
        except Exception as e:
            logger.error("获取广告组时发生意外错误: %s", str(e))
            raise

    def list_ads(
        self, account_id: str, ad_group_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出指定账户（可限定广告组）下的广告

        查询广告的详细信息，包括标题、描述、展示网址、状态等。
        可通过 ad_group_id 限定查询到特定广告组。

        在 Mock 模式下，返回模拟的广告数据。

        Args:
            account_id: Google Ads 账户 ID
            ad_group_id: 可选的广告组 ID，用于限定查询范围。
                         如果不指定，则返回账户下所有广告组的广告。

        Returns:
            List[Dict[str, Any]]: 广告列表，每项包含：
                - id (str): 广告 ID
                - ad_group_id (str): 所属广告组 ID
                - type (str): 广告类型（RESPONSIVE_SEARCH_AD / EXPANDED_TEXT_AD 等）
                - status (str): 广告状态（ENABLED / PAUSED / REMOVED）
                - headlines (List[str]): 标题列表
                - descriptions (List[str]): 描述列表
                - final_url (str): 最终落地页 URL
                - display_url (str): 展示 URL

        Example:
            >>> ads = service.list_ads("123-456-7890", ad_group_id="6666777788")
            >>> for ad in ads:
            ...     print(ad["type"], ad["headlines"])
        """
        if self.mock_mode:
            time.sleep(0.1)
            mock_ads = [
                {
                    "id": "100110021003",
                    "ad_group_id": ad_group_id or "6666777788",
                    "type": "RESPONSIVE_SEARCH_AD",
                    "status": "ENABLED",
                    "headlines": [
                        "专业品质值得信赖",
                        "限时优惠全场折扣",
                        "免费注册立即体验",
                    ],
                    "descriptions": [
                        "行业领先的解决方案，覆盖全球 100+ 国家和地区",
                        "7x24 小时技术支持，99.9% 服务可用性保障",
                    ],
                    "final_url": "https://www.example.com/landing",
                    "display_url": "www.example.com/landing",
                },
                {
                    "id": "200120022003",
                    "ad_group_id": ad_group_id or "6666777788",
                    "type": "RESPONSIVE_SEARCH_AD",
                    "status": "ENABLED",
                    "headlines": [
                        "行业排名第一品牌",
                        "用户好评率 98%",
                        "立即咨询获取方案",
                    ],
                    "descriptions": [
                        "超过 500 万用户的选择，安全可靠值得信赖",
                        "新用户注册立享 30 天免费试用，无需信用卡",
                    ],
                    "final_url": "https://www.example.com/promo",
                    "display_url": "www.example.com/promo",
                },
                {
                    "id": "300130023003",
                    "ad_group_id": ad_group_id or "6666777788",
                    "type": "EXPANDED_TEXT_AD",
                    "status": "PAUSED",
                    "headlines": [
                        "年终大促火热进行中",
                        "全场商品低至五折",
                    ],
                    "descriptions": [
                        "精选优质商品，正品保障，闪电发货，售后无忧",
                    ],
                    "final_url": "https://www.example.com/sale",
                    "display_url": "www.example.com/sale",
                },
            ]

            if ad_group_id:
                mock_ads = [
                    ad for ad in mock_ads
                    if ad["ad_group_id"] == ad_group_id
                ]

            return mock_ads

        try:
            client = self.get_client()
            ga_service = client.get_service("GoogleAdsService")

            # 查询响应式搜索广告（RSA）
            query = """
                SELECT
                    ad_group_ad.ad.id,
                    ad_group_ad.ad_group,
                    ad_group_ad.status,
                    ad_group_ad.ad.type,
                    ad_group_ad.ad.final_urls,
                    ad_group_ad.ad.display_url
                FROM ad_group_ad
            """
            if ad_group_id:
                query += f" WHERE ad_group.id = '{ad_group_id}'"
            query += " ORDER BY ad_group_ad.ad.id"

            response = ga_service.search(customer_id=account_id, query=query)

            ads = []
            for row in response:
                ad_group_ad = row.ad_group_ad
                ad = ad_group_ad.ad
                ads.append({
                    "id": str(ad.id),
                    "ad_group_id": ad_group_ad.ad_group.replace("customers/", "").split("/")[1],
                    "type": str(ad.type).split(".")[-1],
                    "status": str(ad_group_ad.status).split(".")[-1],
                    "headlines": [],  # 需要额外查询 ad_asset
                    "descriptions": [],
                    "final_url": ad.final_urls[0] if ad.final_urls else "",
                    "display_url": ad.display_url or "",
                })

            logger.info(
                "账户 %s 下获取到 %d 条广告（ad_group_id=%s）",
                account_id, len(ads), ad_group_id or "全部",
            )
            return ads

        except GoogleAdsException as e:
            logger.error("获取广告失败: %s", str(e))
            raise
        except Exception as e:
            logger.error("获取广告时发生意外错误: %s", str(e))
            raise

    def list_keywords(
        self, account_id: str, ad_group_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出指定账户（可限定广告组）下的关键词

        查询关键词的详细信息，包括关键词文本、匹配类型、出价、状态等。
        可通过 ad_group_id 限定查询到特定广告组。

        在 Mock 模式下，返回模拟的关键词数据。

        Args:
            account_id: Google Ads 账户 ID
            ad_group_id: 可选的广告组 ID，用于限定查询范围。
                         如果不指定，则返回账户下所有广告组的关键词。

        Returns:
            List[Dict[str, Any]]: 关键词列表，每项包含：
                - id (str): 关键词 ID
                - ad_group_id (str): 所属广告组 ID
                - text (str): 关键词文本
                - match_type (str): 匹配类型（EXACT / PHRASE / BROAD）
                - cpc_bid_micros (int): CPC 出价（微单位）
                - cpc_bid (float): CPC 出价（正常单位）
                - status (str): 关键词状态（ENABLED / PAUSED / REMOVED）
                - quality_score (int): 质量得分（1-10，真实模式下需额外查询）

        Example:
            >>> keywords = service.list_keywords("123-456-7890", ad_group_id="6666777788")
            >>> for kw in keywords:
            ...     print(kw["text"], kw["match_type"], kw["cpc_bid"])
        """
        if self.mock_mode:
            time.sleep(0.1)
            mock_keywords = [
                {
                    "id": "400140024003",
                    "ad_group_id": ad_group_id or "6666777788",
                    "text": "云服务解决方案",
                    "match_type": "EXACT",
                    "cpc_bid_micros": 2500000,
                    "cpc_bid": 2.5,
                    "status": "ENABLED",
                    "quality_score": 8,
                },
                {
                    "id": "400140024004",
                    "ad_group_id": ad_group_id or "6666777788",
                    "text": "企业级云平台",
                    "match_type": "PHRASE",
                    "cpc_bid_micros": 1800000,
                    "cpc_bid": 1.8,
                    "status": "ENABLED",
                    "quality_score": 7,
                },
                {
                    "id": "400140024005",
                    "ad_group_id": ad_group_id or "6666777788",
                    "text": "云计算服务商",
                    "match_type": "BROAD",
                    "cpc_bid_micros": 1000000,
                    "cpc_bid": 1.0,
                    "status": "ENABLED",
                    "quality_score": 5,
                },
                {
                    "id": "400140024006",
                    "ad_group_id": ad_group_id or "6666777788",
                    "text": "海外云服务器",
                    "match_type": "EXACT",
                    "cpc_bid_micros": 3200000,
                    "cpc_bid": 3.2,
                    "status": "PAUSED",
                    "quality_score": 9,
                },
                {
                    "id": "400140024007",
                    "ad_group_id": ad_group_id or "6666777788",
                    "text": "大数据分析平台",
                    "match_type": "PHRASE",
                    "cpc_bid_micros": 2200000,
                    "cpc_bid": 2.2,
                    "status": "ENABLED",
                    "quality_score": 6,
                },
            ]

            if ad_group_id:
                mock_keywords = [
                    kw for kw in mock_keywords
                    if kw["ad_group_id"] == ad_group_id
                ]

            return mock_keywords

        try:
            client = self.get_client()
            ga_service = client.get_service("GoogleAdsService")

            query = """
                SELECT
                    ad_group_criterion.criterion_id,
                    ad_group_criterion.ad_group,
                    ad_group_criterion.keyword.text,
                    ad_group_criterion.keyword.match_type,
                    ad_group_criterion.cpc_bid_micros,
                    ad_group_criterion.status
                FROM ad_group_criterion
                WHERE ad_group_criterion.type = 'KEYWORD'
            """
            if ad_group_id:
                query += f" AND ad_group.id = '{ad_group_id}'"
            query += " ORDER BY ad_group_criterion.keyword.text"

            response = ga_service.search(customer_id=account_id, query=query)

            keywords = []
            for row in response:
                criterion = row.ad_group_criterion
                keywords.append({
                    "id": str(criterion.criterion_id),
                    "ad_group_id": criterion.ad_group.replace("customers/", "").split("/")[1],
                    "text": criterion.keyword.text,
                    "match_type": str(criterion.keyword.match_type).split(".")[-1],
                    "cpc_bid_micros": criterion.cpc_bid_micros,
                    "cpc_bid": criterion.cpc_bid_micros / 1_000_000,
                    "status": str(criterion.status).split(".")[-1],
                    "quality_score": 0,  # 需通过 GoogleAdsService.Search 专项查询
                })

            logger.info(
                "账户 %s 下获取到 %d 个关键词（ad_group_id=%s）",
                account_id, len(keywords), ad_group_id or "全部",
            )
            return keywords

        except GoogleAdsException as e:
            logger.error("获取关键词失败: %s", str(e))
            raise
        except Exception as e:
            logger.error("获取关键词时发生意外错误: %s", str(e))
            raise

    def create_campaign(
        self, account_id: str, campaign_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        创建广告系列

        在指定 Google Ads 账户下创建新的广告系列。支持设置名称、预算、
        出价策略、投放国家等参数。

        在 Mock 模式下，模拟创建过程并返回模拟的创建结果。

        Args:
            account_id: Google Ads 账户 ID
            campaign_data: 广告系列数据字典，包含：
                - name (str): 广告系列名称（必填）
                - budget (float): 日预算金额（必填）
                - bidding_strategy (str): 出价策略类型，可选值：
                    MAXIMIZE_CLICKS / MAXIMIZE_CONVERSIONS / TARGET_CPA /
                    TARGET_ROAS / MANUAL_CPC（默认: MAXIMIZE_CLICKS）
                - target_countries (List[str]): 投放目标国家/地区代码列表
                    （如 ["CN", "US"]，默认: ["CN"]）
                - advertising_channel_type (str): 投放渠道类型
                    （默认: SEARCH）
                - start_date (str): 开始日期 YYYY-MM-DD（默认: 当天）
                - end_date (str): 结束日期 YYYY-MM-DD（可选）

        Returns:
            Dict[str, Any]: 创建结果，包含：
                - success (bool): 是否创建成功
                - campaign_id (str): 新创建的广告系列 ID
                - campaign_name (str): 广告系列名称
                - resource_name (str): Google Ads 资源名称
                - message (str): 描述信息

        Example:
            >>> data = {
            ...     "name": "春季促销",
            ...     "budget": 5000.0,
            ...     "bidding_strategy": "MAXIMIZE_CLICKS",
            ...     "target_countries": ["CN", "TW", "HK"],
            ... }
            >>> result = service.create_campaign("123-456-7890", data)
            >>> print(result["campaign_id"])
        """
        if self.mock_mode:
            time.sleep(0.1)
            mock_campaign_id = str(int(uuid.uuid4().int % 9000000000) + 1000000000)
            return {
                "success": True,
                "campaign_id": mock_campaign_id,
                "campaign_name": campaign_data.get("name", "未命名广告系列"),
                "resource_name": f"customers/{account_id.replace('-', '')}/campaigns/{mock_campaign_id}",
                "message": f"Mock 模式：广告系列 '{campaign_data.get('name')}' 创建成功",
            }

        try:
            client = self.get_client()
            campaign_service = client.get_service("CampaignService")
            campaign_budget_service = client.get_service("CampaignBudgetService")
            operation_service = client.get_service("GoogleAdsService:Mutate")

            # 1. 创建预算
            budget_operation = client.get_type("CampaignBudgetOperation")
            budget = budget_operation.create
            budget.name = f"预算 - {campaign_data.get('name', '')}"
            budget.amount_micros = int(campaign_data.get("budget", 1000) * 1_000_000)
            budget.delivery_method = client.get_type("BudgetDeliveryMethodEnum").STANDARD

            budget_response = campaign_budget_service.mutate_campaign_budgets(
                customer_id=account_id,
                operations=[budget_operation],
            )
            budget_resource_name = budget_response.results[0].resource_name

            # 2. 创建广告系列
            campaign_operation = client.get_type("CampaignOperation")
            campaign = campaign_operation.create
            campaign.name = campaign_data.get("name", "未命名广告系列")
            campaign.advertising_channel_type = client.get_type(
                "AdvertisingChannelTypeEnum"
            ).value[campaign_data.get("advertising_channel_type", "SEARCH")]

            # 设置预算
            campaign.campaign_budget = budget_resource_name

            # 设置出价策略
            bidding_strategy_type = campaign_data.get("bidding_strategy", "MAXIMIZE_CLICKS")
            campaign_bidding = campaign.bidding_strategy
            campaign_bidding.maximize_clicks.target_cpc_micros = 1000000  # 1.0

            # 设置投放目标
            target_countries = campaign_data.get("target_countries", ["CN"])
            for country_code in target_countries:
                geo_target = campaign.targeting.geo_targets.append(
                    client.get_type("Criterion")
                )
                geo_target.location.location_names[0] = country_code

            # 设置日期
            start_date = campaign_data.get("start_date", "")
            if start_date:
                campaign.start_date = start_date.replace("-", "")
            end_date = campaign_data.get("end_date", "")
            if end_date:
                campaign.end_date = end_date.replace("-", "")

            campaign_response = campaign_service.mutate_campaigns(
                customer_id=account_id,
                operations=[campaign_operation],
            )
            new_campaign_id = campaign_response.results[0].campaign.id

            logger.info(
                "广告系列 '%s' 创建成功，ID=%s",
                campaign_data.get("name"), new_campaign_id,
            )

            return {
                "success": True,
                "campaign_id": str(new_campaign_id),
                "campaign_name": campaign_data.get("name", "未命名广告系列"),
                "resource_name": campaign_response.results[0].resource_name,
                "message": f"广告系列 '{campaign_data.get('name')}' 创建成功",
            }

        except GoogleAdsException as e:
            logger.error("创建广告系列失败: %s", str(e))
            return {
                "success": False,
                "campaign_id": "",
                "campaign_name": campaign_data.get("name", ""),
                "resource_name": "",
                "message": f"创建失败: {str(e)}",
            }
        except Exception as e:
            logger.error("创建广告系列时发生意外错误: %s", str(e))
            return {
                "success": False,
                "campaign_id": "",
                "campaign_name": campaign_data.get("name", ""),
                "resource_name": "",
                "message": f"创建失败（意外错误）: {str(e)}",
            }

    def update_campaign_status(
        self,
        account_id: str,
        campaign_id: str,
        new_status: str,
    ) -> Dict[str, Any]:
        """
        更新广告系列状态

        将指定广告系列的状态更新为启用（ENABLED）或暂停（PAUSED）。
        可用于广告系列的批量暂停或恢复操作。

        在 Mock 模式下，模拟更新过程并返回模拟结果。

        Args:
            account_id: Google Ads 账户 ID
            campaign_id: 要更新的广告系列 ID
            new_status: 新状态，可选值：
                - "ENABLED": 启用广告系列
                - "PAUSED": 暂停广告系列

        Returns:
            Dict[str, Any]: 更新结果，包含：
                - success (bool): 是否更新成功
                - campaign_id (str): 广告系列 ID
                - old_status (str): 更新前的状态
                - new_status (str): 更新后的状态
                - message (str): 描述信息

        Raises:
            ValueError: 当 new_status 不是有效的状态值时抛出

        Example:
            >>> result = service.update_campaign_status("123-456-7890", "1111222233", "PAUSED")
            >>> print(result["success"], result["message"])
        """
        if new_status not in ("ENABLED", "PAUSED"):
            raise ValueError(
                f"无效的状态值: {new_status}。"
                "new_status 必须是 'ENABLED' 或 'PAUSED'"
            )

        if self.mock_mode:
            time.sleep(0.1)
            return {
                "success": True,
                "campaign_id": campaign_id,
                "old_status": "ENABLED" if new_status == "PAUSED" else "PAUSED",
                "new_status": new_status,
                "message": f"Mock 模式：广告系列 {campaign_id} 状态已更新为 {new_status}",
            }

        try:
            client = self.get_client()
            campaign_service = client.get_service("CampaignService")

            # 构建更新操作
            campaign_operation = client.get_type("CampaignOperation")
            campaign = campaign_operation.update
            campaign.resource_name = f"customers/{account_id.replace('-', '')}/campaigns/{campaign_id}"

            status_enum = client.get_type("CampaignStatusEnum").value[new_status]
            campaign.status = status_enum

            # 设置更新掩码，仅更新 status 字段
            field_mask = client.get_type("FieldMask")
            field_mask.paths.append("status")
            campaign_operation.update_mask.CopyFrom(field_mask)

            response = campaign_service.mutate_campaigns(
                customer_id=account_id,
                operations=[campaign_operation],
            )

            logger.info(
                "广告系列 %s 状态已更新为 %s",
                campaign_id, new_status,
            )

            return {
                "success": True,
                "campaign_id": campaign_id,
                "old_status": "PAUSED" if new_status == "ENABLED" else "ENABLED",
                "new_status": new_status,
                "message": f"广告系列 {campaign_id} 状态已成功更新为 {new_status}",
            }

        except GoogleAdsException as e:
            logger.error("更新广告系列状态失败: %s", str(e))
            return {
                "success": False,
                "campaign_id": campaign_id,
                "old_status": "",
                "new_status": new_status,
                "message": f"状态更新失败: {str(e)}",
            }
        except Exception as e:
            logger.error("更新广告系列状态时发生意外错误: %s", str(e))
            return {
                "success": False,
                "campaign_id": campaign_id,
                "old_status": "",
                "new_status": new_status,
                "message": f"状态更新失败（意外错误）: {str(e)}",
            }

    def create_ad(
        self,
        account_id: str,
        ad_group_id: str,
        ad_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        创建广告

        在指定账户的广告组下创建新的广告。支持响应式搜索广告（RSA）格式，
        可设置多个标题和描述以提高投放灵活性。

        在 Mock 模式下，模拟创建过程并返回模拟结果。

        Args:
            account_id: Google Ads 账户 ID
            ad_group_id: 目标广告组 ID
            ad_data: 广告数据字典，包含：
                - headline_1 (str): 标题 1（必填）
                - headline_2 (str): 标题 2（可选）
                - headline_3 (str): 标题 3（可选）
                - description_1 (str): 描述 1（必填）
                - description_2 (str): 描述 2（可选）
                - final_url (str): 最终落地页 URL（必填）
                - display_url (str): 展示 URL（可选）
                - path_1 (str): 路径 1（可选）
                - path_2 (str): 路径 2（可选）

        Returns:
            Dict[str, Any]: 创建结果，包含：
                - success (bool): 是否创建成功
                - ad_id (str): 新创建的广告 ID
                - ad_group_id (str): 所属广告组 ID
                - resource_name (str): Google Ads 资源名称
                - message (str): 描述信息

        Example:
            >>> ad_data = {
            ...     "headline_1": "限时优惠全场折扣",
            ...     "headline_2": "专业品质值得信赖",
            ...     "description_1": "超过 500 万用户的选择",
            ...     "final_url": "https://www.example.com/promo",
            ... }
            >>> result = service.create_ad("123-456-7890", "6666777788", ad_data)
            >>> print(result["ad_id"])
        """
        if self.mock_mode:
            time.sleep(0.1)
            mock_ad_id = str(int(uuid.uuid4().int % 900000000000) + 100000000000)
            return {
                "success": True,
                "ad_id": mock_ad_id,
                "ad_group_id": ad_group_id,
                "resource_name": (
                    f"customers/{account_id.replace('-', '')}"
                    f"/adGroupAds/{ad_group_id}~{mock_ad_id}"
                ),
                "message": f"Mock 模式：广告创建成功，ID={mock_ad_id}",
            }

        try:
            client = self.get_service("AdGroupAdService")

            # 创建响应式搜索广告操作
            ad_group_ad_operation = client.get_type("AdGroupAdOperation")
            ad_group_ad = ad_group_ad_operation.create

            # 设置所属广告组
            ad_group_ad.ad_group = (
                f"customers/{account_id.replace('-', '')}/adGroups/{ad_group_id}"
            )
            ad_group_ad.status = client.get_type("AdGroupAdStatusEnum").ENABLED

            # 设置广告类型为响应式搜索广告
            ad = ad_group_ad.ad
            rsa = ad.responsive_search_ad

            # 收集所有标题
            headlines = [
                ad_data.get("headline_1", ""),
                ad_data.get("headline_2", ""),
                ad_data.get("headline_3", ""),
            ]
            headlines = [h for h in headlines if h]

            for headline_text in headlines:
                headline = rsa.headlines.append(
                    client.get_type("AdTextAsset")
                )
                headline.text = headline_text

            # 收集所有描述
            descriptions = [
                ad_data.get("description_1", ""),
                ad_data.get("description_2", ""),
            ]
            descriptions = [d for d in descriptions if d]

            for desc_text in descriptions:
                description = rsa.descriptions.append(
                    client.get_type("AdTextAsset")
                )
                description.text = desc_text

            # 设置落地页
            if ad_data.get("final_url"):
                ad.final_urls.append(ad_data["final_url"])
            if ad_data.get("display_url"):
                ad.display_url = ad_data["display_url"]

            # 设置路径
            if ad_data.get("path_1"):
                rsa.paths[0] = ad_data["path_1"]
            if ad_data.get("path_2"):
                rsa.paths[1] = ad_data["path_2"]

            response = client.mutate_ad_group_ads(
                customer_id=account_id,
                operations=[ad_group_ad_operation],
            )

            new_ad_id = response.results[0].ad_group_ad.ad.id

            logger.info(
                "广告创建成功，ID=%s，广告组=%s",
                new_ad_id, ad_group_id,
            )

            return {
                "success": True,
                "ad_id": str(new_ad_id),
                "ad_group_id": ad_group_id,
                "resource_name": response.results[0].resource_name,
                "message": f"广告创建成功，ID={new_ad_id}",
            }

        except GoogleAdsException as e:
            logger.error("创建广告失败: %s", str(e))
            return {
                "success": False,
                "ad_id": "",
                "ad_group_id": ad_group_id,
                "resource_name": "",
                "message": f"广告创建失败: {str(e)}",
            }
        except Exception as e:
            logger.error("创建广告时发生意外错误: %s", str(e))
            return {
                "success": False,
                "ad_id": "",
                "ad_group_id": ad_group_id,
                "resource_name": "",
                "message": f"广告创建失败（意外错误）: {str(e)}",
            }

    def add_keywords(
        self,
        account_id: str,
        ad_group_id: str,
        keywords_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        批量添加关键词

        在指定账户的广告组下批量添加关键词。支持设置每个关键词的文本、
        匹配类型和出价。

        在 Mock 模式下，模拟批量添加过程并返回模拟结果。

        Args:
            account_id: Google Ads 账户 ID
            ad_group_id: 目标广告组 ID
            keywords_data: 关键词数据列表，每项包含：
                - text (str): 关键词文本（必填）
                - match_type (str): 匹配类型，可选值：
                    EXACT（精确匹配）/ PHRASE（短语匹配）/ BROAD（广泛匹配）
                    默认: EXACT
                - bid (float): CPC 出价金额（可选）

        Returns:
            Dict[str, Any]: 批量添加结果，包含：
                - success (bool): 整体是否成功
                - total (int): 请求添加的关键词总数
                - succeeded (int): 成功添加的关键词数
                - failed (int): 添加失败的关键词数
                - results (List[Dict]): 每个关键词的添加结果
                - message (str): 描述信息

        Example:
            >>> keywords = [
            ...     {"text": "云计算服务", "match_type": "EXACT", "bid": 2.5},
            ...     {"text": "企业云平台", "match_type": "PHRASE", "bid": 1.8},
            ...     {"text": "数据托管", "match_type": "BROAD", "bid": 1.0},
            ... ]
            >>> result = service.add_keywords("123-456-7890", "6666777788", keywords)
            >>> print(result["succeeded"], result["total"])
        """
        if not keywords_data:
            return {
                "success": True,
                "total": 0,
                "succeeded": 0,
                "failed": 0,
                "results": [],
                "message": "未提供关键词数据，无需添加",
            }

        if self.mock_mode:
            time.sleep(0.1)
            mock_results = []
            for kw in keywords_data:
                mock_kw_id = str(int(uuid.uuid4().int % 900000000000) + 100000000000)
                mock_results.append({
                    "success": True,
                    "keyword_id": mock_kw_id,
                    "text": kw.get("text", ""),
                    "match_type": kw.get("match_type", "EXACT"),
                    "bid": kw.get("bid", 0),
                    "message": f"关键词 '{kw.get('text')}' 添加成功",
                })

            return {
                "success": True,
                "total": len(keywords_data),
                "succeeded": len(mock_results),
                "failed": 0,
                "results": mock_results,
                "message": f"Mock 模式：成功批量添加 {len(mock_results)} 个关键词",
            }

        try:
            client = self.get_client()
            ad_group_criterion_service = client.get_service("AdGroupCriterionService")

            operations = []
            match_type_enum = client.get_type("KeywordMatchTypeEnum")

            for kw_data in keywords_data:
                operation = client.get_type("AdGroupCriterionOperation")
                criterion = operation.create

                # 设置所属广告组
                criterion.ad_group = (
                    f"customers/{account_id.replace('-', '')}/adGroups/{ad_group_id}"
                )

                # 设置关键词
                criterion.keyword.text = kw_data.get("text", "")
                criterion.keyword.match_type = match_type_enum.value.get(
                    kw_data.get("match_type", "EXACT"),
                    match_type_enum.EXACT,
                )

                # 设置状态
                criterion.status = client.get_type(
                    "AdGroupCriterionStatusEnum"
                ).ENABLED

                # 设置出价（如果有）
                if kw_data.get("bid"):
                    criterion.cpc_bid_micros = int(kw_data["bid"] * 1_000_000)

                operations.append(operation)

            response = ad_group_criterion_service.mutate_ad_group_criteria(
                customer_id=account_id,
                operations=operations,
            )

            results = []
            for result in response.results:
                results.append({
                    "success": True,
                    "keyword_id": str(result.ad_group_criterion.criterion_id),
                    "text": result.ad_group_criterion.keyword.text,
                    "match_type": str(
                        result.ad_group_criterion.keyword.match_type
                    ).split(".")[-1],
                    "bid": (
                        result.ad_group_criterion.cpc_bid_micros / 1_000_000
                        if result.ad_group_criterion.cpc_bid_micros
                        else 0
                    ),
                    "message": f"关键词 '{result.ad_group_criterion.keyword.text}' 添加成功",
                })

            logger.info(
                "批量添加关键词完成：成功 %d / 总计 %d",
                len(results), len(keywords_data),
            )

            return {
                "success": True,
                "total": len(keywords_data),
                "succeeded": len(results),
                "failed": len(keywords_data) - len(results),
                "results": results,
                "message": f"成功批量添加 {len(results)} 个关键词",
            }

        except GoogleAdsException as e:
            logger.error("批量添加关键词失败: %s", str(e))
            return {
                "success": False,
                "total": len(keywords_data),
                "succeeded": 0,
                "failed": len(keywords_data),
                "results": [],
                "message": f"批量添加关键词失败: {str(e)}",
            }
        except Exception as e:
            logger.error("批量添加关键词时发生意外错误: %s", str(e))
            return {
                "success": False,
                "total": len(keywords_data),
                "succeeded": 0,
                "failed": len(keywords_data),
                "results": [],
                "message": f"批量添加关键词失败（意外错误）: {str(e)}",
            }
