import os
from utils.llm import llm_gen_dict,get_llm_client
import requests
import logging
from pyairtable import Table

logger = logging.getLogger(__name__)

def get_seedream_key():
    """从 Airtable 获取 SEEDREAM 配置，包括密钥和URL
    Returns:
         dict: 包含 cookie_value 和 url 的字典
    """
    logger.info("[get_seedream_key] 开始从 Airtable 获取 SEEDREAM 密钥")
    try:
        airtable_key = os.environ.get('AIRTABLE_KEY')
        base_id = os.environ.get('AIRTABLE_BASE_ID')
        table_name = 'cookies'

        table = Table(airtable_key, base_id, table_name)
        records = table.all(formula=f"{{Name}} = 'dreamina'")
        print(records)
        for record in records:
            if record['fields'].get('Name') == 'dreamina':
                seedream_key = record['fields'].get('cookie_value')
                dreamina_endpoint = record['fields'].get('endpoint')
                if seedream_key and dreamina_endpoint:
                    logger.info("[get_seedream_key] 成功获取 SEEDREAM 配置, cookie_value: {}， endpoint: {}".format(seedream_key, dreamina_endpoint))
                    return {"cookie_value": seedream_key, "endpoint": dreamina_endpoint}
                else:
                    logger.error("[get_seedream_key] 未获取到完整的SEEDREAM配置, cookie_value: {}， endpoint: {}".format(seedream_key, dreamina_endpoint))
                    return None

        logger.error("[get_seedream_key] 未在 Airtable 中找到 SEEDREAM 配置")
        return None

    except Exception as e:
        logger.error(f"[get_seedream_key] 获取 SEEDREAM 配置失败: {str(e)}")
        return None

def generate_image(prompt:str):
    logger.info(f'[generate_image] 开始处理, prompt长度: {len(prompt)}')
    jsonformat={
        'description':'someone some action somewhere',
    }
    sys_prompt='''you are a helpful assistant that write a excellent midjourney prompt for the user's query.
Now, you need to turn the request into a detailed prompt for user to generate a beautiful image on midjourney.
Avoid words like robot and AI, let human as main character in the prompt. for example, two young ladies shopping in a futuristic store.
DONT USE BRANDS OR PRODUCTS SUCH AI OPENAI, GOOGLE, XAI, ANTHROPIC AND SO ON!
'''
    prompt= f'{sys_prompt} output English json like {jsonformat} to call a serp tool, user query:\n'+prompt
    llm_client = get_llm_client()
    model='gpt-4o-mini'
    desc = llm_gen_dict(llm_client,model,prompt,jsonformat)
    logger.info(f'[generate_image] 生成的描述: {desc}')

    # 获取 SEEDREAM 配置，包括密钥和URL
    config = get_seedream_key()
    if not config:
        logger.error("[generate_image] 无法获取 SEEDREAM 配置")
        return []
    # 构建请求数据
    headers = {
        'Authorization': f'Bearer {config["cookie_value"]}'
    }

    data = {
        "model": "jimeng-3.0",
        "prompt": desc['description'],
        "width": 1584,
        "height": 1056,
        "sample_strength": 0.5
    }

    # 发送请求
    response = requests.post(
        config["endpoint"],
        headers=headers,
        json=data
    )
    # 解析响应
    result = response.json()
    os.makedirs('downloads', exist_ok=True)

    urls = [x['url'] for x in result['data']]
    logger.info(f"[generate_image] 生成的图片数量: {len(urls)}")
    for i, image_url in enumerate(urls):
        logger.debug(f"[generate_image] 生成图片URL {i+1}: {image_url}")

    return urls