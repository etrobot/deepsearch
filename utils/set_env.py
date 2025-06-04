import os
import logging
from pyairtable import Table
import browser_cookie3

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
            # 先尝试 browser_cookie3 获取 sessionid
            sessionid = None
            try:
                cj = browser_cookie3.chromium(
                    cookie_file='/browser-data',
                    domain_name='dreamina.capcut.com'
                )
                for c in cj:
                    if c.domain == 'dreamina.capcut.com' and c.name == 'sessionid':
                        sessionid = c.value
                        break
                if sessionid:
                    os.environ['DREAMINA_SESSIONID'] = sessionid
                    logging.info('已通过 browser_cookie3 获取并设置 DREAMINA_SESSIONID')
                else:
                    os.environ['DREAMINA_API_KEY'] = fields['key']
            except Exception as e:
                os.environ['DREAMINA_API_KEY'] = fields['key']
                logging.warning(f'browser_cookie3 获取 sessionid 失败，已设置 DREAMINA_API_KEY: {e}')

    logging.info("环境变量设置完成")