# -*- coding: utf-8 -*-
"""
代理 IP 管理服务

提供代理 IP 的获取、测试、会话管理等功能，支持多个代理供应商。
当真实供应商 SDK 不可用时，自动切换到 mock 模式。
"""

import logging
import time
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class ProxyService:
    """代理 IP 管理服务类

    负责管理多个代理供应商的配置，提供代理 IP 的获取、
    测试以及带代理的 HTTP 会话构建等功能。

    Attributes:
        providers (list): 代理供应商配置列表
        mock_mode (bool): 是否使用 mock 模式（无真实 SDK 时自动启用）
    """

    def __init__(self, providers_config=None):
        """初始化代理服务

        Args:
            providers_config (list, optional): 代理供应商配置列表，每项包含
                name（供应商名称）、type（供应商类型）、api_endpoint（API 地址）、
                api_key（API 密钥）、country_config（国家配置映射）。
                默认为空列表。
        """
        if providers_config is None:
            providers_config = []
        self.providers = []
        self.mock_mode = True  # 默认 mock 模式，检测到真实 SDK 后切换

        # 尝试导入真实供应商 SDK
        try:
            import brightdata  # noqa: F401
            self.mock_mode = False
            logger.info("检测到 brightdata SDK，使用真实模式")
        except ImportError:
            logger.info("未检测到 brightdata SDK，使用 mock 模式")

        # 初始化供应商
        for config in providers_config:
            self.add_provider(config)

        logger.info("ProxyService 初始化完成，已加载 %d 个供应商，mock_mode=%s",
                     len(self.providers), self.mock_mode)

    def add_provider(self, provider_config):
        """添加代理供应商

        Args:
            provider_config (dict): 供应商配置字典，包含以下字段：
                - name (str): 供应商名称
                - type (str): 供应商类型（如 "brightdata"）
                - api_endpoint (str): API 端点地址
                - api_key (str): API 密钥
                - country_config (dict): 国家配置，键为国家代码，值为该国家的代理配置
        """
        # 校验必要字段
        required_fields = ["name", "type", "api_endpoint", "api_key"]
        for field in required_fields:
            if field not in provider_config:
                raise ValueError(f"供应商配置缺少必要字段: {field}")

        # 检查是否已存在同名供应商
        for existing in self.providers:
            if existing["name"] == provider_config["name"]:
                logger.warning("供应商 '%s' 已存在，将覆盖配置", provider_config["name"])
                self.providers.remove(existing)
                break

        self.providers.append(provider_config)
        logger.info("已添加代理供应商: %s (类型: %s)", provider_config["name"], provider_config["type"])

    def remove_provider(self, name):
        """移除指定名称的代理供应商

        Args:
            name (str): 要移除的供应商名称

        Returns:
            bool: 是否成功移除
        """
        for i, provider in enumerate(self.providers):
            if provider["name"] == name:
                self.providers.pop(i)
                logger.info("已移除代理供应商: %s", name)
                return True
        logger.warning("未找到供应商: %s，移除失败", name)
        return False

    def get_proxy(self, country_code='US'):
        """获取指定国家的代理 IP

        根据国家代码查找对应供应商配置，调用供应商 API 获取代理 IP。
        在 mock 模式下返回模拟的代理地址。

        Args:
            country_code (str): 国家代码，默认为 'US'

        Returns:
            dict or None: 代理信息字典，包含 host、port、protocol、country 等字段；
                          获取失败时返回 None
        """
        # 在所有供应商中查找支持该国家的配置
        target_provider = None
        country_settings = None

        for provider in self.providers:
            country_config = provider.get("country_config", {})
            if country_code in country_config:
                target_provider = provider
                country_settings = country_config[country_code]
                break

        if target_provider is None:
            logger.warning("没有供应商支持国家代码: %s", country_code)
            return None

        if self.mock_mode:
            # mock 模式：返回模拟的代理 IP
            mock_proxy = {
                "host": "203.0.113.42",
                "port": 12345,
                "protocol": "https",
                "country": country_code,
                "provider": target_provider["name"],
                "username": None,
                "password": None,
            }
            logger.info("[Mock] 返回模拟代理: %s:%d (%s)",
                        mock_proxy["host"], mock_proxy["port"], country_code)
            return mock_proxy
        else:
            # 真实模式：调用供应商 API 获取代理
            try:
                proxy = self._fetch_proxy_from_provider(target_provider, country_settings, country_code)
                logger.info("成功从供应商 '%s' 获取 %s 代理", target_provider["name"], country_code)
                return proxy
            except Exception as e:
                logger.error("从供应商 '%s' 获取代理失败: %s", target_provider["name"], str(e))
                return None

    def _fetch_proxy_from_provider(self, provider, country_settings, country_code):
        """从供应商 API 获取真实代理 IP

        Args:
            provider (dict): 供应商配置
            country_settings (dict): 该国家的代理配置
            country_code (str): 国家代码

        Returns:
            dict: 代理信息字典

        Raises:
            Exception: API 调用失败时抛出
        """
        import brightdata  # noqa: F401

        api_endpoint = provider["api_endpoint"]
        api_key = provider["api_key"]

        # 根据供应商类型调用不同的获取逻辑
        if provider["type"] == "brightdata":
            # 构建 BrightData 请求参数
            params = {
                "country": country_code,
                **country_settings,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
            }

            response = requests.get(api_endpoint, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            return {
                "host": data.get("proxy", data.get("host", "")),
                "port": int(data.get("port", 22222)),
                "protocol": country_settings.get("protocol", "https"),
                "country": country_code,
                "provider": provider["name"],
                "username": data.get("username", country_settings.get("username")),
                "password": data.get("password", country_settings.get("password")),
            }
        else:
            raise ValueError(f"不支持的供应商类型: {provider['type']}")

    def build_proxy_url(self, proxy_dict):
        """构建代理 URL

        将代理字典转换为标准的代理 URL 格式。

        Args:
            proxy_dict (dict): 代理信息字典，包含 host、port、
                               可选的 username 和 password、protocol

        Returns:
            str: 代理 URL，格式为 "http://user:pass@host:port" 或 "http://host:port"
        """
        if proxy_dict is None:
            return None

        host = proxy_dict.get("host", "")
        port = proxy_dict.get("port", "")
        username = proxy_dict.get("username")
        password = proxy_dict.get("password")

        # 确定协议（代理 URL 通常使用 http 作为协议前缀）
        scheme = "http"

        if username and password:
            # 带认证的代理 URL
            proxy_url = f"{scheme}://{username}:{password}@{host}:{port}"
        else:
            # 无认证的代理 URL
            proxy_url = f"{scheme}://{host}:{port}"

        return proxy_url

    def get_session_with_proxy(self, country_code='US'):
        """获取带代理配置的 requests.Session 对象

        创建一个配置了代理、超时和重试策略的 HTTP 会话。

        Args:
            country_code (str): 代理国家代码，默认为 'US'

        Returns:
            requests.Session: 配置好代理的会话对象；获取代理失败时返回普通会话
        """
        session = requests.Session()

        # 获取代理
        proxy_dict = self.get_proxy(country_code)

        if proxy_dict:
            proxy_url = self.build_proxy_url(proxy_dict)
            session.proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }
            logger.info("会话已配置 %s 代理: %s", country_code, proxy_url)
        else:
            logger.warning("未能获取 %s 代理，使用直连模式", country_code)

        # 配置重试策略：最多重试 3 次，状态码 429/500/502/503/504 时重试
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # 设置默认超时（连接超时 10 秒，读取超时 30 秒）
        session.request = lambda *args, **kwargs: requests.Session.request(session, *args, timeout=(10, 30), **kwargs)

        return session

    def test_proxy(self, proxy_dict):
        """测试代理是否可用

        通过访问 httpbin.org/ip 验证代理连通性，并测量延迟。

        Args:
            proxy_dict (dict): 代理信息字典

        Returns:
            dict: 测试结果，包含以下字段：
                - success (bool): 是否成功
                - ip (str): 代理出口 IP
                - latency_ms (float): 延迟毫秒数
                - error (str, optional): 错误信息
        """
        if proxy_dict is None:
            return {
                "success": False,
                "ip": "",
                "latency_ms": 0,
                "error": "代理字典为空",
            }

        proxy_url = self.build_proxy_url(proxy_dict)
        test_url = "https://httpbin.org/ip"

        proxies = {
            "http": proxy_url,
            "https": proxy_url,
        }

        start_time = time.time()
        try:
            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=(10, 30),
            )
            latency_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                origin_ip = data.get("origin", "")
                logger.info("代理测试成功，出口 IP: %s，延迟: %.1fms", origin_ip, latency_ms)
                return {
                    "success": True,
                    "ip": origin_ip,
                    "latency_ms": round(latency_ms, 2),
                }
            else:
                logger.warning("代理测试失败，HTTP 状态码: %d", response.status_code)
                return {
                    "success": False,
                    "ip": "",
                    "latency_ms": round(latency_ms, 2),
                    "error": f"HTTP 状态码: {response.status_code}",
                }

        except requests.exceptions.Timeout:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("代理测试超时")
            return {
                "success": False,
                "ip": "",
                "latency_ms": round(latency_ms, 2),
                "error": "连接超时",
            }
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("代理测试异常: %s", str(e))
            return {
                "success": False,
                "ip": "",
                "latency_ms": round(latency_ms, 2),
                "error": str(e),
            }

    def list_providers(self):
        """列出所有已注册的代理供应商配置

        返回供应商列表，但隐藏敏感的 api_key 字段。

        Returns:
            list: 供应商配置列表，api_key 被替换为 "***"
        """
        safe_list = []
        for provider in self.providers:
            safe_config = {
                "name": provider["name"],
                "type": provider["type"],
                "api_endpoint": provider["api_endpoint"],
                "api_key": "***",  # 隐藏敏感信息
                "country_config": provider.get("country_config", {}),
            }
            safe_list.append(safe_config)
        return safe_list