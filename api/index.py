# api/index.py

import json
import re
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from lark_oapi import Config, Client
from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

# === 1. 配置 (已填入你的信息) ===
APP_ID = "cli_a9465268b839dcc2"
APP_SECRET = "zLSzHVEWSaTKI6YNOdQfAeRflMAKKpM1"

# 初始化客户端
config = Config.new_internal_app_config(APP_ID, APP_SECRET)
client = Client.new_internal_app_client(config)

# === 2. 允许的分类 (白名单) ===
ALLOWED_CATEGORIES = ["技术", "管理", "案例", "流程", "制度"]

def validate_filename(name):
    """校验文件名逻辑"""
    if not name.startswith("【"):
        return "格式错误！必须以【分类】开头。"

    if not re.search(r'_\d{4}_', name):
        return "格式错误！必须包含_年份_作者。"

    category_match = re.search(r'【(.*?)】', name)
    if category_match:
        category = category_match.group(1)
        if category not in ALLOWED_CATEGORIES:
            return f"分类错误！必须是 {ALLOWED_CATEGORIES} 之一。"

    return "valid"

# === 3. Vercel 强制要求的入口类 ===
# 注意：类名必须是 'handler' (小写)
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # 1. 读取请求
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            event = json.loads(post_data.decode('utf-8'))

            # 2. 处理 URL 验证 (飞书第一次回调会发这个)
            if event.get("type") == "url_verification":
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"challenge": event.get("challenge")}).encode('utf-8'))
                return

            # 3. 处理消息事件
            header = event.get("header", {})
            if header.get("event_type") == "im.message.receive_v1":
                data = event.get("event", {}).get("message", {})
                sender = event.get("event", {}).get("sender", {})

                # 解析消息内容
                content = json.loads(data.get("content", "{}"))
                file_key = content.get("file_key", "")
                file_name = content.get("file_name", "")
                chat_id = data.get("chat_id", "")
                user_id = sender.get("sender_id", {}).get("user_id", "")

                reply_text = ""

                # 校验逻辑
                if not file_name.lower().endswith('.pdf'):
                    reply_text = "❌ 文档需要pdf格式。命名规范：【分类】+文档名称+文档编写年份+文档作者。"
                else:
                    name_without_ext = re.sub(r'\.pdf$', '', file_name, flags=re.IGNORECASE)
                    result = validate_filename(name_without_ext)
                    if result != "valid":
                        reply_text = f"❌ {result}"

                # 发送回复 (如果有)
                if reply_text and chat_id:
                    req = CreateMessageRequest.builder() \
                        .receive_id_type("chat_id") \
                        .request_body(CreateMessageRequestBody.builder()
                            .receive_id(chat_id)
                            .content(json.dumps({"text": reply_text}))
                            .msg_type("text")
                            .build()) \
                        .build()

                    # 注意：这里使用同步阻塞调用，Vercel 环境下通常可用
                    resp = client.im.v1.message.create(req)
                    if resp.success():
                        print("回复成功")
                    else:
                        print("回复失败:", resp.code, resp.msg)

            # 4. 返回 HTTP 响应
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))

        except Exception as e:
            print("Error:", e)
            self.send_response(200) # 即使内部报错也返回200，防止飞书重试风暴
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error"}).encode('utf-8'))

    def do_GET(self):
        # Vercel 健康检查用
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot Running")