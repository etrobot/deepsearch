import os
from utils.llm import llm_gen_dict,get_llm_client
import requests
import random
import logging

logger = logging.getLogger(__name__)

def generate_image(prompt:str):
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
    logger.info(f'keyword:{desc}')

    # 构建请求数据
    headers = {
        'Authorization': f'Bearer {os.environ["SEEDREAM"]}'
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
        os.environ['DREAMINA'],
        headers=headers,
        json=data
    )
    # 解析响应
    result = response.json()
    os.makedirs('downloads', exist_ok=True)
    
    chosen_url = random.choice(result['data'])['url']
    logger.info(f"[generate_image] chosen_url:{chosen_url}")

    urls = [x['url'] for x in result['data'] if x['url'] != chosen_url]
    for i, image_url in enumerate(urls):
        logger.debug(f"[generate_image] 生成图片URL {i+1}: {image_url}")        
    # 随机返回一个URL
    return chosen_url