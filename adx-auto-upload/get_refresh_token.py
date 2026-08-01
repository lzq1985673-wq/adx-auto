#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Ads API — Refresh Token 生成工具

使用方法：
1. pip install google-auth-oauthlib
2. 把第3步获取的 client secrets JSON 文件路径传入
3. 运行脚本，浏览器会自动打开授权页面
4. 授权后，终端会输出 Refresh Token

命令：
    python get_refresh_token.py --client_secrets_path /path/to/client_secret_xxx.json
"""

import argparse
import hashlib
import os
import re
import socket
import sys
from urllib.parse import unquote

try:
    from google_auth_oauthlib.flow import Flow
except ImportError:
    print("请先安装依赖：pip install google-auth-oauthlib")
    sys.exit(1)

_SCOPE = "https://www.googleapis.com/auth/adwords"
_SERVER = "127.0.0.1"
_PORT = 8080
_REDIRECT_URI = f"http://{_SERVER}:{_PORT}"


def main(client_secrets_path: str, scopes: list) -> None:
    flow = Flow.from_client_secrets_file(client_secrets_path, scopes=scopes)
    flow.redirect_uri = _REDIRECT_URI

    passthrough_val = hashlib.sha256(os.urandom(1024)).hexdigest()

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        state=passthrough_val,
        prompt="consent",
        include_granted_scopes="true",
    )

    print("\n" + "=" * 60)
    print("  请在浏览器中打开以下链接进行授权：")
    print("=" * 60)
    print(authorization_url)
    print(f"\n等待授权回调: {_REDIRECT_URI}")
    print("=" * 60 + "\n")

    code = unquote(get_authorization_code(passthrough_val))

    flow.fetch_token(code=code)
    refresh_token = flow.credentials.refresh_token

    print("\n" + "=" * 60)
    print("  ✅ 授权成功！")
    print("=" * 60)
    print(f"\n  你的 Refresh Token:\n  {refresh_token}\n")
    print("  请将此 Token 保存好，填入 ADX-Auto 系统设置页面。")
    print("=" * 60 + "\n")


def get_authorization_code(passthrough_val: str) -> str:
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((_SERVER, _PORT))
    sock.listen(1)
    connection, address = sock.accept()
    data = connection.recv(1024)
    params = parse_raw_query_params(data)

    try:
        if not params.get("code"):
            error = params.get("error", "unknown")
            raise ValueError(f"获取授权码失败。错误: {error}")
        elif params.get("state") != passthrough_val:
            raise ValueError("State token 不匹配")
        else:
            message = "授权码获取成功！"
    except ValueError as error:
        print(error)
        sys.exit(1)
    finally:
        response = (
            "HTTP/1.1 200 OK\n"
            "Content-Type: text/html; charset=utf-8\n\n"
            f"<b>{message}</b>"
            "<p>请返回终端查看 Refresh Token。</p>\n"
        )
        connection.sendall(response.encode())
        connection.close()

    return params.get("code")


def parse_raw_query_params(data: bytes) -> dict:
    decoded = data.decode("utf-8")
    match = re.search(r"GET\s\/\?(.*) ", decoded)
    params = match.group(1)
    pairs = [pair.split("=") for pair in params.split("&")]
    return {key: val for key, val in pairs}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成 Google Ads API Refresh Token")
    parser.add_argument(
        "-c", "--client_secrets_path",
        required=True,
        help="client_secret JSON 文件路径（从 Google Cloud Console 下载）"
    )
    args = parser.parse_args()
    main(args.client_secrets_path, [_SCOPE])
