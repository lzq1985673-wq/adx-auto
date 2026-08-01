"""
ADX-Auto 命令行入口
用法：
    python cli.py init          # 初始化数据库
    python cli.py run           # 启动 Web 服务
    python cli.py mock          # Mock 模式启动（无需任何第三方 API）
    python cli.py scrape <url>  # 爬取落地页
    python cli.py creative <url> # 生成广告创意
"""

import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cmd_init():
    """初始化数据库"""
    from app import create_app
    app = create_app()
    with app.app_context():
        from models import db
        db.create_all()
        # 创建默认管理员
        from app import _create_default_admin
        _create_default_admin(app)
        print("✓ 数据库初始化完成")
        print("✓ 默认管理员已创建 (admin / admin123)")


def cmd_run():
    """启动 Web 服务"""
    from app import create_app
    app = create_app()
    print("=" * 50)
    print("  ADX-Auto Google Ads 自动化管理系统")
    print("  http://127.0.0.1:5000")
    print("  默认账号: admin / admin123")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)


def cmd_scrape(url):
    """爬取落地页"""
    print(f"正在爬取: {url}")
    from services.scraper_service import ScraperService
    scraper = ScraperService()
    result = scraper.scrape(url)

    if "error" in result:
        print(f"✗ 爬取失败: {result['error']}")
        return

    print(f"\n✓ 爬取成功 (状态码: {result['status_code']})")
    print(f"  标题: {result['title']}")
    print(f"  描述: {result['meta_description']}")
    print(f"  H1标签: {result['h1_tags']}")
    print(f"  关键词: {result['keywords']}")

    keywords = scraper.extract_keywords(result)
    print(f"\n✓ 提取关键词 ({len(keywords)} 个):")
    for kw in keywords[:10]:
        print(f"  - {kw['word']} (分数: {kw['score']:.2f})")

    hints = scraper.extract_ad_copy_hints(result)
    print(f"\n✓ 广告文案线索:")
    print(f"  卖点: {hints['selling_points'][:3]}")
    print(f"  痛点: {hints['pain_points'][:3]}")


def cmd_creative(url):
    """生成广告创意"""
    print(f"正在为落地页生成创意: {url}")
    from services.scraper_service import ScraperService
    from services.creative_service import CreativeService

    # 先爬取
    scraper = ScraperService()
    scraped = scraper.scrape(url)
    if "error" in scraped:
        print(f"✗ 爬取失败: {scraped['error']}")
        return

    # 生成创意
    creative = CreativeService()
    result = creative.generate_creative(scraped, target_countries=["US"], language="en")

    print(f"\n✓ 生成完成!")
    print(f"\n--- 标题 ({len(result['titles'])} 个) ---")
    for i, t in enumerate(result["titles"][:5], 1):
        print(f"  {i}. {t}")

    print(f"\n--- 描述 ({len(result['descriptions'])} 个) ---")
    for i, d in enumerate(result["descriptions"], 1):
        print(f"  {i}. {d}")

    print(f"\n--- 关键词 ({len(result['keywords'])} 个) ---")
    for i, kw in enumerate(result["keywords"][:10], 1):
        print(f"  {i}. [{kw['match_type']}] {kw['text']}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    command = sys.argv[1]

    if command == "init":
        cmd_init()
    elif command == "run":
        cmd_run()
    elif command == "scrape" and len(sys.argv) >= 3:
        cmd_scrape(sys.argv[2])
    elif command == "creative" and len(sys.argv) >= 3:
        cmd_creative(sys.argv[2])
    else:
        print(f"未知命令: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
