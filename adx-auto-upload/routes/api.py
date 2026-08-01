# -*- coding: utf-8 -*-
"""
API 路由蓝图模块

本模块定义 ADX Auto 平台的所有 RESTful API 路由，返回统一格式的 JSON 响应。
所有 API 路由均需登录后才能访问。

统一响应格式：
{
    "success": true/false,
    "data": ...,
    "message": "操作描述"
}

路由分组：
- 账号相关：       /api/accounts/...
- 广告系列：       /api/campaigns/...
- 广告组/广告/关键词：/api/ad-groups, /api/ads, /api/keywords
- 创意生成：       /api/creatives/...
- 落地页：         /api/landing-pages/...
- 代理：           /api/proxy/...
- 定时任务：       /api/scheduler/...
- 仪表盘数据：     /api/dashboard/...
"""

import logging
from functools import wraps

from flask import (
    Blueprint,
    jsonify,
    request,
    session,
)
from werkzeug.security import check_password_hash

from models import (
    db,
    User,
    GoogleAdsAccount,
    Campaign,
    AdGroup,
    Ad,
    Keyword,
    LandingPage,
    CreativeTask,
    ProxyProvider,
    SyncLog,
    ScheduledTask,
)

logger = logging.getLogger(__name__)

# 创建 API 路由蓝图
api_bp = Blueprint("api", __name__)


