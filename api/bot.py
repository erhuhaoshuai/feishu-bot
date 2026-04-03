# api/bot.py

import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
from lark_oapi.api.core import Config, Client

# === 1. 配置区 (请替换为你自己的信息) ===
APP_ID = "cli_a9465268b839dcc2"  # 替换为你的飞书机器人App ID
APP_SECRET = "zLSzHVEWSaTKI6YNOdQfAeRflMAKKpM1"  # 替换为你的飞书机器人App Secret

# 允许的分类白名单
ALLOWED_CATEGORIES = ["技术", "管理", "案例", "流程", "制度"]

# === 2. 核心校验逻辑 (保持不变) ===
def validate_filename(name):
    """校验文件名是否符合规范"""
    # 必须以 【 开头
    if not name.startswith("【"):
        return "格式错误！必须以【分类】开头。示例：【技术】方案_2026_张三.pdf"

    # 必须包含 _年份_作者
    if not re.search(r'_\d{4}_', name):
        return "格式错误！必须包含_年份_作者。示例：【技术】方案_2026_张三.pdf"

    # 检查分类是否在白名单内
    category_match = re.search(r'【(.*?)】', name)
    if category_match:
        category = category_match.group(1)
        if category not in ALLOWED_CATEGORIES:
            return f"分类错误！必须是 {ALLOWED_CATEGORIES} 之一。"

    return "valid"

# === 3. Vercel 入口处理器 (关键修改点) ===
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """处理飞书发来的 POST 请求"""
        try:
            # 1. 读取请求体长度并解析 JSON
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            event = json.loads(post_data.decode('utf-8'))
            
            print("收到飞书事件:", json.dumps(event, ensure_ascii=False)[:100]) # 打印前100字符日志

            # 2. 提取消息信息
            message = event.get("event", {}).get("message", {})
            sender_id = message.get("sender", {}).get("sender_id", {}).get("user_id", "")
            chat_id = message.get("chat_id", "")
            
            content = json.loads(message.get("content", "{}"))
            file_key = content.get("file_key", "")
            file_name = content.get("file_name", "")

            # 3. 核心校验逻辑
            reply_text = ""
            
            # 检查是否为 PDF
            if not file_name.lower().endswith('.pdf'):
                reply_text = "❌ 文档需要pdf格式。命名规范：【分类】+文档名称+文档编写年份+文档作者。示例：【技术】方案_2026_张三.pdf"
            
            # 检查命名规范
            else:
                name_without_ext = file_name[:-4] # 去掉.pdf后缀
                validation_result = validate_filename(name_without_ext)
                if validation_result != "valid":
                    reply_text = f"❌ {validation_result}"

            # 4. 发送回复 (如果需要回复)
            if reply_text and chat_id:
                # 初始化飞书客户端
                client = Client.builder() \
                    .app_id(APP_ID) \
                    .app_secret(APP_SECRET) \
                    .build()
                
                # 构建回复消息
                req = CreateMessageRequest.builder() \
                    .request_body(CreateMessageRequestBody.builder() \
                        .receive_id_type('chat_id') \
                        .msg_type('text') \
                        .content(json.dumps({"text": reply_text})) \
                        .build()) \
                    .path_params({'chat_id': chat_id}) \
                    .build()
                
                # 发送
                resp = client.im.v1.message.create(req)
                if resp.success():
                    print("回复发送成功")
                else:
                    print("回复发送失败:", resp.code, resp.msg)

            # 5. 返回 HTTP 响应给飞书 (必须返回 200，否则飞书会认为发送失败并重试)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"msg": "success"}).encode('utf-8'))

        except Exception as e:
            print("处理错误:", e)
            self.send_response(200) # 即使内部出错，也返回200防止飞书无限重试
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"msg": "error"}).encode('utf-8'))

# 如果你是本地调试，可以保留下面这行；如果是部署到 Vercel，这行可以注释掉。
# if __name__ == "__main__":
#     HTTPServer(('', 3000), handler).serve_forever()
