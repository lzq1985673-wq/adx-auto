# -*- coding: utf-8 -*-
"""
页面路由蓝图模块

本模块定义 ADX Auto 平台的所有页面路由，负责渲染 HTML 页面。
所有页面路由均需登录后才能访问（login 除外）。

路由列表：
- /                — 仪表盘首页
- /accounts        — 账号管理页
- /campaigns       — 广告系列页
- /creatives       — 广告创意管理页
- /landing-pages   — 落地页管理页
- /scheduler       — 定时任务页
- /settings        — 系统设置页
- /login           — 登录页（GET） / 登录处理（POST）
- /logout          — 登出
"""

from functools import wraps

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    session,
    flash,
)

from models import (
    db,
    User,
    GoogleAdsAccount,
    Campaign,
    Ad,
    CreativeTask,
    SyncLog,
)

# 创建页面路由蓝图
main_bp = Blueprint("main", __name__)


# ============================================================
# 登录验证装饰器
# ============================================================
def login_required(f):
    """
    登录验证装饰器

    检查 session 中是否存在 user_id，未登录时重定向到登录页。
    适用于除登录页以外的所有页面路由。

    用法：
        @main_bp.route("/dashboard")
        @login_required
        def dashboard():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("请先登录", "warning")
            return redirect(url_for("main.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================
# 登录 / 登出路由
# ============================================================
@main_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    登录页面和处理

    GET:  渲染登录页面
    POST: 处理登录表单，验证用户名和密码，成功后写入 session
    """
    # 已登录用户直接跳转首页
    if "user_id" in session:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # 查找用户
        user = User.query.filter_by(username=username).first()

        # 验证密码（使用 werkzeug 的 check_password_hash）
        if user and hasattr(user, "password_hash") and user.password_hash:
            from werkzeug.security import check_password_hash
            if check_password_hash(user.password_hash, password):
                session["user_id"] = user.id
                session["username"] = user.username
                session["role"] = user.role
                flash("登录成功", "success")

                # 跳转到之前访问的页面，或默认首页
                next_page = request.args.get("next")
                if next_page:
                    return redirect(next_page)
                return redirect(url_for("main.dashboard"))

        flash("用户名或密码错误", "danger")

    return render_template("login.html")


@main_bp.route("/logout")
def logout():
    """
    登出处理

    清除 session 中的用户信息，重定向到登录页。
    """
    session.clear()
    flash("已成功登出", "info")
    return redirect(url_for("main.login"))


