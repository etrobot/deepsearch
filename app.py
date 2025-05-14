import os,time
import logging
import sys
from utils.llm import get_llm_client,llm_gen_dict
from utils.vars import check_required_env_vars
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
from utils.notion import NotionMarkdownManager
from utils.ripGrok import call_grok_api
from utils.discord import DiscordWebhook
from dotenv import load_dotenv,find_dotenv
from utils.seedream import generate_image
import random,traceback

# 配置logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())

def validate_notion_response(response, context=""):
    """验证 Notion API 响应"""
    if not response:
        raise ValueError(f"Notion API 返回空响应 {context}")
    return response

def get_todo_prompt(manager, page_id):
    """
    获取页面的内容

    Args:
        manager: NotionMarkdownManager 实例
        page_id: Notion 页面 ID

    Returns:
        str: 页面内容
    """
    logger.info(f"[get_todo_prompt] 开始获取页面 {page_id} 的内容")

    # 获取页面主要内容
    todo_prompt = validate_notion_response(
        manager.get_article_content(page_id),
        f"获取页面 {page_id} 的内容"
    ).strip()

    if not todo_prompt:
        raise ValueError(f"页面 {page_id} 内容为空")

    logger.debug(f"[get_todo_prompt] 最终内容长度: {len(todo_prompt)} 前200字符: {todo_prompt[:200]}")
    return todo_prompt

def dailyMission():
    logger.info(f"[定时任务] 开始执行dailyMission - {time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 检查环境变量
        check_required_env_vars()

        discord = DiscordWebhook()

        logger.info("[Notion] 初始化 NotionMarkdownManager")
        manager = NotionMarkdownManager(os.environ['NOTION_API_KEY'], os.environ['NOTION_DATABASE_ID'])

        logger.info("[Notion] 获取 Prompt 状态的文章")
        notion_pages = validate_notion_response(
            manager.list_articles_in_status("Prompt"),
            "获取 Prompt 状态的文章"
        )
        logger.info(f"[Notion] 找到 {len(notion_pages)} 个 Prompt 状态的文章")

        success_count = 0
        error_count = 0
        error_messages = []

        for idx, page in enumerate(notion_pages):
            try:
                id = page['id']
                status = page['properties']['Status']['status']['name']
                logger.info(f"[处理页面][{idx}] 开始处理页面: id={id}, status={status}")

                # 获取 todo_prompt
                todo_prompt = get_todo_prompt(manager, id)

                # 获取页面封面信息
                logger.info(f"[处理页面][{idx}] 获取页面信息")
                page_info = manager.notion.pages.retrieve(page_id=id)
                logger.debug(f"[处理页面][{idx}] page_info原始内容: {page_info}")
                cover = page_info.get('cover', None)
                if cover and isinstance(cover, dict):
                    existing_cover = cover.get('external', {}).get('url', None)
                else:
                    existing_cover = None
                logger.info(f"[处理页面][{idx}] 页面现有封面URL: {existing_cover}")

                logger.info(f"[处理页面][{idx}] 调用 grok api")
                grok_result = validate_notion_response(
                    call_grok_api(todo_prompt,'grok-3-deepsearch'),
                    f"调用 Grok API 处理页面 {id} 的内容"
                )
                summary = llm_gen_dict(get_llm_client(),'gpt-4o-mini',grok_result+'extract the best choice of these arcicle',
                    {"summary":"summary in one sentence",
                     "best_picked":"the best pick from the data",
                     "related_links":["link1","link2","..."]}
                )
                grok_result = validate_notion_response(
                    call_grok_api(summary['summary']+summary['best_picked']+'\nUse embedding mode to find at least 5 best posts for this topic and ouput a ranking board in xaiArtifact','grok-3-deepsearch'),
                    f"调用 Grok API 处理 {summary} 的内容"
                )
                logger.debug(f"[处理页面][{idx}] grok_result 长度: {len(grok_result)} 前500字符: {grok_result[:500]}")
                title_format = {
                    'title_en':'upper title in english with \n， change lines between time, description and the leading role，such as 2025\nTOP 5\nREASONING MODEL',
                    'title_cn':'中文标题带换行（年份\n描述\n主体，比如"2025\n排名前五\n推理模型"）'
                }
                title_prompt = '\n\nWrite a title for this youtube video in 2025.'
                logger.info(f"[处理页面][{idx}] 生成标题")
                titles = validate_notion_response(
                    llm_gen_dict(get_llm_client(),'gpt-4o-mini',grok_result+title_prompt,title_format),
                    f"生成页面 {id} 的标题"
                )
                logger.info(f"[处理页面][{idx}] 生成的标题: {titles}")

                # 处理封面图片
                if existing_cover:
                    chosen_url = existing_cover
                    logger.info(f"[处理页面][{idx}] 使用现有封面URL: {chosen_url}  清空原页面封面")
                    manager.notion.pages.update(
                        page_id=id,
                        cover=None
                    )
                else:
                    logger.info(f"[处理页面][{idx}] 生成新的图片")
                    image_urls = validate_notion_response(
                        generate_image(grok_result),
                        f"为页面 {id} 生成图片"
                    )
                    if not image_urls:
                        raise ValueError(f"生成图片失败，返回空URL列表")

                    logger.info(f"[处理页面][{idx}] 获取到 {len(image_urls)} 个图片URL")
                    chosen_url = random.choice(image_urls)
                    logger.info(f"[处理页面][{idx}] 随机选择的新图片URL: {chosen_url} 为原始页面添加封面")
                    remaining_urls = [imgurl for imgurl in image_urls if imgurl != chosen_url]
                    if remaining_urls:
                        manager.notion.pages.update(
                            page_id=id,
                            cover={
                                "type": "external",
                                "external": {
                                    "url": random.choice(remaining_urls)
                                }
                            }
                        )

                logger.info(f"[处理页面][{idx}] 创建新的 Markdown 内容")
                md_content = f'![thumbnail]({chosen_url})\n\n{grok_result}'

                logger.info(f"[处理页面][{idx}] 插入新的 Notion 页面")
                new_page_id = validate_notion_response(
                    manager.insert_markdown_to_notion(
                        md_content,
                        title=titles['title_en'].replace('\n',' ').strip(),
                        cover_url=chosen_url
                    ),
                    f"创建页面 {id} 的新子页面"
                )
                logger.info(f"[处理页面][{idx}] 新页面创建成功: {new_page_id}")

                logger.info(f"[处理页面][{idx}] 更新新页面的属性")
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

                logger.info(f"[处理页面][{idx}] 更新原页面的最后编辑时间")
                manager.update_page_last_edited_time(id)

                success_count += 1
                logger.info(f"[处理页面][{idx}] 页面处理完成")

            except Exception as e:
                error_message = f"处理第{idx+1}个页面时出错: {str(e)}\n{traceback.format_exc()}"
                logger.error(f"[处理页面][{idx}] {error_message}")
                error_count += 1
                error_messages.append(error_message)

        if success_count > 0:
            success_msg = f"成功处理了 {success_count} 个页面"
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
        check_required_env_vars()
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
        discord = DiscordWebhook()
        discord.send_error(error_msg)
        sys.exit(1)
