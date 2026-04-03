import json
import re
from lark_oapi.api.im.v1 import *
from lark_oapi.api.core import *
from lark_oapi import Config, Client

# --- 配置 ---
# 在 Vercel 后台设置环境变量，或者在这里写死（不推荐）
APP_ID = "cli_a9465268b839dcc2"
APP_SECRET = "zLSzHVEWSaTKI6YNOdQfAeRflMAKKpM1"

ALLOWED_CATEGORIES = ["技术", "管理", "案例"] # 可以随时修改

# Vercel 入口函数
def handler(environ, start_response):
    try:
        # 1. 读取请求体
        request_body = environ['wsgi.input'].read(int(environ['CONTENT_LENGTH'])).decode('utf-8')
        event = json.loads(request_body)
        
        # 2. 处理逻辑
        message = event.get("event", {}).get("message", {})
        content = json.loads(message.get("content", "{}"))
        file_name = content.get("file_name", "")
        chat_id = message.get("chat_id", "")

        reply_text = ""
        
        # --- 核心校验逻辑 (保持不变) ---
        if not file_name.lower().endswith('.pdf'):
            reply_text = "文档需要pdf格式。格式：【分类】文档_年份_作者。例：【技术】方案_2026_张三"
        else:
            name_without_ext = file_name[:-4]
            # 简单校验：必须包含 【 和 _年份_作者
            if not (re.search(r'【.*】', name_without_ext) and re.search(r'_\d{4}_', name_without_ext)):
                reply_text = "格式错误！请按：【分类】文档名称_年份_作者。示例：【技术】XX方案_2026_张三"
            else:
                # 进一步检查分类
                cat_match = re.search(r'【(.*?)】', name_without_ext)
                if cat_match and cat_match.group(1) not in ALLOWED_CATEGORIES:
                    reply_text = f"分类错误！必须是 {ALLOWED_CATEGORIES} 之一。"

        # --- 发送回复 ---
        if reply_text:
            client = Client.builder().app_id(APP_ID).app_secret(APP_SECRET).build()
            req = CreateMessageRequest.builder() \
                .request_body(CreateMessageRequestBody.builder() \
                    .receive_id_type('chat_id') \
                    .msg_type('text') \
                    .content(json.dumps({"text": reply_text})) \
                    .build()) \
                .path_params({'chat_id': chat_id}) \
                .build()
            client.im.v1.message.create(req)

        # --- 返回响应 ---
        start_response('200 OK', [('Content-Type', 'application/json')])
        return [json.dumps({"msg": "ok"}).encode('utf-8')]

    except Exception as e:
        print("Error:", e)
        start_response('200 OK', [('Content-Type', 'application/json')])
        return [json.dumps({"msg": "error"}).encode('utf-8')]