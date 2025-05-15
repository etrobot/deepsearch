from typing import Dict, List
import requests
import time as t
import logging
import os,re
from feedparser import parse
import html2text

logger = logging.getLogger(__name__)

XURL = 'https://x.com/'
DEFAULT_BASE_URL = os.environ['NITTER']
DEFAULT_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6',
    'Authorization': 'Basic c29sb2Z1bjp0eW1tMTExMTEx',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
}

def get_tweet_nitter(
    tweet_id: str,
    base_url: str = DEFAULT_BASE_URL,
    parse_content: bool = True
) -> Dict:
    """获取单条推文的详细信息"""
    logger.info(f"开始获取推文 - ID: {tweet_id}, 解析内容: {parse_content}")

    # 保存原始URL，这将是我们的推文链接
    original_tweet_link = tweet_id

    # 使用简化版的headers
    headers = {
        'Accept': DEFAULT_HEADERS['Accept'],
        'Accept-Language': DEFAULT_HEADERS['Accept-Language'],
        'Authorization': DEFAULT_HEADERS['Authorization'],
        'User-Agent': DEFAULT_HEADERS['User-Agent'],
    }

    tweet_url = f'{base_url}{tweet_id}'
    response = requests.get(
        tweet_url,
        headers=headers,
        verify=False,
    )
    response.raise_for_status()
    logger.info(f"获取推文成功 - 状态码: {response.status_code}")

    return response.text

def extract_thread_links_nitter(html_content: str) -> list:
    """从HTML内容中提取thread的所有推文链接

    Args:
        html_content: nitter返回的HTML内容

    Returns:
        list: thread中所有推文的链接列表,如果不是thread则返回空列表
    """
    # 使用正则表达式匹配所有推文链接
    pattern = r'class="tweet-link" href="/([^"]+/status/\d+)#m"'
    matches = re.findall(pattern, html_content)

    logger.debug(f"正则表达式匹配到的原始链接: {matches}")

    # 如果没有找到链接，尝试其他可能的模式
    if not matches:
        logger.info("尝试备用正则表达式模式")
        patterns = [
            r'href="/([^"]+/status/\d+)#m"',
            r'<a[^>]+href="/([^"]+/status/\d+)#m"[^>]*>',
            r'class="tweet-link"[^>]+href="/([^"]+/status/\d+)#m"'
        ]

        for p in patterns:
            matches = re.findall(p, html_content)
            if matches:
                logger.info(f"使用备用模式 '{p}' 找到链接")
                break

    if not matches:
        logger.warning("未找到任何推文链接")
        # 输出HTML片段以帮助调试
        logger.debug(f"HTML片段预览:\n{html_content[:1000]}")
        return []

    # 提取原始作者用户名（从第一个链接）
    first_link = matches[0]
    original_author = first_link.split('/')[0]
    logger.info(f"原始作者: {original_author}")

    # 找到连续的原作者推文
    continuous_tweets = []
    current_sequence = []

    for link in matches:
        current_author = link.split('/')[0]
        if current_author == original_author:
            current_sequence.append(link)
        else:
            # 如果遇到其他作者的推文，保存当前最长序列并重置
            if len(current_sequence) > len(continuous_tweets):
                continuous_tweets = current_sequence.copy()
            current_sequence = []

    # 检查最后一个序列
    if len(current_sequence) > len(continuous_tweets):
        continuous_tweets = current_sequence

    if not continuous_tweets:
        logger.warning("未找到原始作者的连续推文")
        return []

    # 去重并保持顺序
    links = list(dict.fromkeys(continuous_tweets))

    logger.info(f"找到thread中原始作者的连续推文: {len(links)} 条")
    return [XURL+l for l in links]


def check_thread_using_nitter(nitter_link:str):
    logger.info(f"原始链接: {nitter_link}")
    if nitter_link.startswith(XURL):
        nitter_link=nitter_link[len(XURL):]
        logger.debug(f"移除XURL后: {nitter_link}")
    if nitter_link.startswith(DEFAULT_BASE_URL):
        nitter_link=nitter_link[len(DEFAULT_BASE_URL):]
        logger.debug(f"移除DEFAULT_BASE_URL后: {nitter_link}")
    if not '/status/' in nitter_link:
        logger.warning("链接中不包含 /status/，返回空列表")
        return []
    logger.info(f"开始获取推文HTML，处理后的链接: {nitter_link}")
    rawhtml = get_tweet_nitter(nitter_link)
    logger.debug(f"获取到的HTML长度: {len(rawhtml)}")
    logger.debug(f"HTML片段预览: {rawhtml[:500]}")  # 只显示前500个字符
    links = extract_thread_links_nitter(rawhtml)
    return links

def nitter_list_rss(rss_url):
    """将RSS内容转换为markdown格式的文本

    Args:
        list_id: nitter list的ID

    Returns:
        str: 包含所有条目的markdown格式文本
    """

    feed = parse(rss_url)
    result = []

    for i in range(len(feed.entries)):
        entry = feed.entries[i]
        link = entry.link.replace('http://localhost:8080','x.com').replace('localhost:8080','x.com').replace('#m','')
        text_maker = html2text.HTML2Text()
        text_maker.ignore_images = True   # 保留图片
        text_maker.ignore_links = True    # 保留链接
        content = entry.description.replace('http://localhost:8080','x.com').replace('localhost:8080','x.com').replace('#m','')
        content = text_maker.handle(content)
        markdown_text = f"[{i}]({link})\n{content}\n---\n"
        result.append(markdown_text)

    return "\n".join(result)

def AI_news_tweets() -> List[str]:
    lists_txt = []
    for id in os.environ['LIST_IDS'].split(','):
        lists_txt.append(nitter_list_rss(id.strip()))
    return lists_txt


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    links = check_thread_using_nitter('minchoi/status/1904689072351641652')
    logger.info("Thread links:")
    for link in links:
        logger.info(f"- {link}")
    # logger.info(nitter_list_rss('1910888237314564276'))