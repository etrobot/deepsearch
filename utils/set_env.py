import os
import logging
from pyairtable import Table

def set_env_from_airtable_data():
    """从 Airtable 数据设置环境变量，dreamina 优先尝试 browser_cookie3 获取 sessionid，获取不到再用 Airtable 的 api key"""
    logging.info("开始设置环境变量")
    data = Table(
            os.environ['AIRTABLE_KEY'],
            os.environ['AIRTABLE_BASE_ID'],
            'APIKeys'
        ).all(formula="{category} = 'deepsearch'")
    # 映射 Airtable 记录到环境变量
    for record in data:
        fields = record['fields']
        name = fields.get('Name', '').lower()
        
        if name == 'notion':
            os.environ['NOTION_API_KEY'] = fields['key']
            os.environ['NOTION_DATABASE_ID'] = fields['db_id']
            logging.info("已设置 Notion 相关环境变量")
            
        elif name == 'openrouter':
            os.environ['OPENROUTER_API_KEY'] = fields['key']
            os.environ['OPENROUTER_BASE_URL'] = fields['endpoint']
            logging.info("已设置 OpenRouter 相关环境变量")

        elif name == 'time':
            os.environ['DAILY_TIME'] = fields['key']
            logging.info("已设置每日时间环境变量")
            
        elif name == 'discord':
            os.environ['DISCORD_WEBHOOK_URL'] = fields['endpoint']
            logging.info("已设置 Discord Webhook 环境变量")
            
        elif name == 'dreamina':
            os.environ['DREAMINA_BASE_URL'] = fields['endpoint']
            os.environ['DREAMINA_API_KEY'] = fields['key']
            logging.info('已设置 DREAMINA_API_KEY')

    logging.info("环境变量设置完成")