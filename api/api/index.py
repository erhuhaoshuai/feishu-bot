from http.server import BaseHTTPRequestHandler
import json

# 注意：类名必须是 handler，且首字母小写
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. 准备回复数据
        message = {
            "status": "success",
            "message": "机器人已激活！代码结构正确。"
        }
        
        # 2. 发送 HTTP 响应头
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        # 3. 发送响应体
        self.wfile.write(json.dumps(message).encode('utf-8'))

    # Vercel 有时会发 GET 请求来健康检查，我们也简单响应一下
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is running")