import asyncio
import json
import logging
import websockets
from typing import Optional, Dict, Any
from .cdp_tools import create_new_tab, close_tab_by_ws_url
from .grok_utils import FIND_ELEMENT_JS

logger = logging.getLogger(__name__)

class GrokClient:
    def __init__(self):
        self.ws_url = None
        self.ws = None
        self.msg_id = 1

    async def __aenter__(self):
        self.ws_url = create_new_tab()
        self.ws = await websockets.connect(self.ws_url, max_size=None)
        await self._send_message("Page.enable")
        await self._send_message("Network.enable")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.ws:
            await self.ws.close()
        if self.ws_url:
            close_tab_by_ws_url(self.ws_url)
            logger.debug('已关闭tab')

    async def _send_message(self, method: str, params: Optional[Dict] = None) -> Dict:
        """发送消息到 Chrome DevTools Protocol"""
        msg = {"id": self.msg_id, "method": method}
        if params:
            msg["params"] = params
        
        await self.ws.send(json.dumps(msg))
        self.msg_id += 1
        
        while True:
            resp = await self.ws.recv()
            data = json.loads(resp)
            if data.get('id') == self.msg_id - 1:
                return data

    async def navigate(self, url: str):
        """导航到指定URL"""
        await self._send_message("Page.navigate", {"url": url})
        # 等待页面加载完成
        while True:
            resp = await self.ws.recv()
            data = json.loads(resp)
            if data.get('method') == 'Page.loadEventFired':
                logger.debug('页面加载完成')
                break

    async def evaluate_js(self, expression: str) -> Any:
        """执行JavaScript并返回结果"""
        result = await self._send_message("Runtime.evaluate", {"expression": expression})
        return result.get('result', {}).get('result', {}).get('value')

    async def toggle_deepsearch(self, enable: bool) -> bool:
        """切换DeepSearch功能"""
        logger.debug(f'切换DeepSearch: enable={enable}')
        
        js_get_btn = '''
            (() => {
                try {
                    let btn = Array.from(document.querySelectorAll('button'))
                        .find(b => b.getAttribute('aria-label') === 'DeepSearch');
                    if (!btn) return JSON.stringify({found: false});
                    return JSON.stringify({
                        found: true,
                        ariaPressed: btn.getAttribute('aria-pressed'),
                        outerHTML: btn.outerHTML
                    });
                } catch (e) {
                    return JSON.stringify({error: e.message});
                }
            })()
        '''
        
        # 查找并切换按钮状态
        for _ in range(5):
            btn_info = await self.evaluate_js(js_get_btn)
            try:
                btn_info = json.loads(btn_info) if btn_info else {}
            except json.JSONDecodeError:
                logger.error(f"按钮信息解析失败: {btn_info}")
                continue
                
            if btn_info.get('found'):
                current = btn_info.get('ariaPressed')
                target = 'true' if enable else 'false'
                if current == target:
                    return True
                    
                # 点击按钮
                js_click = '''
                    (() => {
                        let btn = Array.from(document.querySelectorAll('button'))
                            .find(b => b.getAttribute('aria-label') === 'DeepSearch');
                        if (!btn) return 'notfound';
                        btn.click();
                        return 'clicked';
                    })()
                '''
                await self.evaluate_js(js_click)
                
                # 验证状态是否更新
                btn_info = await self.evaluate_js(js_get_btn)
                try:
                    btn_info = json.loads(btn_info) if btn_info else {}
                    if btn_info.get('ariaPressed') == target:
                        logger.debug('DeepSearch切换成功')
                        return True
                except json.JSONDecodeError:
                    continue
            
            logger.warning('未找到DeepSearch按钮，重试中...')
            await asyncio.sleep(0.5)
            
        logger.error('DeepSearch切换失败')
        return False

    async def ask_grok(self, question: str, deepsearch: bool = True) -> Optional[str]:
        """向Grok提问并获取回答"""
        logger.debug(f'提问: {question}, deepsearch={deepsearch}')
        
        # 启用DeepSearch
        if deepsearch:
            if not await self.toggle_deepsearch(True):
                raise RuntimeError('DeepSearch启用失败')
        
        # 输入问题前等待 textarea 出现
        js_check_textarea = f'''
            (() => {{
                let params = {{tag: 'textarea'}};
                let result = {FIND_ELEMENT_JS}(params);
                return result.length > 0 ? 'found' : 'notfound';
            }})()
        '''
        for _ in range(20):  # 最多等10秒
            textarea_status = await self.evaluate_js(js_check_textarea)
            if textarea_status == 'found':
                logger.debug('已检测到textarea')
                break
            logger.warning('未检测到textarea，重试中...')
            await asyncio.sleep(0.5)
        else:
            logger.error('长时间未检测到textarea，放弃提问')
            return None

        # 输入问题
        js_set_question = f'''
            (() => {{
                let params = {{tag: 'textarea'}};
                let result = {FIND_ELEMENT_JS}(params);
                if (!result.length) return 'notfound';
                let el = document.querySelectorAll('textarea')[0];
                let descriptor = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value');
                descriptor.set.call(el, {json.dumps(question)});
                let event = new Event('input', {{ bubbles: true }});
                el.dispatchEvent(event);
                return 'ok';
            }})()
        '''
        await self.evaluate_js(js_set_question)
        
        # 点击发送
        js_click_send = f'''
            (() => {{
                let params = {{tag: 'button', type: 'submit'}};
                let result = {FIND_ELEMENT_JS}(params);
                if (!result.length) return 'notfound';
                let btn = Array.from(document.querySelectorAll('button')).find(b => b.getAttribute('type') === 'submit');
                btn.click();
                return 'clicked';
            }})()
        '''
        await self.evaluate_js(js_click_send)
        
        # 捕获API响应
        target_api = '/rest/app-chat/conversations/new'
        target_request_id = None
        
        async def wait_for_api_response():
            nonlocal target_request_id
            while True:
                resp = await self.ws.recv()
                data = json.loads(resp)
                if data.get('method') == 'Network.requestWillBeSent':
                    url = data['params']['request']['url']
                    if target_api in url:
                        target_request_id = data['params']['requestId']
                        logger.debug(f'捕获到目标API请求: {url}, requestId={target_request_id}')
                if data.get('method') == 'Network.loadingFinished' and target_request_id:
                    if data['params']['requestId'] == target_request_id:
                        result = await self._send_message("Network.getResponseBody", 
                                                        {"requestId": target_request_id})
                        return result.get('result', {}).get('body')
        try:
            return await asyncio.wait_for(wait_for_api_response(), timeout=900)
        except asyncio.TimeoutError:
            logger.error('等待API响应超时（10分钟）')
            return None

async def grok_ask_api_async(question: str, deepsearch: bool = True) -> Optional[str]:
    """异步API：向Grok提问"""
    async with GrokClient() as client:
        await client.navigate("https://grok.com/chat#private")
        return await client.ask_grok(question, deepsearch)

def grok_ask_api(question: str, deepsearch: bool = True) -> Optional[str]:
    """同步API：向Grok提问"""
    logger.debug(f'grok_ask_api 入参: question={question}, deepsearch={deepsearch}')
    result = asyncio.run(grok_ask_api_async(question, deepsearch))
    logger.debug(f'grok_ask_api 出参: {result[:200] if result else result}')
    return result

__all__ = ['GrokClient', 'grok_ask_api', 'grok_ask_api_async']
