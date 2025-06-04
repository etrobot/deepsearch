from app import dailyMission
from pyairtable import Table
import os
from utils.seedream import generate_image
from utils.set_env import set_env_from_airtable_data

def test_generate_image():
    print('--- 图片生成测试 ---')
    try:
        urls = generate_image('A group of engineers working in a futuristic lab')
        if urls:
            print(f'[TEST] 图片生成成功，返回URL数量: {len(urls)}')
            for i, url in enumerate(urls):
                print(f'  图片{i+1}: {url}')
        else:
            print('[TEST] 图片生成无结果或发生异常，请查看日志')
    except Exception as e:
        print('[TEST] 图片生成异常:')
        import traceback
        traceback.print_exc()

def test_airtable_formula():
    try:
        airtable = Table(
            os.environ['AIRTABLE_KEY'],
            os.environ['AIRTABLE_BASE_ID'],
            'prompt'
        )
        print('[TEST] Airtable连接成功，开始查询...')
        records = airtable.all(formula="{status} = 'Ready'")
        print(f'[TEST] 查询成功，记录数量: {len(records)}')
    except Exception as e:
        print('[TEST] Airtable 查询异常:')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    set_env_from_airtable_data()
    print('--- 图片生成测试 ---')
    test_generate_image()
    # print('--- dailyMission 测试 ---')
    # dailyMission(1)
