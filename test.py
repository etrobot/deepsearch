from app import dailyMission,get_todo_prompt
from utils.notion import NotionMarkdownManager

import os

if __name__ == '__main__':
    os.environ['PROXY_URL'] = 'http://127.0.0.1:7890'
    # dailyMission()
    manager = NotionMarkdownManager(os.environ['NOTION_API_KEY'], os.environ['NOTION_DATABASE_ID'])
    print(get_todo_prompt(manager,'1e637564-38fa-80d3-be89-fc417d7e537f'))