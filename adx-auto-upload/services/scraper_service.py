# -*- coding: utf-8 -*-
"""
落地页爬虫服务

负责爬取广告落地页内容，提取标题、描述、关键词、图片、链接等信息，
并提供关键词提取和广告文案线索分析功能。
"""

import re
import json
from datetime import datetime, timezone
from collections import Counter

# 尝试导入 requests，不可用时回退到 urllib
try:
    import requests as _requests_lib
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False
    from urllib import request as _urllib_request
    from urllib import error as _urllib_error

# ========================= 停用词列表 =========================

# 英文停用词
_EN_STOP_WORDS = frozenset([
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need", "dare",
    "ought", "used", "it", "its", "this", "that", "these", "those",
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you",
    "your", "yours", "yourself", "yourselves", "he", "him", "his",
    "himself", "she", "her", "hers", "herself", "they", "them", "their",
    "theirs", "themselves", "what", "which", "who", "whom", "when",
    "where", "why", "how", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "s", "t", "just", "don", "now",
    "about", "above", "after", "again", "against", "below", "between",
    "during", "further", "here", "there", "once", "then", "up", "down",
    "out", "off", "over", "under", "if", "also", "into", "through",
    "because", "while", "before", "any", "many", "much", "get", "got",
    "make", "like", "well", "back", "even", "still", "new", "way", "use",
])

# 中文停用词
_ZH_STOP_WORDS = frozenset([
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
    "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
    "会", "着", "没有", "看", "好", "自己", "这", "他", "她", "它",
    "们", "那", "里", "为", "来", "对", "可以", "个", "与", "但",
    "被", "从", "把", "让", "用", "中", "将", "能", "已", "之",
    "还", "而", "及", "等", "或", "其", "所", "更", "做", "可",
    "最", "些", "什么", "如何", "这个", "那个", "没", "吗", "呢",
    "吧", "啊", "哦", "嗯", "呀", "么", "哈", "啦", "喔", "嘛",
    "并", "且", "若", "则", "因", "此", "以", "于", "向", "给",
    "当", "比", "按", "通过", "进行", "使用", "包括", "关于", "以下",
    "以上", "之间", "之后", "之前", "同时", "以及", "其中", "或者",
    "不是", "就是", "可能", "应该", "需要", "能够", "已经", "虽然",
    "但是", "因为", "所以", "如果", "那么", "这样", "那样", "我们",
    "他们", "你们", "自己", "这些", "那些", "这种", "那种", "哪个",
    "哪些", "怎么", "为什么", "多", "少", "大", "小", "来", "去",
])

# 合并所有停用词
_ALL_STOP_WORDS = _EN_STOP_WORDS | _ZH_STOP_WORDS

# 默认 User-Agent
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# 请求超时时间（秒）
_DEFAULT_TIMEOUT = 10


