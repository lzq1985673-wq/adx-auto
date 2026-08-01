"""
SQLAlchemy 数据库模型模块

本模块定义了 ADX Auto 平台的所有数据库模型，包括：
- 租户管理（Tenant）
- 用户管理（User）
- Google Ads 账号（GoogleAdsAccount）
- 广告系列（Campaign）
- 广告组（AdGroup）
- 广告（Ad）
- 关键词（Keyword）
- 落地页（LandingPage）
- 创意任务（CreativeTask）
- 代理提供商（ProxyProvider）
- 同步日志（SyncLog）
- 定时任务（ScheduledTask）

所有模型均包含 id（主键）、created_at（创建时间）、updated_at（更新时间）。
JSON 字段使用 SQLAlchemy 的 JSON 类型存储。
"""

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

# 创建全局数据库实例（需在 Flask app 初始化时调用 db.init_app(app)）
db = SQLAlchemy()


# ============================================================
# 基础 Mixin：为所有模型提供公共字段
# ============================================================
class TimestampMixin:
    """
    时间戳混入类

    为模型提供 created_at 和 updated_at 字段。
    - created_at: 记录创建时间，插入时自动设置为当前 UTC 时间
    - updated_at: 记录更新时间，插入时初始化，后续每次保存时自动更新
    """

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="记录创建时间（UTC）",
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="记录更新时间（UTC）",
    )


# ============================================================
# a) 租户模型
# ============================================================
class Tenant(TimestampMixin, db.Model):
    """
    租户（Tenant）模型

    系统支持多租户架构，每个租户拥有独立的用户、广告账号和配置。
    slug 用于生成租户专属的访问标识。
    """

    __tablename__ = "tenants"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键 ID")

    # 租户名称
    name = db.Column(db.String(128), nullable=False, comment="租户名称")

    # 租户唯一标识符（用于 URL 和 API 路径）
    slug = db.Column(db.String(64), unique=True, nullable=False, comment="租户唯一标识")

    # 套餐类型：free（免费）、annual（年费）、biennial（两年费）
    plan = db.Column(
        db.String(20),
        nullable=False,
        default="free",
        comment="套餐类型：free/annual/biennial",
    )

    # 是否激活
    is_active = db.Column(db.Boolean, default=True, nullable=False, comment="是否激活")

    # AI 模型配置（JSON 格式，如模型选择、温度参数等）
    ai_model_config = db.Column(db.JSON, default=dict, comment="AI 模型配置（JSON）")

    # 代理配置（JSON 格式，如代理提供商、路由规则等）
    proxy_config = db.Column(db.JSON, default=dict, comment="代理配置（JSON）")

    # ============================================================
    # 关联关系
    # ============================================================
    users = db.relationship("User", backref="tenant", lazy="dynamic")
    google_ads_accounts = db.relationship(
        "GoogleAdsAccount", backref="tenant", lazy="dynamic"
    )
    campaigns = db.relationship("Campaign", backref="tenant", lazy="dynamic")
    landing_pages = db.relationship("LandingPage", backref="tenant", lazy="dynamic")
    creative_tasks = db.relationship("CreativeTask", backref="tenant", lazy="dynamic")
    proxy_providers = db.relationship(
        "ProxyProvider", backref="tenant", lazy="dynamic"
    )
    sync_logs = db.relationship("SyncLog", backref="tenant", lazy="dynamic")
    scheduled_tasks = db.relationship(
        "ScheduledTask", backref="tenant", lazy="dynamic"
    )

    def __repr__(self):
        return f"<Tenant(id={self.id}, name='{self.name}', slug='{self.slug}')>"