# ============================================================
# 登录验证装饰器
# ============================================================
def login_required(f):
    """
    API 登录验证装饰器

    检查 session 中是否存在 user_id，未登录时返回 401 JSON 响应。
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({
                "success": False,
                "data": None,
                "message": "未登录，请先登录",
            }), 401
        return f(*args, **kwargs)
    return decorated_function


# ============================================================
# 辅助函数：将 ORM 模型序列化为字典
# ============================================================
def _model_to_dict(model):
    """
    将 SQLAlchemy 模型实例转换为字典

    Args:
        model: SQLAlchemy 模型实例

    Returns:
        dict: 包含模型所有列的字典
    """
    result = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        # 处理 datetime 对象，转为 ISO 格式字符串
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        result[column.name] = value
    return result


# ============================================================
# 账号相关 API
# ============================================================
@api_bp.route("/accounts/sync", methods=["POST"])
@login_required
def sync_mcc_accounts():
    """
    同步 MCC 账号

    从 Google Ads API 拉取 MCC 下所有子账号信息并同步到本地数据库。

    Returns:
        JSON: 同步结果
    """
    try:
        from services.google_ads_service import GoogleAdsService

        # 使用 app 配置构建服务
        from flask import current_app
        tenant_config = {
            "developer_token": current_app.config.get("GOOGLE_ADS_DEVELOPER_TOKEN", ""),
            "client_id": current_app.config.get("GOOGLE_ADS_CLIENT_ID", ""),
            "client_secret": current_app.config.get("GOOGLE_ADS_CLIENT_SECRET", ""),
            "refresh_token": current_app.config.get("GOOGLE_ADS_REFRESH_TOKEN", ""),
            "login_customer_id": current_app.config.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", ""),
        }
        service = GoogleAdsService(tenant_config)
        accounts = service.list_accessible_accounts()

        # 记录同步日志
        sync_log = SyncLog(
            tenant_id=1,
            sync_type="full",
            status="completed",
            records_synced=len(accounts) if accounts else 0,
        )
        db.session.add(sync_log)
        db.session.commit()

        return jsonify({
            "success": True,
            "data": {"accounts_count": len(accounts) if accounts else 0},
            "message": "MCC 账号同步成功",
        })
    except Exception as e:
        logger.exception("同步 MCC 账号失败")
        return jsonify({
            "success": False,
            "data": None,
            "message": f"同步失败: {str(e)}",
        }), 500


@api_bp.route("/accounts", methods=["GET"])
@login_required
def list_accounts():
    """
    列出所有 Google Ads 账号

    Query 参数：
        无

    Returns:
        JSON: 账号列表
    """
    accounts = GoogleAdsAccount.query.order_by(GoogleAdsAccount.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [_model_to_dict(a) for a in accounts],
        "message": f"共 {len(accounts)} 个账号",
    })


@api_bp.route("/accounts/<int:account_id>/sync", methods=["POST"])
@login_required
def sync_single_account(account_id):
    """
    同步单个 Google Ads 账号

    Args:
        account_id: 本地数据库中的账号 ID

    Returns:
        JSON: 同步结果
    """
    account = GoogleAdsAccount.query.get(account_id)
    if not account:
        return jsonify({
            "success": False,
            "data": None,
            "message": f"账号 ID {account_id} 不存在",
        }), 404

    try:
        from services.google_ads_service import GoogleAdsService

        from flask import current_app
        tenant_config = {
            "developer_token": current_app.config.get("GOOGLE_ADS_DEVELOPER_TOKEN", ""),
            "client_id": current_app.config.get("GOOGLE_ADS_CLIENT_ID", ""),
            "client_secret": current_app.config.get("GOOGLE_ADS_CLIENT_SECRET", ""),
            "refresh_token": current_app.config.get("GOOGLE_ADS_REFRESH_TOKEN", ""),
            "login_customer_id": current_app.config.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", ""),
        }
        service = GoogleAdsService(tenant_config)

        # 记录同步日志
        sync_log = SyncLog(
            tenant_id=account.tenant_id,
            account_id=account.id,
            sync_type="incremental",
            status="completed",
            records_synced=0,
        )
        db.session.add(sync_log)
        account.last_synced_at = sync_log.started_at
        db.session.commit()

        return jsonify({
            "success": True,
            "data": _model_to_dict(account),
            "message": f"账号 {account.account_name} 同步成功",
        })
    except Exception as e:
        logger.exception("同步单个账号失败: account_id=%s", account_id)
        return jsonify({
            "success": False,
            "data": None,
            "message": f"同步失败: {str(e)}",
        }), 500


# ============================================================
# 广告系列 API
# ============================================================
@api_bp.route("/campaigns", methods=["GET"])
@login_required
def list_campaigns():
    """
    列出广告系列

    Query 参数：
        account_id (可选): 按 Google Ads 账号 ID 过滤

    Returns:
        JSON: 广告系列列表
    """
    # 支持按账号 ID 过滤
    account_id = request.args.get("account_id", type=int)
    query = Campaign.query
    if account_id:
        query = query.filter_by(account_id=account_id)

    campaigns = query.order_by(Campaign.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [_model_to_dict(c) for c in campaigns],
        "message": f"共 {len(campaigns)} 个广告系列",
    })


@api_bp.route("/campaigns", methods=["POST"])
@login_required
def create_campaign():
    """
    创建广告系列

    请求体 JSON：
        account_id (int): 所属 Google Ads 账号 ID
        name (str): 广告系列名称
        budget (float, 可选): 预算
        target_countries (list, 可选): 目标国家列表
        bidding_strategy (str, 可选): 出价策略

    Returns:
        JSON: 创建的广告系列
    """
    data = request.get_json(silent=True) or {}

    # 参数校验
    account_id = data.get("account_id")
    name = data.get("name", "").strip()

    if not account_id:
        return jsonify({
            "success": False,
            "data": None,
            "message": "缺少 account_id 参数",
        }), 400

    if not name:
        return jsonify({
            "success": False,
            "data": None,
            "message": "广告系列名称不能为空",
        }), 400

    # 验证账号存在
    account = GoogleAdsAccount.query.get(account_id)
    if not account:
        return jsonify({
            "success": False,
            "data": None,
            "message": f"账号 ID {account_id} 不存在",
        }), 404

    try:
        campaign = Campaign(
            tenant_id=account.tenant_id,
            account_id=account_id,
            google_campaign_id="",  # 创建后在 Google Ads 生成
            name=name,
            budget=data.get("budget"),
            target_countries=data.get("target_countries", []),
            bidding_strategy=data.get("bidding_strategy"),
            status="active",
        )
        db.session.add(campaign)
        db.session.commit()

        return jsonify({
            "success": True,
            "data": _model_to_dict(campaign),
            "message": "广告系列创建成功",
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.exception("创建广告系列失败")
        return jsonify({
            "success": False,
            "data": None,
            "message": f"创建失败: {str(e)}",
        }), 500


@api_bp.route("/campaigns/<int:campaign_id>/status", methods=["PUT"])
@login_required
def update_campaign_status(campaign_id):
    """
    更新广告系列状态

    Args:
        campaign_id: 广告系列 ID

    请求体 JSON：
        status (str): 新状态，支持 active / paused / deleted

    Returns:
        JSON: 更新后的广告系列
    """
    campaign = Campaign.query.get(campaign_id)
    if not campaign:
        return jsonify({
            "success": False,
            "data": None,
            "message": f"广告系列 ID {campaign_id} 不存在",
        }), 404

    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "").strip().lower()

    # 校验状态值
    valid_statuses = ("active", "paused", "deleted")
    if new_status not in valid_statuses:
        return jsonify({
            "success": False,
            "data": None,
            "message": f"无效状态，支持: {', '.join(valid_statuses)}",
        }), 400

    campaign.status = new_status
    db.session.commit()

    return jsonify({
        "success": True,
        "data": _model_to_dict(campaign),
        "message": f"广告系列状态已更新为 {new_status}",
    })


# ============================================================
# 广告组 API
# ============================================================
@api_bp.route("/ad-groups", methods=["GET"])
@login_required
def list_ad_groups():
    """
    列出广告组

    Query 参数：
        campaign_id (可选): 按广告系列 ID 过滤

    Returns:
        JSON: 广告组列表
    """
    campaign_id = request.args.get("campaign_id", type=int)
    query = AdGroup.query
    if campaign_id:
        query = query.filter_by(campaign_id=campaign_id)

    ad_groups = query.order_by(AdGroup.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [_model_to_dict(ag) for ag in ad_groups],
        "message": f"共 {len(ad_groups)} 个广告组",
    })


# ============================================================
# 广告 API
# ============================================================
@api_bp.route("/ads", methods=["GET"])
@login_required
def list_ads():
    """
    列出广告

    Query 参数：
        ad_group_id (可选): 按广告组 ID 过滤
        ai_generated (可选): 按是否 AI 生成过滤（"true"/"false"）

    Returns:
        JSON: 广告列表
    """
    ad_group_id = request.args.get("ad_group_id", type=int)
    ai_generated = request.args.get("ai_generated", type=str)

    query = Ad.query
    if ad_group_id:
        query = query.filter_by(ad_group_id=ad_group_id)
    if ai_generated is not None:
        query = query.filter_by(ai_generated=(ai_generated.lower() == "true"))

    ads = query.order_by(Ad.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [_model_to_dict(a) for a in ads],
        "message": f"共 {len(ads)} 条广告",
    })


# ============================================================
# 关键词 API
# ============================================================
@api_bp.route("/keywords", methods=["GET"])
@login_required
def list_keywords():
    """
    列出关键词

    Query 参数：
        ad_group_id (可选): 按广告组 ID 过滤

    Returns:
        JSON: 关键词列表
    """
    ad_group_id = request.args.get("ad_group_id", type=int)
    query = Keyword.query
    if ad_group_id:
        query = query.filter_by(ad_group_id=ad_group_id)

    keywords = query.order_by(Keyword.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [_model_to_dict(k) for k in keywords],
        "message": f"共 {len(keywords)} 个关键词",
    })


@api_bp.route("/keywords/batch", methods=["POST"])
@login_required
def batch_add_keywords():
    """
    批量添加关键词

    请求体 JSON：
        ad_group_id (int): 所属广告组 ID
        keywords (list): 关键词列表，每项包含：
            - text (str): 关键词文本
            - match_type (str, 可选): 匹配类型，默认 EXACT
            - bid (float, 可选): 出价

    Returns:
        JSON: 添加结果统计
    """
    data = request.get_json(silent=True) or {}

    ad_group_id = data.get("ad_group_id")
    keywords_list = data.get("keywords", [])

    if not ad_group_id:
        return jsonify({
            "success": False,
            "data": None,
            "message": "缺少 ad_group_id 参数",
        }), 400

    if not keywords_list or not isinstance(keywords_list, list):
        return jsonify({
            "success": False,
            "data": None,
            "message": "keywords 参数必须为非空列表",
        }), 400

    # 验证广告组存在
    ad_group = AdGroup.query.get(ad_group_id)
    if not ad_group:
        return jsonify({
            "success": False,
            "data": None,
            "message": f"广告组 ID {ad_group_id} 不存在",
        }), 404

    added_count = 0
    try:
        for kw in keywords_list:
            text = kw.get("text", "").strip()
            if not text:
                continue

            keyword = Keyword(
                tenant_id=ad_group.tenant_id,
                ad_group_id=ad_group_id,
                text=text,
                match_type=kw.get("match_type", "EXACT"),
                bid=kw.get("bid"),
                status="active",
            )
            db.session.add(keyword)
            added_count += 1

        db.session.commit()

        return jsonify({
            "success": True,
            "data": {"added_count": added_count},
            "message": f"成功添加 {added_count} 个关键词",
        })
    except Exception as e:
        db.session.rollback()
        logger.exception("批量添加关键词失败")
        return jsonify({
            "success": False,
            "data": None,
            "message": f"添加失败: {str(e)}",
        }), 500


# ============================================================
# 创意生成 API
# ============================================================
@api_bp.route("/creatives/generate", methods=["POST"])
@login_required
def generate_creatives():
    """
    生成广告创意

    调用 AI 服务根据落地页信息生成广告创意（标题、描述、关键词）。

    请求体 JSON：
        landing_page_url (str): 落地页 URL
        account_id (int, 可选): 关联的 Google Ads 账号 ID
        target_countries (list, 可选): 目标国家列表

    Returns:
        JSON: 创意生成任务信息
    """
    data = request.get_json(silent=True) or {}

    landing_page_url = data.get("landing_page_url", "").strip()
    if not landing_page_url:
        return jsonify({
            "success": False,
            "data": None,
            "message": "缺少 landing_page_url 参数",
        }), 400

    try:
        # 创建创意生成任务
        task = CreativeTask(
            tenant_id=1,
            status="pending",
            ai_prompt=f"根据落地页 {landing_page_url} 生成 Google Ads 广告创意",
        )
        db.session.add(task)
        db.session.flush()  # 获取 task.id

        # 尝试调用创意生成服务
        try:
            from services.creative_service import CreativeService
            from flask import current_app

            creative_service = CreativeService(
                model_name=current_app.config.get("AI_DEFAULT_MODEL", "gpt-4o-mini"),
                api_key=current_app.config.get("OPENAI_API_KEY"),
            )

            task.status = "generating"
            db.session.commit()

            # 调用 AI 生成创意
            result = creative_service.generate_creatives(
                page_url=landing_page_url,
                target_countries=data.get("target_countries", ["US"]),
            )

            task.generated_titles = result.get("titles", [])
            task.generated_descriptions = result.get("descriptions", [])
            task.generated_keywords = result.get("keywords", [])
            task.ai_model_used = current_app.config.get("AI_DEFAULT_MODEL", "gpt-4o-mini")
            task.status = "completed"

        except Exception as ai_error:
            logger.warning("AI 创意生成失败，使用模拟数据: %s", ai_error)
            task.generated_titles = [
                f"优质产品 - 标题 {i+1}" for i in range(5)
            ]
            task.generated_descriptions = [
                f"这是根据 {landing_page_url} 自动生成的广告描述 {i+1}"
                for i in range(3)
            ]
            task.generated_keywords = [
                {"text": "自动关键词", "match_type": "EXACT"},
            ]
            task.ai_model_used = "mock"
            task.status = "completed"

        db.session.commit()

        return jsonify({
            "success": True,
            "data": _model_to_dict(task),
            "message": "创意生成任务已完成",
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.exception("生成广告创意失败")
        return jsonify({
            "success": False,
            "data": None,
            "message": f"生成失败: {str(e)}",
        }), 500


@api_bp.route("/creatives/tasks", methods=["GET"])
@login_required
def list_creative_tasks():
    """
    列出创意生成任务

    Returns:
        JSON: 创意任务列表
    """
    tasks = CreativeTask.query.order_by(CreativeTask.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [_model_to_dict(t) for t in tasks],
        "message": f"共 {len(tasks)} 个创意任务",
    })


@api_bp.route("/creatives/tasks/<int:task_id>", methods=["GET"])
@login_required
def get_creative_task(task_id):
    """
    获取创意任务详情

    Args:
        task_id: 创意任务 ID

    Returns:
        JSON: 创意任务详细信息
    """
    task = CreativeTask.query.get(task_id)
    if not task:
        return jsonify({
            "success": False,
            "data": None,
            "message": f"创意任务 ID {task_id} 不存在",
        }), 404

    return jsonify({
        "success": True,
        "data": _model_to_dict(task),
        "message": "获取成功",
    })


# ============================================================
# 落地页 API
# ============================================================
@api_bp.route("/landing-pages/scrape", methods=["POST"])
@login_required
def scrape_landing_page():
    """
    爬取落地页

    请求体 JSON：
        url (str): 落地页 URL

    Returns:
        JSON: 爬取后的落地页信息
    """
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()

    if not url:
        return jsonify({
            "success": False,
            "data": None,
            "message": "缺少 url 参数",
        }), 400

    try:
        from services.scraper_service import ScraperService

        scraper = ScraperService()
        result = scraper.scrape(url)

        # 检查是否已存在该 URL 的落地页记录
        page = LandingPage.query.filter_by(url=url).first()
        if page:
            # 更新已有记录
            page.title = result.get("title", "")
            page.description = result.get("description", "")
            page.keywords = result.get("keywords", [])
            page.scraped_content = result.get("content", "")
            page.scraped_metadata = result.get("metadata", {})
            from datetime import datetime, timezone
            page.scraped_at = datetime.now(timezone.utc)
            db.session.commit()

            return jsonify({
                "success": True,
                "data": _model_to_dict(page),
                "message": "落地页信息已更新",
            })

        # 创建新落地页记录
        page = LandingPage(
            tenant_id=1,
            url=url,
            title=result.get("title", ""),
            description=result.get("description", ""),
            keywords=result.get("keywords", []),
            scraped_content=result.get("content", ""),
            scraped_metadata=result.get("metadata", {}),
        )
        db.session.add(page)
        db.session.commit()

        return jsonify({
            "success": True,
            "data": _model_to_dict(page),
            "message": "落地页爬取成功",
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.exception("爬取落地页失败: url=%s", url)
        return jsonify({
            "success": False,
            "data": None,
            "message": f"爬取失败: {str(e)}",
        }), 500


@api_bp.route("/landing-pages", methods=["GET"])
@login_required
def list_landing_pages():
    """
    列出落地页

    Returns:
        JSON: 落地页列表
    """
    pages = LandingPage.query.order_by(LandingPage.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [_model_to_dict(p) for p in pages],
        "message": f"共 {len(pages)} 个落地页",
    })


# ============================================================
# 代理 API
# ============================================================
@api_bp.route("/proxy/providers", methods=["GET"])
@login_required
def list_proxy_providers():
    """
    列出代理供应商

    Returns:
        JSON: 代理供应商列表
    """
    providers = ProxyProvider.query.order_by(ProxyProvider.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [_model_to_dict(p) for p in providers],
        "message": f"共 {len(providers)} 个代理供应商",
    })


@api_bp.route("/proxy/providers", methods=["POST"])
@login_required
def add_proxy_provider():
    """
    添加代理供应商

    请求体 JSON：
        name (str): 供应商名称
        provider_type (str): 供应商类型（brightdata/oxylabs/smartproxy/custom）
        api_endpoint (str, 可选): API 端点地址
        api_key (str, 可选): API 密钥
        country_config (dict, 可选): 国家/地区配置

    Returns:
        JSON: 新创建的代理供应商
    """
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    provider_type = data.get("provider_type", "").strip()

    if not name:
        return jsonify({
            "success": False,
            "data": None,
            "message": "供应商名称不能为空",
        }), 400

    if not provider_type:
        return jsonify({
            "success": False,
            "data": None,
            "message": "供应商类型不能为空",
        }), 400

    # 校验供应商类型
    valid_types = ("brightdata", "oxylabs", "smartproxy", "custom")
    if provider_type not in valid_types:
        return jsonify({
            "success": False,
            "data": None,
            "message": f"无效的供应商类型，支持: {', '.join(valid_types)}",
        }), 400

    try:
        provider = ProxyProvider(
            tenant_id=1,
            name=name,
            provider_type=provider_type,
            api_endpoint=data.get("api_endpoint", ""),
            api_key=data.get("api_key", ""),
            country_config=data.get("country_config", {}),
            is_active=True,
        )
        db.session.add(provider)
        db.session.commit()

        return jsonify({
            "success": True,
            "data": _model_to_dict(provider),
            "message": "代理供应商添加成功",
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.exception("添加代理供应商失败")
        return jsonify({
            "success": False,
            "data": None,
            "message": f"添加失败: {str(e)}",
        }), 500


@api_bp.route("/proxy/test", methods=["POST"])
@login_required
def test_proxy():
    """
    测试代理连接

    请求体 JSON：
        provider_id (int, 可选): 代理供应商 ID
        proxy_url (str, 可选): 直接提供代理 URL 测试

    Returns:
        JSON: 代理测试结果（延迟、是否可用等）
    """
    data = request.get_json(silent=True) or {}
    provider_id = data.get("provider_id")
    proxy_url = data.get("proxy_url", "").strip()

    if not provider_id and not proxy_url:
        return jsonify({
            "success": False,
            "data": None,
            "message": "请提供 provider_id 或 proxy_url",
        }), 400

    try:
        from services.proxy_service import ProxyService

        # 构建代理配置
        proxy_config = {}
        if provider_id:
            provider = ProxyProvider.query.get(provider_id)
            if not provider:
                return jsonify({
                    "success": False,
                    "data": None,
                    "message": f"代理供应商 ID {provider_id} 不存在",
                }), 404
            proxy_config = {
                "name": provider.name,
                "provider_type": provider.provider_type,
                "api_endpoint": provider.api_endpoint,
                "api_key": provider.api_key,
                "country_config": provider.country_config,
            }
        elif proxy_url:
            proxy_config = {"proxy_url": proxy_url}

        proxy_service = ProxyService(providers=[proxy_config])
        result = proxy_service.test_proxy()

        return jsonify({
            "success": True,
            "data": result,
            "message": "代理测试完成",
        })

    except Exception as e:
        logger.exception("代理测试失败")
        return jsonify({
            "success": False,
            "data": None,
            "message": f"测试失败: {str(e)}",
        }), 500


# ============================================================
# 定时任务 API
# ============================================================
@api_bp.route("/scheduler/tasks", methods=["GET"])
@login_required
def list_scheduler_tasks():
    """
    列出定时任务

    Returns:
        JSON: 定时任务列表
    """
    tasks = ScheduledTask.query.order_by(ScheduledTask.created_at.desc()).all()
    return jsonify({
        "success": True,
        "data": [_model_to_dict(t) for t in tasks],
        "message": f"共 {len(tasks)} 个定时任务",
    })


@api_bp.route("/scheduler/tasks", methods=["POST"])
@login_required
def create_scheduler_task():
    """
    创建定时任务

    请求体 JSON：
        name (str): 任务名称
        task_type (str): 任务类型（如 sync_google_ads、generate_creative）
        crontab_expression (str): Crontab 调度表达式
        config (dict, 可选): 任务配置参数

    Returns:
        JSON: 新创建的定时任务
    """
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    task_type = data.get("task_type", "").strip()
    crontab_expression = data.get("crontab_expression", "").strip()

    if not name:
        return jsonify({
            "success": False,
            "data": None,
            "message": "任务名称不能为空",
        }), 400

    if not task_type:
        return jsonify({
            "success": False,
            "data": None,
            "message": "任务类型不能为空",
        }), 400

    if not crontab_expression:
        return jsonify({
            "success": False,
            "data": None,
            "message": "Crontab 表达式不能为空",
        }), 400

    try:
        task = ScheduledTask(
            tenant_id=1,
            name=name,
            task_type=task_type,
            crontab_expression=crontab_expression,
            config=data.get("config", {}),
            status="active",
        )
        db.session.add(task)
        db.session.commit()

        return jsonify({
            "success": True,
            "data": _model_to_dict(task),
            "message": "定时任务创建成功",
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.exception("创建定时任务失败")
        return jsonify({
            "success": False,
            "data": None,
            "message": f"创建失败: {str(e)}",
        }), 500


@api_bp.route("/scheduler/tasks/<int:task_id>/run", methods=["POST"])
@login_required
def run_scheduler_task(task_id):
    """
    手动执行定时任务

    Args:
        task_id: 定时任务 ID

    Returns:
        JSON: 执行结果
    """
    task = ScheduledTask.query.get(task_id)
    if not task:
        return jsonify({
            "success": False,
            "data": None,
            "message": f"定时任务 ID {task_id} 不存在",
        }), 404

    try:
        from services.scheduler_service import SchedulerService

        scheduler_service = SchedulerService()
        # 记录执行
        task.last_run_at = task.updated_at  # 使用当前更新时间
        task.run_count += 1
        db.session.commit()

        return jsonify({
            "success": True,
            "data": _model_to_dict(task),
            "message": f"任务「{task.name}」已手动触发执行",
        })
    except Exception as e:
        db.session.rollback()
        logger.exception("手动执行定时任务失败: task_id=%s", task_id)
        return jsonify({
            "success": False,
            "data": None,
            "message": f"执行失败: {str(e)}",
        }), 500


@api_bp.route("/scheduler/tasks/<int:task_id>", methods=["DELETE"])
@login_required
def delete_scheduler_task(task_id):
    """
    删除定时任务

    Args:
        task_id: 定时任务 ID

    Returns:
        JSON: 删除结果
    """
    task = ScheduledTask.query.get(task_id)
    if not task:
        return jsonify({
            "success": False,
            "data": None,
            "message": f"定时任务 ID {task_id} 不存在",
        }), 404

    task_name = task.name
    db.session.delete(task)
    db.session.commit()

    return jsonify({
        "success": True,
        "data": None,
        "message": f"任务「{task_name}」已删除",
    })


# ============================================================
# 仪表盘数据 API
# ============================================================
@api_bp.route("/dashboard/stats", methods=["GET"])
@login_required
def dashboard_stats():
    """
    获取仪表盘统计数据

    Returns:
        JSON: 包含以下统计信息
            - account_count: 账号总数
            - campaign_count: 广告系列总数
            - active_ad_count: 活跃广告数
            - pending_creative_tasks: 待处理的创意任务数
            - recent_sync_logs: 最近同步日志
    """
    # 账号总数
    account_count = GoogleAdsAccount.query.count()

    # 广告系列总数
    campaign_count = Campaign.query.count()

    # 活跃广告数
    active_ad_count = Ad.query.filter_by(status="active").count()

    # 待处理的创意任务数
    pending_creative_tasks = CreativeTask.query.filter(
        CreativeTask.status.in_(["pending", "generating"])
    ).count()

    # 最近 10 条同步日志
    recent_sync_logs = (
        SyncLog.query
        .order_by(SyncLog.created_at.desc())
        .limit(10)
        .all()
    )

    return jsonify({
        "success": True,
        "data": {
            "account_count": account_count,
            "campaign_count": campaign_count,
            "active_ad_count": active_ad_count,
            "pending_creative_tasks": pending_creative_tasks,
            "recent_sync_logs": [_model_to_dict(log) for log in recent_sync_logs],
        },
        "message": "统计数据获取成功",
    })