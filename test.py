import asyncio
import websockets
import json
import requests

# 获取可用的 DevTools 页面
resp = requests.get('http://127.0.0.1:9223/json')
pages = resp.json()

# 新建tab（target）
def create_new_tab():
    url = 'http://127.0.0.1:9223/json/new?url=https://grok.com'
    try:
        ws_url = requests.put(url).json()['webSocketDebuggerUrl']
    except Exception as e:
        print(f"[WARN] 新建tab失败，原因: {e}. 尝试复用已有tab。")
        ws_url = requests.get('http://127.0.0.1:9223/json').json()[0]['webSocketDebuggerUrl']
    # 必须补端口号，否则CDP默认返回无端口的ws url
    if ws_url.startswith('ws://127.0.0.1/devtools'):
        ws_url = ws_url.replace('ws://127.0.0.1/', 'ws://127.0.0.1:9223/')
    return ws_url
    
async def main():
    async with websockets.connect(create_new_tab()) as ws:
        msg_id = 1
        # 启用 Page 域
        await ws.send(json.dumps({"id": msg_id, "method": "Page.enable"}))
        await ws.recv()
        msg_id += 1
        # 导航到grok.com
        await ws.send(json.dumps({
            "id": msg_id,
            "method": "Page.navigate",
            "params": {"url": "https://grok.com"}
        }))
        msg_id += 1
        # 等待 Page.loadEventFired 事件
        while True:
            resp = await ws.recv()
            data = json.loads(resp) 
            if data.get('method') == 'Page.loadEventFired':
                break
        # 获取页面HTML
        await ws.send(json.dumps({
            "id": msg_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": "document.documentElement.outerHTML"
            }
        }))
        while True:
            resp = await ws.recv()
            data = json.loads(resp)
            if data.get('id') == msg_id:
                html = data['result']['result']['value']
                print(html)
                break

if __name__ == "__main__":
    asyncio.run(main())
