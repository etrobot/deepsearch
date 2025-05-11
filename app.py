import os,time
import logging
from utils.llm import get_llm_client,llm_gen_dict
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
from utils.notion import NotionMarkdownManager
from utils.ripGrok import call_grok_api
from utils.discord import DiscordWebhook
from dotenv import load_dotenv,find_dotenv
from utils.seedream import generate_image

# 配置logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())

def dailyMission():
    logger.info(f"[定时任务] 开始执行dailyMission - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    discord = DiscordWebhook()
    try:
        manager = NotionMarkdownManager(os.environ['NOTION_API_KEY'], os.environ['NOTION_DATABASE_ID'])
        noiton_pages =  manager.list_articles_in_status("Prompt")
        success_count = 0
        error_count = 0
        error_messages = []
        
        for idx, page in enumerate(noiton_pages):
            try:
                id = page['id']
                status = page['properties']['Status']['status']['name']
                todo_prompt = manager.get_article_content(id).strip()
                title_format = {
                    'title_en':'upper title in english with \n， change lines between time, description and the leading role，such as 2025\nTOP 5\nREASONING MODEL',
                    'title_cn':'中文标题带换行（年份\n描述\n主体，比如"2025\n排名前五\n推理模型"）'
                }
                title_prompt = '\n\nWrite a title for this youtube video.'
                titles =  llm_gen_dict(get_llm_client(),'gpt-4o-mini',todo_prompt+title_prompt,title_format)
                logger.info(f"[main][{idx}] 处理页面: id={id}, status={status}, title={titles}, 内容长度: {len(todo_prompt)}")
                logger.debug(f"[main][{idx}] 调用 grok api 前的 todo_prompt: {todo_prompt[:200]}...")
                grok_result = call_grok_api(todo_prompt,'grok-3-deepsearch')
                logger.debug(f"[main][{idx}] grok_result 类型: {type(grok_result)}, 值: {grok_result}")
                image_url = generate_image(grok_result)
                logger.info(f"[main][{idx}] grok 返回内容长度: {len(grok_result)}")
                logger.debug(f"[main][{idx}] grok 返回内容前500字符:\n{grok_result[:500]}")
                
                md_content = f'![thumbnail]({image_url})\n\n{grok_result}'
                new_page_id = manager.insert_markdown_to_notion(md_content, title=titles['title_en'].replace('\n',' ').strip(), cover_url=image_url)
                
                manager.notion.pages.update(
                    page_id=new_page_id,
                    properties={
                        "intro_en": {
                            "rich_text": [
                                {"type": "text", "text": {"content": titles['title_en']}}
                            ]
                        },
                        "intro_cn": {
                            "rich_text": [
                                {"type": "text", "text": {"content": titles['title_cn']}}
                            ]
                        }
                    }
                )
                
                manager.update_page_last_edited_time(id)
                success_count += 1
            except Exception as e:
                error_message = f"处理第{idx+1}个页面时出错: {str(e)}"
                logger.error(f"[main][{idx}] {error_message}")
                error_count += 1
                error_messages.append(error_message)
                
        if success_count > 0:
            success_msg = f"成功处理了 {success_count} 个页面"
            discord.send_success(success_msg, title="每日任务完成")
        
        if error_count > 0:
            error_content = "\n".join([f"- {msg}" for msg in error_messages])
            error_msg = f"处理过程中遇到 {error_count} 个错误:\n{error_content}"
            discord.send_error(error_msg, title="处理过程有错误")
            
        logger.info(f"[定时任务] 成功完成dailyMission")
    except Exception as e:
        error_msg = f"执行dailyMission出错: {str(e)}"
        logger.error(f"[定时任务] {error_msg}")
        discord.send_error(error_msg)

if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone=timezone('Asia/Shanghai'))
    hour, minute = map(int, os.environ['DAILY_TIME'].split(':'))
    scheduler.add_job(
        dailyMission,
        trigger=CronTrigger(
            hour=hour,
            minute=minute
        ),
        name='daily_notion_mission'
    )
    logger.info(f"[定时任务] 服务已启动，将在每天{hour}:{minute}执行任务")
    scheduler.start()
