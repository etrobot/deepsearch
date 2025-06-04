import os
from utils.llm import llm_gen_dict,get_llm_client
import requests
import logging

logger = logging.getLogger(__name__)

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
    desc = llm_gen_dict(llm_client,model,prompt[:600],jsonformat)
    logger.info(f'[generate_image] 生成的描述: {desc}')

    # 从环境变量获取配置
    api_key = os.environ['DREAMINA_API_KEY']
    base_url = os.environ['DREAMINA_BASE_URL']
    
    # 构建请求数据
    headers = {
        'Authorization': f'Bearer {api_key}'
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
        base_url,
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