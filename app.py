import os,time
import logging
import sys
from utils.llm import get_llm_client,llm_gen_dict
from utils.nitter import nitter_list_rss
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
from utils.notion import NotionMarkdownManager
from pyairtable import Table
from utils.ripGrok import call_grok_api
from utils.discord import DiscordWebhook
from dotenv import load_dotenv,find_dotenv
from utils.seedream import generate_image
from utils.set_env import set_env_from_airtable_data
import random,traceback

# 配置logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())
set_env_from_airtable_data()

def validate_notion_response(response, context=""):
    """验证 Notion API 响应"""
    if not response:
        raise ValueError(f"Notion API 返回空响应 {context}")
    return response

def dailyMission():
    logger.info(f"[定时任务] 开始执行dailyMission - {time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 初始化环境变量
        set_env_from_airtable_data()

        discord = DiscordWebhook()

        logger.info("[Airtable] 初始化 Table")
        airtable = Table(
            os.environ['AIRTABLE_KEY'],
            os.environ['AIRTABLE_BASE_ID'],
            'prompts'
        )

        logger.info("[Notion] 初始化 NotionMarkdownManager")
        manager = NotionMarkdownManager(os.environ['NOTION_API_KEY'], os.environ['NOTION_DATABASE_ID'])

        airtable_records = airtable.all(formula="{status} = 'Ready'")
        logger.info(f"[Airtable] 找到 {len(airtable_records)} 个prompts")

        success_count = 0
        error_count = 0
        error_messages = []

        for idx, record in enumerate(airtable_records):
            try:
                id = record['id']
                fields = record['fields']
                status = fields.get('status', 'Ready')
                logger.info(f"[处理记录][{idx}] 开始处理记录: id={id}, status={status}")

                # 获取 todo_prompt
                todo_prompt = nitter_list_rss(record['fields']['nitter_rss'])
                todo_prompt += 'pick the hottest topic from these tweets by verified accounts and use embedding mode to search more recent topic-related hot posts and output a xaiArtifact report'
                if todo_prompt is None:
                    logger.info(f"[处理记录][{idx}] 跳过空内容记录")
                    continue

                # 获取现有封面 URL
                existing_cover = fields.get('cover_url')
                logger.info(f"[处理记录][{idx}] 记录现有封面URL: {existing_cover}")

                logger.info(f"[处理记录][{idx}] 调用 grok api")
                grok_result = validate_notion_response(
                    call_grok_api(todo_prompt,'grok-3-deepsearch'),
                    f"调用 Grok API 处理记录 {id} 的内容"
                )
                title_format = {
                    'title_en':'upper title in english with \n， change lines between time, description and the leading role，such as 2025\nTOP 5\nREASONING MODEL',
                    'title_cn':'中文标题带换行（年份\n描述\n主体，比如"2025\n排名前五\n推理模型"）'
                }
                title_prompt = '\n\nWrite a title for this youtube video in 2025.'
                logger.info(f"[处理记录][{idx}] 生成标题")
                titles = validate_notion_response(
                    llm_gen_dict(get_llm_client(),'gpt-4o-mini',grok_result+title_prompt,title_format),
                    f"生成记录 {id} 的标题"
                )
                logger.info(f"[处理记录][{idx}] 生成的标题: {titles}")

                # 处理封面图片
                chosen_url = None
                if existing_cover:
                    chosen_url = existing_cover
                    logger.info(f"[处理记录][{idx}] 使用现有封面URL: {chosen_url}  清空原记录封面")
                    airtable.update(id, {
                        'status': 'Ready',
                        'cover_url': None
                    })
                else:
                    logger.info(f"[处理记录][{idx}] 生成新的图片")
                    try:
                        image_urls = generate_image(grok_result)
                        if image_urls:
                            logger.info(f"[处理记录][{idx}] 获取到 {len(image_urls)} 个图片URL")
                            chosen_url = random.choice(image_urls)
                            logger.info(f"[处理记录][{idx}] 随机选择的新图片URL: {chosen_url}")
                            remaining_urls = [imgurl for imgurl in image_urls if imgurl != chosen_url]
                            if remaining_urls:
                                airtable.update(id, {
                                    'status': 'Ready',
                                    'cover_url': random.choice(remaining_urls)
                                })
                        else:
                            logger.warning(f"[处理记录][{idx}] 图片生成失败，将不使用图片")
                    except Exception as e:
                        logger.error(f"[处理记录][{idx}] 图片生成过程出错: {str(e)}")

                logger.info(f"[处理记录][{idx}] 创建新的 Markdown 内容")
                md_content = grok_result
                if chosen_url:
                    md_content = f'![thumbnail]({chosen_url})\n\n{grok_result}'

                logger.info(f"[处理记录][{idx}] 插入新的 Notion 页面")
                create_params = {
                    "md_text": md_content,
                    "title": titles['title_en'].replace('\n',' ').strip()
                }
                if chosen_url:
                    create_params["cover_url"] = chosen_url

                new_page_id = validate_notion_response(
                    manager.insert_markdown_to_notion(**create_params),
                    f"创建记录 {id} 的新子页面"
                )
                logger.info(f"[处理记录][{idx}] 新页面创建成功: {new_page_id}")

                logger.info(f"[处理记录][{idx}] 更新新页面的属性")
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

                # 更新 Airtable 记录状态和封面 URL
                update_fields = {
                    'status': 'Done'
                }
                if chosen_url:
                    update_fields['cover_url'] = chosen_url
                airtable.update(id, update_fields)

                success_count += 1
                logger.info(f"[处理记录][{idx}] 记录处理完成")

            except Exception as e:
                error_message = f"处理第{idx+1}个记录时出错: {str(e)}\n{traceback.format_exc()}"
                logger.error(f"[处理记录][{idx}] {error_message}")
                error_count += 1
                error_messages.append(error_message)

        if success_count > 0:
            success_msg = f"成功处理了 {success_count} 个记录"
            logger.info(f"[任务完成] {success_msg}")
            discord.send_success(success_msg, title="每日任务完成")

        if error_count > 0:
            error_content = "\n".join([f"- {msg}" for msg in error_messages])
            error_msg = f"处理过程中遇到 {error_count} 个错误:\n{error_content}"
            logger.error(f"[任务错误] {error_msg}")
            discord.send_error(error_msg, title="处理过程有错误")

        logger.info(f"[定时任务] dailyMission执行结束")
    except Exception as e:
        error_msg = f"执行dailyMission出错: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"[定时任务] {error_msg}")
        discord.send_error(error_msg)
        sys.exit(1)

if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone=timezone('UTC'))
    try:
        # 将东八区的时间转换为UTC时间
        local_hour, local_minute = map(int, os.environ['DAILY_TIME'].split(':'))
        utc_hour = (local_hour - 8) % 24  # 东八区减8小时
        scheduler.add_job(
            dailyMission,
            trigger=CronTrigger(
                hour=utc_hour,
                minute=local_minute
            ),
            name='daily_notion_mission'
        )
        logger.info(f"[定时任务] 服务已启动，UTC时间{utc_hour}:{local_minute}执行任务（对应北京时间{local_hour}:{local_minute}）")
        scheduler.start()
    except Exception as e:
        error_msg = f"启动定时任务失败: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"[定时任务] {error_msg}")
        discord = DiscordWebhook(os.environ['DISCORD_WEBHOOK_URL'])
        discord.send_error(error_msg)
        sys.exit(1)
