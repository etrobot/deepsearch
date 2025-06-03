import logging
from utils.grok_client import grok_ask_api
from utils.grok_utils import parse_grok_result

# 配置日志
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')

def main():
    # 示例用法
    question = "hostest AI Video model on X, output a xArtifact ranking board"
    
    # 调用 Grok API 获取原始响应
    raw_response = grok_ask_api(question, deepsearch=False)
    print(f'原始响应类型: {type(raw_response)}')
    print(f'原始响应长度: {len(raw_response) if raw_response else 0}')
    print(f'原始响应内容: {raw_response}')
    print(f'原始响应预览: {raw_response[:200]}...' if raw_response else '无响应')
    
    # 解析响应
    if raw_response:
        parsed_result = parse_grok_result(raw_response)
        if parsed_result:
            print('\n=== 解析结果 ===')
            print(parsed_result)
        else:
            print('无法解析响应')

if __name__ == "__main__":
    main()