# ============================================================
# 仪表盘首页
# ============================================================
@main_bp.route("/")
@login_required
def dashboard():
    """
    仪表盘首页

    展示系统概览数据：
    - 账户总数
    - 广告系列总数
    - 活跃广告数
    - 最近同步日志
    """
    # 统计数据
    total_accounts = GoogleAdsAccount.query.count()
    active_campaigns = Campaign.query.filter(Campaign.status.in_(["enabled", "active"])).count()
    active_ads = Ad.query.filter_by(status="active").count()
    today_creatives = CreativeTask.query.filter(
        CreativeTask.created_at >= db.func.current_date()
    ).count()

    stats = {
        "total_accounts": total_accounts,
        "active_campaigns": active_campaigns,
        "active_ads": active_ads,
        "today_creatives": today_creatives,
        "last_sync_status": "",
    }

    # 最近 10 条同步日志
    sync_logs = (
        SyncLog.query
        .order_by(SyncLog.created_at.desc())
        .limit(10)
        .all()
    )

    # 最近同步状态
    sync_status = ""
    if sync_logs:
        sync_status = sync_logs[0].status if hasattr(sync_logs[0], "status") else ""
        stats["last_sync_status"] = sync_status

    # 最近 10 条创意任务
    recent_tasks = (
        CreativeTask.query
        .order_by(CreativeTask.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "dashboard.html",
        stats=stats,
        sync_logs=sync_logs,
        recent_tasks=recent_tasks,
        sync_status=sync_status,
    )


# ============================================================
# 账号管理页
# ============================================================
@main_bp.route("/accounts")
@login_required
def accounts():
    """
    账号管理页

    列出所有 Google Ads 账号，支持查看账号详情和同步操作。
    """
    accounts = GoogleAdsAccount.query.order_by(GoogleAdsAccount.created_at.desc()).all()
    return render_template("accounts.html", accounts=accounts)


# ============================================================
# 广告系列页
# ============================================================
@main_bp.route("/campaigns")
@login_required
def campaigns():
    """
    广告系列管理页

    展示所有广告系列列表，可按账号筛选。
    """
    # 支持按账号 ID 和状态筛选
    account_id = request.args.get("account_id", type=int)
    selected_status = request.args.get("status", "")

    query = Campaign.query
    if account_id:
        query = query.filter_by(account_id=account_id)
    if selected_status:
        query = query.filter_by(status=selected_status)
    campaign_list = query.order_by(Campaign.created_at.desc()).all()

    # 获取所有账号（用于筛选下拉框）
    all_accounts = GoogleAdsAccount.query.all()

    return render_template(
        "campaigns.html",
        campaigns=campaign_list,
        accounts=all_accounts,
        selected_account=account_id,
        selected_status=selected_status,
    )


# ============================================================
# 广告创意管理页
# ============================================================
@main_bp.route("/creatives")
@login_required
def creatives():
    """
    广告创意管理页

    展示所有 AI 创意生成任务及其状态和结果。
    """
    tasks = (
        CreativeTask.query
        .order_by(CreativeTask.created_at.desc())
        .all()
    )

    # 获取所有账号（用于选择下拉框）
    all_accounts = GoogleAdsAccount.query.all()

    # 获取所有落地页（用于选择下拉框）
    from models import LandingPage
    landing_pages = LandingPage.query.all()

    # 常用国家列表（用于多选复选框）
    countries = [
        {"code": "US", "name": "美国"},
        {"code": "UK", "name": "英国"},
        {"code": "CA", "name": "加拿大"},
        {"code": "AU", "name": "澳大利亚"},
        {"code": "DE", "name": "德国"},
        {"code": "FR", "name": "法国"},
        {"code": "JP", "name": "日本"},
        {"code": "KR", "name": "韩国"},
        {"code": "BR", "name": "巴西"},
        {"code": "IN", "name": "印度"},
        {"code": "MX", "name": "墨西哥"},
        {"code": "IT", "name": "意大利"},
    ]

    return render_template(
        "creatives.html",
        tasks=tasks,
        accounts=all_accounts,
        landing_pages=landing_pages,
        countries=countries,
    )


# ============================================================
# 落地页管理页
# ============================================================
@main_bp.route("/landing-pages")
@login_required
def landing_pages():
    """
    落地页管理页

    展示所有已爬取和管理的落地页信息。
    """
    from models import LandingPage
    pages = LandingPage.query.order_by(LandingPage.created_at.desc()).all()
    return render_template("landing_pages.html", pages=pages)


# ============================================================
# 定时任务页
# ============================================================
@main_bp.route("/scheduler")
@login_required
def scheduler():
    """
    定时任务管理页

    展示所有定时调度任务，支持创建、暂停、手动执行和删除操作。
    """
    from models import ScheduledTask
    jobs = (
        ScheduledTask.query
        .order_by(ScheduledTask.created_at.desc())
        .all()
    )
    return render_template("scheduler.html", jobs=jobs)


# ============================================================
# 系统设置页
# ============================================================
@main_bp.route("/settings")
@login_required
def settings():
    """
    系统设置页

    管理系统配置，包括：
    - 代理（Proxy）供应商配置
    - AI 模型和参数配置
    """
    from models import ProxyProvider
    providers = ProxyProvider.query.all()

    # 从当前 app 配置中读取 AI 相关设置
    from flask import current_app
    ai_config = {
        "model": current_app.config.get("AI_DEFAULT_MODEL", "gpt-4o-mini"),
        "api_key": current_app.config.get("OPENAI_API_KEY", ""),
        "prompt_template": current_app.config.get("AI_PROMPT_TEMPLATE", ""),
    }

    # Google Ads 配置
    ads_config = {
        "developer_token": current_app.config.get("GOOGLE_ADS_DEVELOPER_TOKEN", ""),
        "client_id": current_app.config.get("GOOGLE_ADS_CLIENT_ID", ""),
        "client_secret": current_app.config.get("GOOGLE_ADS_CLIENT_SECRET", ""),
        "refresh_token": current_app.config.get("GOOGLE_ADS_REFRESH_TOKEN", ""),
    }

    return render_template(
        "settings.html",
        proxies=providers,
        ai_config=ai_config,
        ads_config=ads_config,
    )