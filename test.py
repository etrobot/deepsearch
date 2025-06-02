import asyncio
import websockets
import json
import requests
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# 获取可用的 DevTools 页面
def get_pages():
    resp = requests.get('http://127.0.0.1:9223/json')
    return resp.json()

def create_new_tab():
    url = 'http://127.0.0.1:9223/json/new?url=https://grok.com'
    try:
        ws_url = requests.put(url).json()['webSocketDebuggerUrl']
    except Exception as e:
        print(f"[WARN] 新建tab失败，原因: {e}. 尝试复用已有tab。")
        ws_url = get_pages()[0]['webSocketDebuggerUrl']
    if ws_url.startswith('ws://127.0.0.1/devtools'):
        ws_url = ws_url.replace('ws://127.0.0.1/', 'ws://127.0.0.1:9223/')
    return ws_url

async def ask_grok(question):
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
        # 在页面上下 JS，执行 fetch 发送问题
        js_code = f'''
        (async () => {{
            const resp = await fetch('https://grok.com/rest/app-chat/conversations/new', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Accept': '*/*',
                    'Origin': 'https://grok.com',
                    'Referer': 'https://grok.com/',
                }},
                body: JSON.stringify({{
                    message: {json.dumps(question)},
                    forceConcise: true,
                    disableTextFollowUps: true
                }}),
                credentials: 'include'
            }});
            return await resp.text();
        }})()
        '''
        msg_id += 1
        await ws.send(json.dumps({
            "id": msg_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": js_code,
                "awaitPromise": True
            }
        }))
        while True:
            resp = await ws.recv()
            data = json.loads(resp)
            if data.get('id') == msg_id:
                result = data['result']['result']['value']
                logging.info(f"fetch返回: {result[:200]}..." if len(result) > 200 else f"fetch返回: {result}")
                # 逐行找 modelResponse.message
                answer = None
                for line in result.splitlines():
                    try:
                        obj = json.loads(line)
                        model_resp = obj.get('result', {}).get('response', {}).get('modelResponse', {})
                        if isinstance(model_resp, dict) and 'message' in model_resp:
                            answer = model_resp['message']
                            break
                    except Exception:
                        continue
                if answer:
                    print(f"Grok 回复: {answer}")
                else:
                    print("[未找到模型回复]")
                break

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        question = sys.argv[1]
    else:
        question = input("请输入你的问题: ")
    asyncio.run(ask_grok(question))
