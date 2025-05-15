from app import dailyMission,get_todo_prompt
from utils.notion import NotionMarkdownManager
from utils.airtable import AirtableManager

import os

if __name__ == '__main__':
    os.environ['PROXY_URL'] = 'http://127.0.0.1:7890'
    # airtable_manager = AirtableManager(
    #         os.environ['AIRTABLE_KEY'],
    #         os.environ['AIRTABLE_BASE_ID'],
    #         'prompts'
    #     )

    # airtable_records = airtable_manager.list_pending_prompts()

    # print(airtable_manager)
    dailyMission()