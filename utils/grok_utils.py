import json
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# 通用JS查找方法
FIND_ELEMENT_JS = """
(function(params){
    let selector = params.tag || '*';
    let nodes = Array.from(document.querySelectorAll(selector));
    return nodes.map((node, idx) => {
        let ok = true;
        if (params.ariaLabel && node.getAttribute('aria-label') !== params.ariaLabel) ok = false;
        if (params.className && !(node.className||'').includes(params.className)) ok = false;
        if (params.innerText && node.innerText !== params.innerText) ok = false;
        if (params.type && node.getAttribute('type') !== params.type) ok = false;
        if (params.placeholder && node.getAttribute('placeholder') !== params.placeholder) ok = false;
        if (ok) {
            return {
                idx,
                tag: node.tagName,
                ariaLabel: node.getAttribute('aria-label'),
                className: node.className,
                type: node.getAttribute('type'),
                innerText: node.innerText,
                placeholder: node.getAttribute('placeholder'),
                outerHTML: node.outerHTML
            };
        }
        return null;
    }).filter(x=>x);
})"""

def parse_grok_result(response: str) -> str:
    """
    解析grok返回的多行JSON字符串，提取所有modelResponse.message内容，拼接成完整答案。
    
    Args:
        response: Grok API返回的响应字符串
        
    Returns:
        {"messages": [msg1, msg2, ...], "full_message": "..."}，如果解析失败则返回None
    """
    if not response:
        return None
    
    # 1. 错误字符串处理
    if isinstance(response, str) and response.startswith('Error:'):
        error_data = handle_str_error(response)
        if isinstance(error_data, dict):
            return error_data

    # 2. 区域不可用提示
    if 'This service is not available in your region' in response:
        return {'error': 'This service is not available in your region'}

    messages = []
    for line in response.splitlines():
        try:
            parsed = json.loads(line)
            # 提取modelResponse.message
            msg = parsed.get("result", {}).get("response", {}).get("modelResponse", {}).get("message")
            if msg:
                messages.append(msg)
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            logger.warning(f"解析JSON行时出错: {e}")
            continue
    if messages:
        return "".join(messages)
    return None

def handle_str_error(error_str: str) -> Dict[str, str]:
    """
    处理错误字符串
    
    Args:
        error_str: 错误信息字符串
        
    Returns:
        包含错误信息的字典
    """
    return {"error": error_str}

__all__ = ['parse_grok_result', 'FIND_ELEMENT_JS', 'handle_str_error']