# ============================================================
# b) 用户模型
# ============================================================
class User(TimestampMixin, db.Model):
    """
    用户（User）模型

    每个用户归属于一个租户，具有不同的角色权限。
    密码以哈希形式存储，不存储明文。
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键 ID")

    # 所属租户 ID
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属租户 ID",
    )

    # 用户名（全局唯一）
    username = db.Column(db.String(64), unique=True, nullable=False, comment="用户名")

    # 邮箱地址（全局唯一）
    email = db.Column(db.String(128), unique=True, nullable=False, comment="邮箱地址")

    # 密码哈希值（存储 bcrypt 或 werkzeug 生成的哈希）
    password_hash = db.Column(
        db.String(256), nullable=False, comment="密码哈希值"
    )

    # 角色：admin（管理员）、manager（经理）、operator（操作员）
    role = db.Column(
        db.String(20),
        nullable=False,
        default="operator",
        comment="角色：admin/manager/operator",
    )

    # 是否激活
    is_active = db.Column(db.Boolean, default=True, nullable=False, comment="是否激活")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


# ============================================================
# c) Google Ads 账号模型
# ============================================================
class GoogleAdsAccount(TimestampMixin, db.Model):
    """
    Google Ads 账号（GoogleAdsAccount）模型

    存储从 Google Ads API 同步的账号信息。
    每个租户可绑定多个 Google Ads 账号。
    """

    __tablename__ = "google_ads_accounts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键 ID")

    # 所属租户 ID
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属租户 ID",
    )

    # MCC 管理中心 ID
    mcc_id = db.Column(db.String(20), nullable=True, comment="MCC 管理中心 ID")

    # Google Ads 账号 ID（唯一）
    account_id = db.Column(
        db.String(20), unique=True, nullable=False, comment="Google Ads 账号 ID"
    )

    # 账号名称
    account_name = db.Column(db.String(256), nullable=False, comment="账号名称")

    # 账号状态：active（活跃）、paused（暂停）、suspended（封停）
    status = db.Column(
        db.String(20),
        nullable=False,
        default="active",
        comment="账号状态：active/paused/suspended",
    )

    # 账号货币（如 USD、CNY）
    currency = db.Column(db.String(10), nullable=True, comment="账号货币")

    # 账号时区（如 Asia/Shanghai）
    timezone = db.Column(db.String(64), nullable=True, comment="账号时区")

    # 最后同步时间
    last_synced_at = db.Column(
        db.DateTime, nullable=True, comment="最后同步时间"
    )

    # ============================================================
    # 关联关系
    # ============================================================
    campaigns = db.relationship("Campaign", backref="google_ads_account", lazy="dynamic")
    sync_logs = db.relationship("SyncLog", backref="google_ads_account", lazy="dynamic")
    creative_tasks = db.relationship(
        "CreativeTask", backref="google_ads_account", lazy="dynamic"
    )

    def __repr__(self):
        return (
            f"<GoogleAdsAccount(id={self.id}, account_id='{self.account_id}', "
            f"name='{self.account_name}')>"
        )


# ============================================================
# d) 广告系列模型
# ============================================================
class Campaign(TimestampMixin, db.Model):
    """
    广告系列（Campaign）模型

    对应 Google Ads 中的 Campaign 实体。
    每个广告系列归属于一个租户和一个 Google Ads 账号。
    """

    __tablename__ = "campaigns"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键 ID")

    # 所属租户 ID
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属租户 ID",
    )

    # 所属 Google Ads 账号 ID
    account_id = db.Column(
        db.Integer,
        db.ForeignKey("google_ads_accounts.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属 Google Ads 账号 ID",
    )

    # Google Ads 原生广告系列 ID
    google_campaign_id = db.Column(
        db.String(30), nullable=False, comment="Google Ads 广告系列 ID"
    )

    # 广告系列名称
    name = db.Column(db.String(256), nullable=False, comment="广告系列名称")

    # 状态：active（活跃）、paused（暂停）、deleted（已删除）
    status = db.Column(
        db.String(20),
        nullable=False,
        default="active",
        comment="状态：active/paused/deleted",
    )

    # 预算（单位：微单位，与 Google Ads API 一致）
    budget = db.Column(db.Float, nullable=True, comment="预算")

    # 出价策略（如 MANUAL_CPC、TARGET CPA 等）
    bidding_strategy = db.Column(
        db.String(64), nullable=True, comment="出价策略"
    )

    # 目标国家/地区列表（JSON 格式，如 ["US", "UK", "CA"]）
    target_countries = db.Column(
        db.JSON, default=list, comment="目标国家/地区（JSON）"
    )

    # 在 Google Ads 中创建的时间
    created_in_google_at = db.Column(
        db.DateTime, nullable=True, comment="在 Google Ads 中创建的时间"
    )

    # ============================================================
    # 关联关系
    # ============================================================
    ad_groups = db.relationship("AdGroup", backref="campaign", lazy="dynamic")

    def __repr__(self):
        return (
            f"<Campaign(id={self.id}, google_campaign_id='{self.google_campaign_id}', "
            f"name='{self.name}')>"
        )


# ============================================================
# e) 广告组模型
# ============================================================
class AdGroup(TimestampMixin, db.Model):
    """
    广告组（AdGroup）模型

    对应 Google Ads 中的 Ad Group 实体。
    每个广告组归属于一个广告系列。
    """

    __tablename__ = "ad_groups"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键 ID")

    # 所属租户 ID
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属租户 ID",
    )

    # 所属广告系列 ID
    campaign_id = db.Column(
        db.Integer,
        db.ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属广告系列 ID",
    )

    # Google Ads 原生广告组 ID
    google_ad_group_id = db.Column(
        db.String(30), nullable=False, comment="Google Ads 广告组 ID"
    )

    # 广告组名称
    name = db.Column(db.String(256), nullable=False, comment="广告组名称")

    # 状态：active（活跃）、paused（暂停）、deleted（已删除）
    status = db.Column(
        db.String(20),
        nullable=False,
        default="active",
        comment="状态：active/paused/deleted",
    )

    # 最高每次点击费用（CPC）
    max_cpc = db.Column(db.Float, nullable=True, comment="最高 CPC")

    # ============================================================
    # 关联关系
    # ============================================================
    ads = db.relationship("Ad", backref="ad_group", lazy="dynamic")
    keywords = db.relationship("Keyword", backref="ad_group", lazy="dynamic")

    def __repr__(self):
        return (
            f"<AdGroup(id={self.id}, google_ad_group_id='{self.google_ad_group_id}', "
            f"name='{self.name}')>"
        )


# ============================================================
# f) 广告模型
# ============================================================
class Ad(TimestampMixin, db.Model):
    """
    广告（Ad）模型

    对应 Google Ads 中的 Ad 实体（响应式搜索广告格式）。
    支持多条标题和描述，可记录是否由 AI 生成及所使用的提示词。
    """

    __tablename__ = "ads"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键 ID")

    # 所属租户 ID
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属租户 ID",
    )

    # 所属广告组 ID
    ad_group_id = db.Column(
        db.Integer,
        db.ForeignKey("ad_groups.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属广告组 ID",
    )

    # Google Ads 原生广告 ID
    google_ad_id = db.Column(
        db.String(30), nullable=True, comment="Google Ads 广告 ID"
    )

    # 标题 1
    headline_1 = db.Column(db.String(30), nullable=True, comment="标题 1")

    # 标题 2
    headline_2 = db.Column(db.String(30), nullable=True, comment="标题 2")

    # 标题 3
    headline_3 = db.Column(db.String(30), nullable=True, comment="标题 3")

    # 描述 1
    description_1 = db.Column(db.String(90), nullable=True, comment="描述 1")

    # 描述 2
    description_2 = db.Column(db.String(90), nullable=True, comment="描述 2")

    # 最终落地页 URL
    final_url = db.Column(db.String(2048), nullable=True, comment="最终落地页 URL")

    # 展示 URL
    display_url = db.Column(db.String(256), nullable=True, comment="展示 URL")

    # 状态：active（活跃）、paused（暂停）、deleted（已删除）
    status = db.Column(
        db.String(20),
        nullable=False,
        default="active",
        comment="状态：active/paused/deleted",
    )

    # 是否由 AI 生成
    ai_generated = db.Column(
        db.Boolean, default=False, nullable=False, comment="是否由 AI 生成"
    )

    # AI 生成时使用的提示词
    ai_prompt_used = db.Column(db.Text, nullable=True, comment="AI 生成时使用的提示词")

    def __repr__(self):
        return (
            f"<Ad(id={self.id}, google_ad_id='{self.google_ad_id}', "
            f"headline_1='{self.headline_1}')>"
        )


# ============================================================
# g) 关键词模型
# ============================================================
class Keyword(TimestampMixin, db.Model):
    """
    关键词（Keyword）模型

    对应 Google Ads 中的 Keyword 实体。
    同一广告组内关键词文本不可重复。
    """

    __tablename__ = "keywords"
    # 同一广告组内关键词文本必须唯一
    __table_args__ = (
        db.UniqueConstraint("ad_group_id", "text", name="uq_adgroup_keyword_text"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键 ID")

    # 所属租户 ID
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属租户 ID",
    )

    # 所属广告组 ID
    ad_group_id = db.Column(
        db.Integer,
        db.ForeignKey("ad_groups.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属广告组 ID",
    )

    # 关键词文本
    text = db.Column(db.String(80), nullable=False, comment="关键词文本")

    # 匹配类型：EXACT（精准）、PHRASE（词组）、BROAD（广泛）
    match_type = db.Column(
        db.String(20),
        nullable=False,
        default="EXACT",
        comment="匹配类型：EXACT/PHRASE/BROAD",
    )

    # 状态：active（活跃）、paused（暂停）、deleted（已删除）
    status = db.Column(
        db.String(20),
        nullable=False,
        default="active",
        comment="状态：active/paused/deleted",
    )

    # 出价
    bid = db.Column(db.Float, nullable=True, comment="关键词出价")

    def __repr__(self):
        return (
            f"<Keyword(id={self.id}, text='{self.text}', "
            f"match_type='{self.match_type}')>"
        )


# ============================================================
# h) 落地页模型
# ============================================================
class LandingPage(TimestampMixin, db.Model):
    """
    落地页（LandingPage）模型

    存储广告投放的目标落地页信息，包括页面 URL、抓取的内容和元数据。
    """

    __tablename__ = "landing_pages"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键 ID")

    # 所属租户 ID
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属租户 ID",
    )

    # 落地页 URL（全局唯一）
    url = db.Column(db.String(2048), unique=True, nullable=False, comment="落地页 URL")

    # 页面标题
    title = db.Column(db.String(256), nullable=True, comment="页面标题")

    # 页面描述
    description = db.Column(db.Text, nullable=True, comment="页面描述")

    # 关键词列表（JSON 格式）
    keywords = db.Column(db.JSON, default=list, comment="关键词列表（JSON）")

    # 抓取时间
    scraped_at = db.Column(db.DateTime, nullable=True, comment="页面抓取时间")

    # 抓取的页面正文内容
    scraped_content = db.Column(db.Text, nullable=True, comment="抓取的页面正文内容")

    # 抓取的页面元数据（JSON 格式，如 og 标签、结构化数据等）
    scraped_metadata = db.Column(
        db.JSON, default=dict, comment="抓取的页面元数据（JSON）"
    )

    # ============================================================
    # 关联关系
    # ============================================================
    creative_tasks = db.relationship(
        "CreativeTask", backref="landing_page", lazy="dynamic"
    )

    def __repr__(self):
        return f"<LandingPage(id={self.id}, url='{self.url}', title='{self.title}')>"


# ============================================================
# i) 创意任务模型
# ============================================================
class CreativeTask(TimestampMixin, db.Model):
    """
    创意任务（CreativeTask）模型

    记录 AI 生成广告创意的异步任务，包括任务状态、生成结果和使用的 AI 参数。
    """

    __tablename__ = "creative_tasks"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键 ID")

    # 所属租户 ID
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属租户 ID",
    )

    # 关联的落地页 ID
    landing_page_id = db.Column(
        db.Integer,
        db.ForeignKey("landing_pages.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联的落地页 ID",
    )

    # 关联的 Google Ads 账号 ID
    account_id = db.Column(
        db.Integer,
        db.ForeignKey("google_ads_accounts.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联的 Google Ads 账号 ID",
    )

    # 任务状态：pending（待处理）、generating（生成中）、completed（已完成）、failed（失败）
    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
        comment="任务状态：pending/generating/completed/failed",
    )

    # AI 生成的标题列表（JSON 格式）
    generated_titles = db.Column(
        db.JSON, default=list, comment="AI 生成的标题（JSON）"
    )

    # AI 生成的描述列表（JSON 格式）
    generated_descriptions = db.Column(
        db.JSON, default=list, comment="AI 生成的描述（JSON）"
    )

    # AI 生成的关键词列表（JSON 格式）
    generated_keywords = db.Column(
        db.JSON, default=list, comment="AI 生成的关键词（JSON）"
    )

    # 本次任务使用的 AI 模型
    ai_model_used = db.Column(
        db.String(64), nullable=True, comment="使用的 AI 模型"
    )

    # 本次任务使用的 AI 提示词
    ai_prompt = db.Column(db.Text, nullable=True, comment="使用的 AI 提示词")

    # 错误信息（任务失败时记录）
    error_message = db.Column(db.Text, nullable=True, comment="错误信息")

    def __repr__(self):
        return f"<CreativeTask(id={self.id}, status='{self.status}')>"


# ============================================================
# j) 代理提供商模型
# ============================================================
class ProxyProvider(TimestampMixin, db.Model):
    """
    代理提供商（ProxyProvider）模型

    管理第三方代理服务提供商的配置信息，支持多种代理类型。
    """

    __tablename__ = "proxy_providers"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键 ID")

    # 所属租户 ID
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属租户 ID",
    )

    # 提供商名称
    name = db.Column(db.String(128), nullable=False, comment="提供商名称")

    # 提供商类型：brightdata、oxylabs、smartproxy、custom
    provider_type = db.Column(
        db.String(20),
        nullable=False,
        comment="提供商类型：brightdata/oxylabs/smartproxy/custom",
    )

    # API 端点地址
    api_endpoint = db.Column(db.String(512), nullable=True, comment="API 端点地址")

    # API 密钥（建议加密存储）
    api_key = db.Column(db.String(512), nullable=True, comment="API 密钥（加密存储）")

    # 国家/地区配置（JSON 格式，用于地区定向代理）
    country_config = db.Column(
        db.JSON, default=dict, comment="国家/地区配置（JSON）"
    )

    # 是否激活
    is_active = db.Column(db.Boolean, default=True, nullable=False, comment="是否激活")

    def __repr__(self):
        return (
            f"<ProxyProvider(id={self.id}, name='{self.name}', "
            f"type='{self.provider_type}')>"
        )


# ============================================================
# k) 同步日志模型
# ============================================================
class SyncLog(TimestampMixin, db.Model):
    """
    同步日志（SyncLog）模型

    记录与 Google Ads API 的数据同步操作日志，包括同步类型、状态和同步数据量。
    """

    __tablename__ = "sync_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键 ID")

    # 所属租户 ID
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属租户 ID",
    )

    # 关联的 Google Ads 账号 ID
    account_id = db.Column(
        db.Integer,
        db.ForeignKey("google_ads_accounts.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联的 Google Ads 账号 ID",
    )

    # 同步类型：full（全量同步）、incremental（增量同步）
    sync_type = db.Column(
        db.String(20),
        nullable=False,
        comment="同步类型：full/incremental",
    )

    # 同步状态：running（运行中）、completed（已完成）、failed（失败）
    status = db.Column(
        db.String(20),
        nullable=False,
        default="running",
        comment="同步状态：running/completed/failed",
    )

    # 同步的记录数量
    records_synced = db.Column(
        db.Integer, default=0, nullable=False, comment="同步的记录数量"
    )

    # 错误信息（同步失败时记录）
    error_message = db.Column(db.Text, nullable=True, comment="错误信息")

    # 同步开始时间
    started_at = db.Column(db.DateTime, nullable=True, comment="同步开始时间")

    # 同步完成时间
    completed_at = db.Column(db.DateTime, nullable=True, comment="同步完成时间")

    def __repr__(self):
        return (
            f"<SyncLog(id={self.id}, sync_type='{self.sync_type}', "
            f"status='{self.status}')>"
        )


# ============================================================
# l) 定时任务模型
# ============================================================
class ScheduledTask(TimestampMixin, db.Model):
    """
    定时任务（ScheduledTask）模型

    管理系统中需要周期性执行的定时任务，使用 crontab 表达式定义调度规则。
    """

    __tablename__ = "scheduled_tasks"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="主键 ID")

    # 所属租户 ID
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属租户 ID",
    )

    # 任务类型（如 sync_google_ads、generate_creative 等）
    task_type = db.Column(db.String(64), nullable=False, comment="任务类型")

    # 任务名称（便于识别）
    name = db.Column(db.String(128), nullable=False, comment="任务名称")

    # Crontab 调度表达式（如 "0 2 * * *" 表示每天凌晨 2 点）
    crontab_expression = db.Column(
        db.String(64), nullable=False, comment="Crontab 调度表达式"
    )

    # 任务配置（JSON 格式，存储任务执行所需的参数）
    config = db.Column(db.JSON, default=dict, comment="任务配置（JSON）")

    # 上次运行时间
    last_run_at = db.Column(db.DateTime, nullable=True, comment="上次运行时间")

    # 下次运行时间
    next_run_at = db.Column(db.DateTime, nullable=True, comment="下次运行时间")

    # 任务状态：active（活跃）、paused（暂停）、failed（失败）
    status = db.Column(
        db.String(20),
        nullable=False,
        default="active",
        comment="任务状态：active/paused/failed",
    )

    # 累计运行次数
    run_count = db.Column(
        db.Integer, default=0, nullable=False, comment="累计运行次数"
    )

    # 累计错误次数
    error_count = db.Column(
        db.Integer, default=0, nullable=False, comment="累计错误次数"
    )

    def __repr__(self):
        return (
            f"<ScheduledTask(id={self.id}, name='{self.name}', "
            f"task_type='{self.task_type}')>"
        )


# ============================================================
# 自动更新 updated_at 字段的监听器
# ============================================================
@db.event.listens_for(db.Model, "before_update", propagate=True)
def timestamp_before_update(mapper, connection, target):
    """
    在模型更新之前，自动将 updated_at 字段设置为当前 UTC 时间。

    此事件监听器对所有继承 db.Model 的模型生效，
    确保每次修改记录时 updated_at 都会自动更新。
    """
    # 仅当目标模型包含 updated_at 字段时才更新
    if hasattr(target, "updated_at"):
        target.updated_at = datetime.utcnow()
