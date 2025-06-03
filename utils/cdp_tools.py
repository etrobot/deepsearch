import requests
import logging

resp = requests.get('http://127.0.0.1:9223/json')
pages = resp.json()

# 新建tab（target）
def create_new_tab():
    url = 'http://127.0.0.1:9223/json/new?url=https://grok.com'
    resp = requests.put(url)
    ws_url = resp.json()['webSocketDebuggerUrl']
    if ws_url.startswith('ws://127.0.0.1/devtools'):
        ws_url = ws_url.replace('ws://127.0.0.1/', 'ws://127.0.0.1:9223/')
    logging.info(f'新建tab ws_url: {ws_url}')
    return ws_url

def close_tab_by_ws_url(ws_url):
    # ws_url: ws://127.0.0.1:9223/devtools/page/xxx
    page_id = ws_url.split('/')[-1]
    close_url = f'http://127.0.0.1:9223/json/close/{page_id}'
    logging.info(f'关闭tab: {close_url}')
    resp = requests.get(close_url)
    logging.info(f'关闭tab响应: {resp.text}')
