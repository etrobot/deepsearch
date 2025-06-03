import logging
from grok_client import grok_ask_api
from utils.grok_utils import parse_grok_result

# 配置日志
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')

def main():
    # 示例用法
    question = "hostest AI Video model on X"
    
    # 调用 Grok API 获取原始响应
    raw_response = grok_ask_api(question, deepsearch=True)
    print(f'原始响应: {raw_response[:200]}...' if raw_response else '无响应')
    
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
