import os
from utils.llm import llm_gen_dict,get_llm_client
import requests
import random

def generate_image(prompt:str):
    jsonformat={
        'description':'someone some action somewhere',
    }
    sys_prompt='''you are a helpful assistant that write a excellent midjourney prompt for the user's query.
Now, you need to turn the request into a detailed prompt for user to generate a beautiful image on midjourney.
Avoid words like robot and AI, let human as main character in the prompt. for example, two young ladies shopping in a futuristic store. 
AVOID AD-LIKED WORDS SUCH AS BRANDS OR PRODUCTS!
'''
    prompt= f'{sys_prompt} output English json like {jsonformat} to call a serp tool, user query:\n'+prompt
    llm_client = get_llm_client()
    model='gpt-4o-mini'
    desc = llm_gen_dict(llm_client,model,prompt,jsonformat)
    print(f'keyword:{desc}')

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
        os.environ['DREAMIA'],
        headers=headers,
        json=data
    )
    # 解析响应
    result = response.json()
    os.makedirs('downloads', exist_ok=True)
    
    chosen_url = random.choice(result['data'])['url']
    print(f"[generate_image] chosen_url:{chosen_url}")

    urls = [x['url'] for x in result['data'] if x['url'] != chosen_url]
    for i, image_url in enumerate(urls):
        print(f"[generate_image] 生成图片URL {i+1}: {image_url}")
        # 下载图片并保存到本地
        img_resp = requests.get(image_url)
        with open(f'downloads/thumbnail_{i+1}.png', 'wb') as f:
                    f.write(img_resp.content)
        
    with open('downloads/thumbnail.png', 'wb') as f:
        f.write(requests.get(chosen_url).content)
    # 随机返回一个URL
    return chosen_url