class ScraperService:
    """
    落地页爬虫服务

    负责爬取指定 URL 的落地页内容，解析 HTML 提取关键信息，
    并提供关键词提取和广告文案线索分析能力。
    """

    def __init__(self, proxy_manager=None):
        """
        初始化爬虫服务

        Args:
            proxy_manager: 可选的代理管理器实例，用于通过代理发送请求。
                           该对象需提供 get_proxy() 方法返回代理地址字典。
        """
        self.proxy_manager = proxy_manager
        # 预编译正则表达式，提升匹配性能
        self._title_re = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)
        self._meta_desc_re = re.compile(
            r'<meta\s+[^>]*name\s*=\s*["\']description["\'][^>]*content\s*=\s*["\'](.*?)["\']',
            re.IGNORECASE | re.DOTALL,
        )
        self._meta_desc_re2 = re.compile(
            r'<meta\s+[^>]*content\s*=\s*["\'](.*?)["\'][^>]*name\s*=\s*["\']description["\']',
            re.IGNORECASE | re.DOTALL,
        )
        self._h1_re = re.compile(r'<h1[^>]*>(.*?)</h1>', re.IGNORECASE | re.DOTALL)
        self._img_re = re.compile(r'<img\s+[^>]*src\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
        self._link_re = re.compile(r'<a\s+[^>]*href\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
        self._body_re = re.compile(
            r'<body[^>]*>(.*?)</body>', re.IGNORECASE | re.DOTALL
        )
        self._script_re = re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)
        self._style_re = re.compile(r'<style[^>]*>.*?</style>', re.IGNORECASE | re.DOTALL)
        self._tag_re = re.compile(r'<[^>]+>', re.DOTALL)
        self._entity_re = re.compile(r'&[a-zA-Z]+;|&#\d+;|&#x[0-9a-fA-F]+;')
        self._whitespace_re = re.compile(r'\s+')

    def scrape(self, url):
        """
        爬取落地页内容

        Args:
            url: 要爬取的落地页 URL

        Returns:
            dict: 包含爬取结果的字典，字段包括：
                - url: 实际请求的 URL
                - status_code: HTTP 状态码
                - title: 页面标题
                - meta_description: 元描述
                - h1_tags: h1 标签列表
                - body_text: 正文文本（截取前 3000 字符）
                - keywords: 关键词列表（从 meta 和 h1 提取）
                - images: 图片 src 列表（前 10 张）
                - links: 链接列表（前 20 个）
                - scraped_at: 爬取时间（ISO 格式）
            异常时返回: {"error": "错误描述字符串"}
        """
        html = None
        status_code = None

        try:
            # 根据是否有 requests 库选择请求方式
            if _HAS_REQUESTS:
                html, status_code = self._request_with_requests(url)
            else:
                html, status_code = self._request_with_urllib(url)

            # 解析 HTML 内容
            return self._parse_html(html, url, status_code)

        except Exception as e:
            # 捕获所有异常（超时、连接错误等），返回错误信息
            return {"error": str(e)}

    def _request_with_requests(self, url):
        """
        使用 requests 库发送 HTTP 请求

        Args:
            url: 请求的 URL

        Returns:
            tuple: (html_text, status_code)

        Raises:
            requests.Timeout: 请求超时
            requests.ConnectionError: 连接错误
        """
        # 构建请求头
        headers = {"User-Agent": _DEFAULT_USER_AGENT}

        # 构建代理配置
        proxies = None
        if self.proxy_manager is not None:
            proxy_url = self.proxy_manager.get_proxy()
            if proxy_url:
                proxies = {"http": proxy_url, "https": proxy_url}

        # 发送 GET 请求
        response = _requests_lib.get(
            url,
            headers=headers,
            proxies=proxies,
            timeout=_DEFAULT_TIMEOUT,
            verify=False,  # 不验证 SSL 证书（落地页场景兼容性）
        )

        return response.text, response.status_code

    def _request_with_urllib(self, url):
        """
        使用 urllib 发送 HTTP 请求（requests 不可用时的回退方案）

        Args:
            url: 请求的 URL

        Returns:
            tuple: (html_text, status_code)
        """
        # 构建请求对象
        req = _urllib_request.Request(url, headers={"User-Agent": _DEFAULT_USER_AGENT})

        # 如果有代理，设置代理处理器
        if self.proxy_manager is not None:
            proxy_url = self.proxy_manager.get_proxy()
            if proxy_url:
                handler = _urllib_request.ProxyHandler(
                    {"http": proxy_url, "https": proxy_url}
                )
                opener = _urllib_request.build_opener(handler)
                response = opener.open(req, timeout=_DEFAULT_TIMEOUT)
                return response.read().decode("utf-8", errors="replace"), 200

        # 无代理，直接请求
        response = _urllib_request.urlopen(req, timeout=_DEFAULT_TIMEOUT)
        return response.read().decode("utf-8", errors="replace"), 200

    def _parse_html(self, html, url, status_code):
        """
        解析 HTML 内容，提取关键信息

        Args:
            html: HTML 文本
            url: 请求的 URL
            status_code: HTTP 状态码

        Returns:
            dict: 结构化的解析结果
        """
        # 提取页面标题
        title_match = self._title_re.search(html)
        title = self._clean_text(title_match.group(1)) if title_match else ""

        # 提取 meta description
        meta_desc = ""
        desc_match = self._meta_desc_re.search(html)
        if not desc_match:
            desc_match = self._meta_desc_re2.search(html)
        if desc_match:
            meta_desc = self._clean_text(desc_match.group(1))

        # 提取所有 h1 标签
        h1_matches = self._h1_re.findall(html)
        h1_tags = [self._clean_text(h1) for h1 in h1_matches if self._clean_text(h1)]

        # 提取正文文本
        body_text = ""
        body_match = self._body_re.search(html)
        if body_match:
            body_html = body_match.group(1)
            # 移除 script 和 style 标签
            body_html = self._script_re.sub("", body_html)
            body_html = self._style_re.sub("", body_html)
            # 移除所有 HTML 标签
            body_html = self._tag_re.sub(" ", body_html)
            # 清理文本
            body_text = self._clean_text(body_html)
            # 截取前 3000 字符
            body_text = body_text[:3000]

        # 提取图片 src（前 10 张）
        img_matches = self._img_re.findall(html)
        images = img_matches[:10]

        # 提取链接（前 20 个），过滤空链接和锚点
        link_matches = self._link_re.findall(html)
        links = [
            link for link in link_matches
            if link and not link.startswith(("#", "javascript:", "mailto:"))
        ][:20]

        # 从 meta 和 h1 中提取初步关键词
        keywords = []
        keyword_text = " ".join([title, meta_desc] + h1_tags)
        if keyword_text.strip():
            # 简单分词：中文按字/词拆分，英文按空格拆分
            raw_words = self._simple_tokenize(keyword_text)
            # 去重并去除停用词
            seen = set()
            for word in raw_words:
                word_lower = word.lower()
                if word_lower not in _ALL_STOP_WORDS and word_lower not in seen and len(word_lower) > 1:
                    keywords.append(word_lower)
                    seen.add(word_lower)

        return {
            "url": url,
            "status_code": status_code,
            "title": title,
            "meta_description": meta_desc,
            "h1_tags": h1_tags,
            "body_text": body_text,
            "keywords": keywords,
            "images": images,
            "links": links,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }

    def extract_keywords(self, scraped_data):
        """
        从爬取数据中提取关键词

        综合分析页面标题、meta 描述、h1 标签和正文前 500 字符，
        通过词频分析提取高频词/短语作为关键词。

        Args:
            scraped_data: scrape() 方法返回的爬取结果字典

        Returns:
            list: 关键词列表，每个元素为 {"word": "xxx", "score": 0.9}
        """
        # 如果爬取数据包含错误，直接返回空列表
        if "error" in scraped_data:
            return []

        # 拼接需要分析的文本字段
        parts = [
            scraped_data.get("title", ""),
            scraped_data.get("meta_description", ""),
            " ".join(scraped_data.get("h1_tags", [])),
            scraped_data.get("body_text", "")[:500],  # 正文只取前 500 字符
        ]
        combined_text = " ".join(parts)

        if not combined_text.strip():
            return []

        # 分词
        words = self._simple_tokenize(combined_text)

        # 过滤停用词和短词
        filtered_words = []
        for word in words:
            word_lower = word.lower()
            if (
                word_lower not in _ALL_STOP_WORDS
                and len(word_lower) > 1
            ):
                filtered_words.append(word_lower)

        if not filtered_words:
            return []

        # 词频统计
        word_counts = Counter(filtered_words)

        # 同时提取二元组（bigram）短语
        bigrams = []
        for i in range(len(filtered_words) - 1):
            bigram = f"{filtered_words[i]} {filtered_words[i + 1]}"
            bigrams.append(bigram)
        bigram_counts = Counter(bigrams)

        # 合并单字词和二元组，计算得分
        total_words = len(filtered_words)
        scored_keywords = []

        # 处理单字词频率
        max_count = max(word_counts.values()) if word_counts else 1
        for word, count in word_counts.most_common(40):
            score = round(count / max_count, 2)
            scored_keywords.append({"word": word, "score": score})

        # 处理二元组频率（出现 2 次以上的才有意义）
        for bigram, count in bigram_counts.most_common(20):
            if count >= 2:
                score = round(count / max_count, 2)
                scored_keywords.append({"word": bigram, "score": score})

        # 按得分降序排序，取前 20 个
        scored_keywords.sort(key=lambda x: x["score"], reverse=True)
        return scored_keywords[:20]

    def extract_ad_copy_hints(self, scraped_data):
        """
        从爬取数据中提取广告文案线索

        通过文本模式匹配（正则表达式），分析页面内容并提取：
        - 核心卖点（selling_points）
        - 用户痛点（pain_points）
        - 评价/证言片段（testimonials）
        - 行动号召（call_to_actions）

        Args:
            scraped_data: scrape() 方法返回的爬取结果字典

        Returns:
            dict: {"selling_points": [], "pain_points": [], "testimonials": [], "call_to_actions": []}
        """
        # 默认返回结构
        result = {
            "selling_points": [],
            "pain_points": [],
            "testimonials": [],
            "call_to_actions": [],
        }

        # 如果爬取数据包含错误，直接返回空结果
        if "error" in scraped_data:
            return result

        # 拼接全文用于分析
        full_text = " ".join([
            scraped_data.get("title", ""),
            scraped_data.get("meta_description", ""),
            " ".join(scraped_data.get("h1_tags", [])),
            scraped_data.get("body_text", ""),
        ])

        if not full_text.strip():
            return result

        # ----- 提取核心卖点 -----
        # 匹配常见的卖点表达模式：形容词/特征 + 名词 的结构
        selling_patterns = [
            # 英文卖点模式
            r'(?:powerful|professional|advanced|premium|leading|top-rated|best|'
            r'innovative|unique|fast|easy|simple|secure|reliable|affordable|'
            r'free|unlimited|instant|automatic|smart|efficient)\s+[\w\s]{5,40}',
            # 中文卖点模式
            r'(?:高效|专业|领先|优质|创新|快速|简单|安全|可靠|实惠|免费|'
            r'无限|即时|自动|智能|便捷|强大|顶级|核心|独家|全新)[\u4e00-\u9fff\w]{2,15}',
        ]
        for pattern in selling_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            for match in matches:
                cleaned = self._clean_text(match)
                if cleaned and cleaned not in result["selling_points"]:
                    result["selling_points"].append(cleaned)

        # ----- 提取用户痛点 -----
        # 匹配常见的痛点表达模式
        pain_patterns = [
            # 英文痛点模式
            r'(?:struggle|problem|issue|challenge|difficulty|worry|concern|'
            r'frustrat|tired of|waste|complicated|expensive|slow|hard to|'
            r'difficult to|lose|risk|fail)[\w\s]{3,40}',
            # 中文痛点模式
            r'(?:困扰|问题|难题|挑战|担心|烦恼|浪费|复杂|昂贵|缓慢|困难|'
            r'风险|失败|痛点|难于|无法|不再|摆脱|解决)[\u4e00-\u9fff\w]{2,15}',
        ]
        for pattern in pain_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            for match in matches:
                cleaned = self._clean_text(match)
                if cleaned and cleaned not in result["pain_points"]:
                    result["pain_points"].append(cleaned)

        # ----- 提取评价/证言片段 -----
        # 匹配引号内容或星级评价附近的文本
        testimonial_patterns = [
            # 引号中的评价内容
            r'"([^"]{10,200})"',
            r"'([^']{10,200})'",
            # 星级评价模式
            r'(\d\.?\d?\s*(?:out of|\/)\s*5\s*(?:stars?|星|评分)[\w\s,\.]{0,100})',
            # 中文评价标记
            r'(?:用户|客户|评价|好评|推荐|反馈|体验)[：:：]?\s*[""「]?(.{5,100})[""」]?',
        ]
        for pattern in testimonial_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            for match in matches:
                cleaned = self._clean_text(match) if isinstance(match, str) else str(match)
                if cleaned and len(cleaned) > 10 and cleaned not in result["testimonials"]:
                    result["testimonials"].append(cleaned)

        # ----- 提取行动号召（CTA） -----
        # 匹配按钮文本、链接文本中的 CTA 表达
        cta_patterns = [
            # 英文 CTA 模式
            r'(?:sign up|get started|try (?:it |now|free)|buy now|order now|'
            r'learn more|read more|click here|download (?:now|free)|subscribe|'
            r'contact us|join (?:now|free|today)|register|start free|shop now|'
            r'book (?:now|today)|schedule|request|get (?:a quote|your free))',
            # 中文 CTA 模式
            r'(?:立即注册|免费试用|马上开始|立即购买|现在订购|了解更多|'
            r'点击这里|免费下载|订阅|联系我们|立即加入|立即体验|马上预约|'
            r'获取报价|免费获取|开始使用|一键下单)',
        ]
        for pattern in cta_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            for match in matches:
                cleaned = self._clean_text(match)
                if cleaned and cleaned not in result["call_to_actions"]:
                    result["call_to_actions"].append(cleaned)

        # 从链接文本中补充 CTA（链接文字通常就是 CTA）
        for link in scraped_data.get("links", []):
            link_text = self._clean_text(link)
            if link_text and len(link_text) < 50:
                for pattern in cta_patterns:
                    if re.search(pattern, link_text, re.IGNORECASE):
                        if link_text not in result["call_to_actions"]:
                            result["call_to_actions"].append(link_text)
                        break

        # 限制各列表的最大长度，避免数据过多
        result["selling_points"] = result["selling_points"][:10]
        result["pain_points"] = result["pain_points"][:10]
        result["testimonials"] = result["testimonials"][:5]
        result["call_to_actions"] = result["call_to_actions"][:10]

        return result

    def _clean_text(self, text):
        """
        清理 HTML 文本：去除 HTML 实体、多余空白等

        Args:
            text: 待清理的文本

        Returns:
            str: 清理后的纯文本
        """
        if not text:
            return ""
        # 解码常见的 HTML 实体
        text = self._entity_re.sub(" ", text)
        # 替换连续空白为单个空格
        text = self._whitespace_re.sub(" ", text)
        return text.strip()

    def _simple_tokenize(self, text):
        """
        简单分词：对混合中英文文本进行基础分词

        英文按空格和标点拆分，中文按连续汉字序列提取（每个字或两字组合作为词）。

        Args:
            text: 待分词的文本

        Returns:
            list: 分词结果列表
        """
        tokens = []

        # 提取英文单词（含连字符）
        en_words = re.findall(r'[a-zA-Z][a-zA-Z0-9\-]+', text)
        tokens.extend(en_words)

        # 提取中文连续字符序列，然后做简单的 bigram 切分
        zh_segments = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        for segment in zh_segments:
            # 生成 bigram（相邻两个字组成一个词）
            for i in range(len(segment) - 1):
                bigram = segment[i:i + 2]
                tokens.append(bigram)
            # 也保留三字词
            for i in range(len(segment) - 2):
                trigram = segment[i:i + 3]
                tokens.append(trigram)

        return tokens