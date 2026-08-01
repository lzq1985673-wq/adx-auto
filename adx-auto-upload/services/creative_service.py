# -*- coding: utf-8 -*-
"""
AI 广告创意生成服务

利用 AI 模型（如 GPT-4o-mini）根据落地页信息自动生成 Google Ads 广告文案，
包括标题、描述和关键词。
"""

import json
import re

# 尝试导入 openai 库，不可用时启用 mock 模式
try:
    from openai import OpenAI
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False


class CreativeService:
    """
    AI 广告创意生成服务

    根据落地页的爬取数据，通过 AI 模型生成符合 Google Ads 规范的广告创意文案，
    包括标题、描述和带匹配类型的关键词。
    """

    def __init__(self, model_name=None, api_key=None):
        """
        初始化广告创意生成服务

        Args:
            model_name: AI 模型名称，默认从 config 读取或使用 gpt-4o-mini
            api_key: OpenAI API 密钥，默认从 config 读取
        """
        # 尝试从 config 模块读取默认配置
        self.model_name = model_name
        self.api_key = api_key

        if self.model_name is None or self.api_key is None:
            try:
                from config import settings
                if self.model_name is None:
                    # 从配置中读取模型名称
                    self.model_name = getattr(settings, "AI_MODEL_NAME", "gpt-4o-mini")
                if self.api_key is None:
                    # 从配置中读取 API 密钥
                    self.api_key = getattr(settings, "OPENAI_API_KEY", "")
            except (ImportError, AttributeError):
                # 配置模块不存在或缺少对应属性，使用默认值
                if self.model_name is None:
                    self.model_name = "gpt-4o-mini"
                if self.api_key is None:
                    self.api_key = ""

        # 判断是否使用 mock 模式（没有 openai 库或没有 API 密钥）
        self.mock_mode = (not _HAS_OPENAI) or (not self.api_key)

        # 初始化 OpenAI 客户端（非 mock 模式下）
        self._client = None
        if not self.mock_mode:
            self._client = OpenAI(api_key=self.api_key)

    def generate_creative(self, landing_page_data, target_countries=[], language="en"):
        """
        生成完整的广告创意（标题 + 描述 + 关键词）

        根据落地页信息，调用 AI 生成符合 Google Ads 规范的完整广告创意。

        Args:
            landing_page_data: 落地页爬取数据字典（来自 ScraperService.scrape）
            target_countries: 目标投放国家列表，如 ["US", "UK", "CA"]
            language: 广告语言，默认 "en"

        Returns:
            dict: 广告创意结果字典，包含：
                - titles: 标题列表（每个 ≤30 字符）
                - descriptions: 描述列表（每个 ≤90 字符）
                - keywords: 关键词列表，每项包含 text 和 match_type
                - raw_response: AI 的原始响应文本
        """
        # 构建完整的广告创意 prompt
        user_prompt = self._build_ad_prompt(landing_page_data, target_countries, language)

        # 定义系统提示词：设定 AI 角色为专业的 Google Ads 文案专家
        system_prompt = (
            "你是一个专业的 Google Ads 广告文案专家，拥有丰富的数字营销经验。"
            "你擅长根据落地页内容撰写高转化率的广告文案。"
            "请始终以 JSON 格式返回结果，不要包含任何额外的说明文字或 markdown 标记。"
        )

        # 调用 AI 生成内容
        raw_response = self._call_ai(user_prompt, system_prompt)

        # 尝试解析 AI 返回的 JSON
        parsed = self._parse_creative_response(raw_response)

        return {
            "titles": parsed.get("titles", []),
            "descriptions": parsed.get("descriptions", []),
            "keywords": parsed.get("keywords", []),
            "raw_response": raw_response,
        }

    def generate_headlines(self, context, count=15, max_length=30):
        """
        仅生成广告标题

        根据落地页上下文信息，生成指定数量的广告标题。

        Args:
            context: 落地页数据字典
            count: 生成标题数量，默认 15
            max_length: 每个标题的最大字符长度，默认 30

        Returns:
            list: 标题字符串列表
        """
        # 构建标题生成的 prompt
        prompt = (
            f"请根据以下落地页信息生成 {count} 个 Google Ads 广告标题。\n"
            f"每个标题不超过 {max_length} 个字符。\n"
            f"标题应该简洁有力，突出核心卖点，吸引用户点击。\n\n"
            f"落地页标题: {context.get('title', 'N/A')}\n"
            f"页面描述: {context.get('meta_description', 'N/A')}\n"
            f"H1标签: {', '.join(context.get('h1_tags', []))}\n"
            f"关键词: {', '.join(context.get('keywords', []))}\n\n"
            f'请以 JSON 格式返回，格式为: {{"titles": ["标题1", "标题2", ...]}}'
        )

        system_prompt = (
            "你是一个专业的 Google Ads 广告文案专家。"
            "请仅返回 JSON 格式的结果，不要包含任何额外文字。"
        )

        # 调用 AI
        raw_response = self._call_ai(prompt, system_prompt)

        # 解析响应
        try:
            parsed = json.loads(raw_response)
            titles = parsed.get("titles", [])
        except (json.JSONDecodeError, AttributeError):
            # 解析失败，返回模拟数据
            titles = self._mock_headlines(context, count, max_length)

        # 确保标题长度不超过限制，并截取指定数量
        result = []
        for title in titles:
            if len(title) <= max_length:
                result.append(title)
            else:
                result.append(title[:max_length - 1] + "…")
        return result[:count]

    def generate_descriptions(self, context, count=4, max_length=90):
        """
        仅生成广告描述

        根据落地页上下文信息，生成指定数量的广告描述文案。

        Args:
            context: 落地页数据字典
            count: 生成描述数量，默认 4
            max_length: 每个描述的最大字符长度，默认 90

        Returns:
            list: 描述字符串列表
        """
        # 构建描述生成的 prompt
        prompt = (
            f"请根据以下落地页信息生成 {count} 个 Google Ads 广告描述。\n"
            f"每个描述不超过 {max_length} 个字符。\n"
            f"描述应该详细说明产品/服务价值，包含行动号召。\n\n"
            f"落地页标题: {context.get('title', 'N/A')}\n"
            f"页面描述: {context.get('meta_description', 'N/A')}\n"
            f"H1标签: {', '.join(context.get('h1_tags', []))}\n"
            f"正文摘要: {context.get('body_text', 'N/A')[:300]}\n\n"
            f'请以 JSON 格式返回，格式为: {{"descriptions": ["描述1", "描述2", ...]}}'
        )

        system_prompt = (
            "你是一个专业的 Google Ads 广告文案专家。"
            "请仅返回 JSON 格式的结果，不要包含任何额外文字。"
        )

        # 调用 AI
        raw_response = self._call_ai(prompt, system_prompt)

        # 解析响应
        try:
            parsed = json.loads(raw_response)
            descriptions = parsed.get("descriptions", [])
        except (json.JSONDecodeError, AttributeError):
            # 解析失败，返回模拟数据
            descriptions = self._mock_descriptions(context, count, max_length)

        # 确保描述长度不超过限制，并截取指定数量
        result = []
        for desc in descriptions:
            if len(desc) <= max_length:
                result.append(desc)
            else:
                result.append(desc[:max_length - 1] + "…")
        return result[:count]

    def generate_keywords(self, context, count=30):
        """
        生成广告关键词

        根据落地页上下文信息，生成带匹配类型的广告关键词。

        Args:
            context: 落地页数据字典
            count: 生成关键词数量，默认 30

        Returns:
            list: 关键词字典列表，每项包含 "text" 和 "match_type"（EXACT/PHRASE/BROAD）
        """
        # 构建关键词生成的 prompt
        prompt = (
            f"请根据以下落地页信息生成 {count} 个 Google Ads 广告关键词。\n"
            f"关键词需要区分匹配类型：EXACT（精确匹配）、PHRASE（短语匹配）、BROAD（广泛匹配）。\n"
            f"大约 1/3 精确匹配、1/3 短语匹配、1/3 广泛匹配。\n\n"
            f"落地页标题: {context.get('title', 'N/A')}\n"
            f"页面描述: {context.get('meta_description', 'N/A')}\n"
            f"H1标签: {', '.join(context.get('h1_tags', []))}\n"
            f"已有关键词: {', '.join(context.get('keywords', []))}\n"
            f"正文摘要: {context.get('body_text', 'N/A')[:500]}\n\n"
            f'请以 JSON 格式返回，格式为: {{"keywords": [{{"text": "关键词", "match_type": "EXACT"}}, ...]}}'
        )

        system_prompt = (
            "你是一个专业的 Google Ads 广告文案专家，精通关键词策略。"
            "请仅返回 JSON 格式的结果，不要包含任何额外文字。"
        )

        # 调用 AI
        raw_response = self._call_ai(prompt, system_prompt)

        # 解析响应
        try:
            parsed = json.loads(raw_response)
            keywords = parsed.get("keywords", [])
            # 确保每个关键词都有 text 和 match_type 字段
            valid_keywords = []
            for kw in keywords:
                if isinstance(kw, dict) and "text" in kw:
                    valid_keywords.append({
                        "text": kw["text"],
                        "match_type": kw.get("match_type", "BROAD").upper(),
                    })
                elif isinstance(kw, str):
                    # 如果返回的是纯字符串，默认为 BROAD 匹配
                    valid_keywords.append({"text": kw, "match_type": "BROAD"})
            return valid_keywords[:count]
        except (json.JSONDecodeError, AttributeError):
            # 解析失败，返回模拟数据
            return self._mock_keywords(context, count)

    def _call_ai(self, prompt, system=""):
        """
        调用 AI 模型

        mock 模式下根据 prompt 关键字返回逼真的模拟数据。
        真实模式下通过 openai 库调用 ChatCompletion API。
        解析 JSON 格式的响应，失败则返回结构化的模拟数据。

        Args:
            prompt: 用户提示词
            system: 系统提示词（可选）

        Returns:
            str: AI 的响应文本（通常是 JSON 字符串）
        """
        if self.mock_mode:
            # Mock 模式：根据 prompt 内容生成模拟响应
            return self._generate_mock_response(prompt, system)

        # 真实模式：调用 OpenAI ChatCompletion API
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,   # 适度的创造性
                max_tokens=2000,   # 足够生成广告文案
            )

            content = response.choices[0].message.content.strip()

            # 尝试提取 JSON 内容（有些模型会在 JSON 外面包裹 markdown 代码块）
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1).strip()

            return content

        except Exception as e:
            # API 调用失败，返回模拟数据
            return self._generate_mock_response(prompt, system)

    def _build_ad_prompt(self, landing_page_data, target_countries, language):
        """
        构建广告创意生成的完整 prompt

        将落地页数据、目标国家和语言要求整合为结构化的 prompt 文本。

        Args:
            landing_page_data: 落地页爬取数据字典
            target_countries: 目标投放国家列表
            language: 广告语言代码

        Returns:
            str: 构建好的完整 prompt 文本
        """
        # 提取落地页关键信息
        title = landing_page_data.get("title", "N/A")
        meta_desc = landing_page_data.get("meta_description", "N/A")
        h1_tags = landing_page_data.get("h1_tags", [])
        keywords = landing_page_data.get("keywords", [])
        body_text = landing_page_data.get("body_text", "")

        # 构建目标国家信息
        countries_info = ""
        if target_countries:
            countries_info = f"目标投放国家: {', '.join(target_countries)}\n"
        else:
            countries_info = "目标投放国家: 未指定（全球投放）\n"

        # 拼接完整的 prompt
        prompt = (
            f"请根据以下落地页信息生成 Google Ads 广告创意。\n\n"
            f"=== 落地页信息 ===\n"
            f"页面标题: {title}\n"
            f"页面描述: {meta_desc}\n"
            f"H1标签: {', '.join(h1_tags) if h1_tags else '无'}\n"
            f"提取的关键词: {', '.join(keywords) if keywords else '无'}\n"
            f"正文摘要: {body_text[:800] if body_text else '无'}\n"
            f"{countries_info}"
            f"广告语言: {language}\n\n"
            f"=== 生成要求 ===\n"
            f"1. 生成 15 个标题（每个不超过 30 个字符），要简洁有力、突出卖点\n"
            f"2. 生成 4 个描述（每个不超过 90 个字符），要包含价值主张和行动号召\n"
            f"3. 生成 30 个关键词（区分 EXACT、PHRASE、BROAD 三种匹配类型，各约 10 个）\n\n"
            f'请严格以如下 JSON 格式返回，不要包含任何其他文字:\n'
            f'{{\n'
            f'  "titles": ["标题1", "标题2", ...],\n'
            f'  "descriptions": ["描述1", "描述2", "描述3", "描述4"],\n'
            f'  "keywords": [\n'
            f'    {{"text": "关键词文本", "match_type": "EXACT"}},\n'
            f'    {{"text": "关键词文本", "match_type": "PHRASE"}},\n'
            f'    {{"text": "关键词文本", "match_type": "BROAD"}}\n'
            f'  ]\n'
            f'}}'
        )

        return prompt

    def _parse_creative_response(self, raw_response):
        """
        解析 AI 返回的广告创意 JSON 响应

        Args:
            raw_response: AI 的原始响应文本

        Returns:
            dict: 解析后的广告创意字典
        """
        try:
            # 尝试直接解析 JSON
            parsed = json.loads(raw_response)
        except (json.JSONDecodeError, TypeError):
            try:
                # 尝试从 markdown 代码块中提取 JSON
                json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw_response, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(1).strip())
                else:
                    # 尝试找到第一个 { 和最后一个 } 之间的内容
                    start = raw_response.find("{")
                    end = raw_response.rfind("}")
                    if start != -1 and end != -1:
                        parsed = json.loads(raw_response[start:end + 1])
                    else:
                        # 完全无法解析，返回模拟数据
                        parsed = self._get_fallback_creative_data()
            except (json.JSONDecodeError, TypeError):
                parsed = self._get_fallback_creative_data()

        # 确保返回的数据结构完整
        return {
            "titles": parsed.get("titles", []),
            "descriptions": parsed.get("descriptions", []),
            "keywords": parsed.get("keywords", []),
        }

    def _get_fallback_creative_data(self):
        """
        获取兜底的模拟广告创意数据

        当 AI 响应解析失败时使用。

        Returns:
            dict: 结构化的模拟广告创意数据
        """
        return {
            "titles": [
                "Get Started Today",
                "Try It Free Now",
                "Limited Time Offer",
                "Top Rated Solution",
                "Fast & Easy Setup",
                "Trusted by Millions",
                "Boost Your Results",
                "No Credit Card Needed",
                "Sign Up in Seconds",
                "Professional Grade Tool",
                "Save Time & Money",
                "Join 10K+ Users",
                "Best Value Choice",
                "Instant Access",
                "Start Free Trial",
            ],
            "descriptions": [
                "Discover the power of our solution. Sign up for a free trial today and see results fast.",
                "Join thousands of satisfied customers. Get started now with no credit card required.",
                "Transform your workflow with our easy-to-use platform. Try it free for 14 days.",
                "The #1 rated tool for professionals. Start your journey today and unlock premium features.",
            ],
            "keywords": [
                {"text": "best online tool", "match_type": "EXACT"},
                {"text": "free trial software", "match_type": "EXACT"},
                {"text": "professional solution", "match_type": "EXACT"},
                {"text": "easy setup platform", "match_type": "EXACT"},
                {"text": "top rated service", "match_type": "EXACT"},
                {"text": "affordable pricing", "match_type": "EXACT"},
                {"text": "fast results", "match_type": "EXACT"},
                {"text": "secure platform", "match_type": "EXACT"},
                {"text": "reliable service", "match_type": "EXACT"},
                {"text": "instant access tool", "match_type": "EXACT"},
                {"text": "\"online management tool\"", "match_type": "PHRASE"},
                {"text": "\"free trial signup\"", "match_type": "PHRASE"},
                {"text": "\"professional grade software\"", "match_type": "PHRASE"},
                {"text": "\"easy to use platform\"", "match_type": "PHRASE"},
                {"text": "\"boost productivity\"", "match_type": "PHRASE"},
                {"text": "\"save time and money\"", "match_type": "PHRASE"},
                {"text": "\"trusted by professionals\"", "match_type": "PHRASE"},
                {"text": "\"no credit card required\"", "match_type": "PHRASE"},
                {"text": "\"instant access account\"", "match_type": "PHRASE"},
                {"text": "\"best value choice\"", "match_type": "PHRASE"},
                {"text": "online tool for business", "match_type": "BROAD"},
                {"text": "software free trial sign up", "match_type": "BROAD"},
                {"text": "how to improve workflow", "match_type": "BROAD"},
                {"text": "professional management solution", "match_type": "BROAD"},
                {"text": "affordable business platform", "match_type": "BROAD"},
                {"text": "fast easy online setup", "match_type": "BROAD"},
                {"text": "top rated tools comparison", "match_type": "BROAD"},
                {"text": "secure reliable service review", "match_type": "BROAD"},
                {"text": "boost results with software", "match_type": "BROAD"},
                {"text": "start free no credit card", "match_type": "BROAD"},
            ],
        }

    def _generate_mock_response(self, prompt, system=""):
        """
        根据 prompt 内容生成模拟的 AI 响应

        在 mock 模式下使用，根据 prompt 中包含的关键字判断需要生成什么类型的响应，
        返回逼真的 JSON 模拟数据。

        Args:
            prompt: 用户提示词
            system: 系统提示词

        Returns:
            str: JSON 格式的模拟响应文本
        """
        prompt_lower = prompt.lower()

        # 如果 prompt 同时要求标题、描述和关键词，返回完整创意
        if "titles" in prompt_lower and "descriptions" in prompt_lower and "keywords" in prompt_lower:
            return json.dumps(self._get_fallback_creative_data(), ensure_ascii=False)

        # 如果只要求标题
        if "标题" in prompt or "headline" in prompt_lower:
            mock_data = {
                "titles": [
                    "Get Started Today",
                    "Try It Free Now",
                    "Limited Time Offer",
                    "Top Rated Solution",
                    "Fast & Easy Setup",
                    "Trusted by Millions",
                    "Boost Your Results",
                    "No Credit Card Needed",
                    "Sign Up in Seconds",
                    "Professional Grade Tool",
                    "Save Time & Money",
                    "Join 10K+ Users",
                    "Best Value Choice",
                    "Instant Access",
                    "Start Free Trial",
                ],
            }
            return json.dumps(mock_data, ensure_ascii=False)

        # 如果只要求描述
        if "描述" in prompt or "description" in prompt_lower:
            mock_data = {
                "descriptions": [
                    "Discover the power of our solution. Sign up for a free trial today and see results fast.",
                    "Join thousands of satisfied customers. Get started now with no credit card required.",
                    "Transform your workflow with our easy-to-use platform. Try it free for 14 days.",
                    "The #1 rated tool for professionals. Start your journey today and unlock premium features.",
                ],
            }
            return json.dumps(mock_data, ensure_ascii=False)

        # 如果只要求关键词
        if "关键词" in prompt or "keyword" in prompt_lower:
            mock_data = {
                "keywords": [
                    {"text": "best online tool", "match_type": "EXACT"},
                    {"text": "free trial software", "match_type": "EXACT"},
                    {"text": "professional solution", "match_type": "EXACT"},
                    {"text": "easy setup platform", "match_type": "EXACT"},
                    {"text": "top rated service", "match_type": "EXACT"},
                    {"text": "affordable pricing", "match_type": "EXACT"},
                    {"text": "fast results", "match_type": "EXACT"},
                    {"text": "secure platform", "match_type": "EXACT"},
                    {"text": "reliable service", "match_type": "EXACT"},
                    {"text": "instant access tool", "match_type": "EXACT"},
                    {"text": "\"online management tool\"", "match_type": "PHRASE"},
                    {"text": "\"free trial signup\"", "match_type": "PHRASE"},
                    {"text": "\"professional grade software\"", "match_type": "PHRASE"},
                    {"text": "\"easy to use platform\"", "match_type": "PHRASE"},
                    {"text": "\"boost productivity\"", "match_type": "PHRASE"},
                    {"text": "\"save time and money\"", "match_type": "PHRASE"},
                    {"text": "\"trusted by professionals\"", "match_type": "PHRASE"},
                    {"text": "\"no credit card required\"", "match_type": "PHRASE"},
                    {"text": "\"instant access account\"", "match_type": "PHRASE"},
                    {"text": "\"best value choice\"", "match_type": "PHRASE"},
                    {"text": "online tool for business", "match_type": "BROAD"},
                    {"text": "software free trial sign up", "match_type": "BROAD"},
                    {"text": "how to improve workflow", "match_type": "BROAD"},
                    {"text": "professional management solution", "match_type": "BROAD"},
                    {"text": "affordable business platform", "match_type": "BROAD"},
                    {"text": "fast easy online setup", "match_type": "BROAD"},
                    {"text": "top rated tools comparison", "match_type": "BROAD"},
                    {"text": "secure reliable service review", "match_type": "BROAD"},
                    {"text": "boost results with software", "match_type": "BROAD"},
                    {"text": "start free no credit card", "match_type": "BROAD"},
                ],
            }
            return json.dumps(mock_data, ensure_ascii=False)

        # 默认返回完整创意数据
        return json.dumps(self._get_fallback_creative_data(), ensure_ascii=False)

    def _mock_headlines(self, context, count, max_length):
        """
        生成模拟的标题数据

        Args:
            context: 落地页数据字典
            count: 需要的标题数量
            max_length: 标题最大长度

        Returns:
            list: 模拟标题列表
        """
        # 基于落地页标题生成变体
        base_title = context.get("title", "Get Started Today")
        base_short = base_title[:max_length] if len(base_title) > max_length else base_title

        headlines = [
            base_short,
            "Try It Free Now",
            "Sign Up Today",
            "Limited Time Offer",
            "Top Rated Solution",
            "Fast & Easy Setup",
            "Trusted by Thousands",
            "Boost Your Results",
            "No Credit Card Needed",
            "Professional Grade Tool",
            "Save Time & Money",
            "Join Our Community",
            "Best Value Online",
            "Instant Access",
            "Start Your Free Trial",
        ]

        # 过滤超长标题并截取指定数量
        result = [h for h in headlines if len(h) <= max_length]
        return result[:count]

    def _mock_descriptions(self, context, count, max_length):
        """
        生成模拟的描述数据

        Args:
            context: 落地页数据字典
            count: 需要的描述数量
            max_length: 描述最大长度

        Returns:
            list: 模拟描述列表
        """
        descriptions = [
            "Discover the power of our solution. Sign up today and see results.",
            "Join thousands of satisfied customers. Get started with no credit card.",
            "Transform your workflow with our easy-to-use platform. Try it free.",
            "The #1 rated tool for professionals. Start your journey today.",
        ]

        # 过滤超长描述并截取指定数量
        result = [d for d in descriptions if len(d) <= max_length]
        return result[:count]

    def _mock_keywords(self, context, count):
        """
        生成模拟的关键词数据

        Args:
            context: 落地页数据字典
            count: 需要的关键词数量

        Returns:
            list: 模拟关键词列表
        """
        match_types = ["EXACT", "PHRASE", "BROAD"]
        keywords = []

        # 基于落地页关键词生成带匹配类型的关键词
        base_keywords = context.get("keywords", [])
        if base_keywords:
            for i, kw in enumerate(base_keywords[:count]):
                match_type = match_types[i % 3]
                keywords.append({"text": kw, "match_type": match_type})
        else:
            # 使用默认关键词
            default_keywords = [
                "online tool", "free trial", "best solution", "professional service",
                "easy setup", "top rated", "affordable", "fast results",
                "secure platform", "reliable tool",
                "management software", "business solution", "productivity tool",
                "workflow automation", "cloud platform",
                "team collaboration", "data analytics", "project management",
                "customer support", "enterprise software",
            ]
            for i, kw in enumerate(default_keywords[:count]):
                match_type = match_types[i % 3]
                keywords.append({"text": kw, "match_type": match_type})

        return keywords[:count]