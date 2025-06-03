import json
import logging
from typing import Dict, Any, Optional

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

def parse_grok_result(response: str) -> Optional[Dict[str, Any]]:
    """
    解析grok返回的多行JSON字符串，结构化返回结果。
    
    Args:
        response: Grok API返回的响应字符串
        
    Returns:
        解析后的结构化数据，如果解析失败则返回None
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

    final_dict = {}
    grok_info = {}
    new_title = None

    # 3. 按行解析JSON字符串
    for line in response.splitlines():
        try:
            parsed = json.loads(line)
            # 以grok解析结构为例，假设有grokResult、meta等字段
            if "grokResult" in parsed.get("result", {}):
                parsed["result"]["response"] = {"grokResult": parsed["result"].pop("grokResult")}
            if "meta" in parsed.get("result", {}):
                grok_info = parsed["result"]["meta"]
            if "title" in parsed.get("result", {}):
                new_title = parsed["result"]["title"].get("newTitle")
            if "grokResult" in parsed.get("result", {}).get("response", {}):
                final_dict = parsed
            elif "grokResult" in parsed.get("result", {}):
                parsed["result"]["response"] = grok_info
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            logger.warning(f"解析JSON行时出错: {e}")
            continue

    # 4. 组装最终结构
    if final_dict and "result" in final_dict:
        grok_result = final_dict["result"].get("response", {}).get("grokResult")
        if grok_result:
            final_dict["result"]["response"] = {"grokResult": grok_result}
            final_dict["result"]["response"].update({
                "metaId": grok_info.get("metaId"),
                "title": grok_info.get("title"),
                "createTime": grok_info.get("createTime"),
                "modifyTime": grok_info.get("modifyTime"),
                "temporary": grok_info.get("temporary"),
                "newTitle": new_title
            })
            return final_dict
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
