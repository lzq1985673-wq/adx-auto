# ADX-Auto 云端部署指南（Render）

本指南帮助你将 ADX-Auto 网站部署到 **Render** 免费云平台，获得一个可分享的公网链接。

> **注意**：Render 免费版在连续 15 分钟无人访问后会进入休眠，下次访问需要约 30 秒唤醒。如需保持 24 小时在线，请升级到付费版。

---

## 一、准备工作

### 1. 注册 Render 账号

1. 打开 [https://render.com](https://render.com)
2. 点击 **Get Started for Free**
3. 用 **GitHub 账号** 登录（推荐，后续部署最方便）

---

## 二、部署方式（推荐：GitHub 部署）

### 步骤 1：将代码上传到 GitHub

1. 访问 [https://github.com/new](https://github.com/new)
2. 创建一个新的仓库，例如 `adx-auto`
3. 将本项目文件夹（`adx-auto` 目录下的所有文件）上传到该仓库

> 如果你不会用 Git，可以直接在 GitHub 网页上拖拽上传文件。

### 步骤 2：在 Render 上创建服务

1. 登录 [Render Dashboard](https://dashboard.render.com)
2. 点击 **New +** → **Blueprint**
3. 选择你刚才创建的 GitHub 仓库
4. Render 会自动识别 `render.yaml` 文件，按配置一键部署
5. 点击 **Apply** 开始部署

### 步骤 3：等待部署完成

- 部署过程约 2-5 分钟
- 完成后，Render 会给你一个链接，例如：
  ```
  https://adx-auto.onrender.com
  ```
- 把这个链接发给别人就能直接访问

---

## 三、部署方式（备用：手动创建）

如果你不想用 GitHub，也可以手动上传：

1. 登录 [Render Dashboard](https://dashboard.render.com)
2. 点击 **New +** → **Web Service**
3. 选择 **Upload Code**（上传代码）
4. 上传 `adx-auto` 文件夹的 ZIP 压缩包
5. 按以下配置填写：

| 配置项 | 值 |
|--------|-----|
| Name | adx-auto |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2` |

6. 在 **Environment** 中添加：
   - `FLASK_ENV` = `production`
   - `SECRET_KEY` = （随便输入一串随机字符，用于加密会话）
   - `SQLALCHEMY_DATABASE_URI` = `sqlite:////var/data/adx_auto.db`

7. 在 **Disks** 中添加：
   - Name: `adx-data`
   - Mount Path: `/var/data`
   - Size: 1 GB

8. 点击 **Create Web Service**

---

## 四、首次访问

部署完成后，打开你的 Render 链接：

- 首次访问时，系统会自动初始化数据库
- 默认管理员账号：
  - **用户名**：`admin`
  - **密码**：`admin123`

> **安全建议**：登录后立即到 **设置** 页面修改默认密码。

---

## 五、常见问题

### Q: 网站打不开，显示 "Service Unavailable"
A: Render 免费版休眠了，等待 30 秒左右自动唤醒。或升级到付费版避免休眠。

### Q: 数据库数据丢失了
A: 检查是否正确配置了 Disk（挂载路径 `/var/data`）。如果没有配置 Disk，每次部署后数据会丢失。

### Q: 如何更新网站内容
A: 如果使用 GitHub 部署，只需推送代码到 GitHub，Render 会自动重新部署。

### Q: 如何绑定自己的域名
A: 在 Render Dashboard → 你的服务 → Settings → Custom Domains 中添加。

---

## 六、项目文件说明

| 文件 | 用途 |
|------|------|
| `render.yaml` | Render 自动部署配置文件 |
| `wsgi.py` | 生产环境 WSGI 入口 |
| `requirements.txt` | Python 依赖清单（已包含 gunicorn） |
| `app.py` | Flask 主程序 |
| `config.py` | 配置模块（支持环境变量） |

---

**部署完成后，你就能把 `https://你的链接.onrender.com` 发给任何人访问了！**
