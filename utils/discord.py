import os
import requests
import logging
# from dotenv import load_dotenv,find_dotenv
# load_dotenv(find_dotenv())


logger = logging.getLogger(__name__)

class DiscordWebhook:
    def __init__(self, webhook_url=None, proxies=None):
        if webhook_url is None:
            webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        self.webhook_url = webhook_url
        if not self.webhook_url:
            raise ValueError("Discord webhook URL 未设置")
        self.proxies = proxies

    def send_message(self, content, title=None, color=None):
        """
        发送消息到 Discord
        
        Args:
            content: 消息内容
            title: 消息标题（可选）
            color: 消息颜色（可选），成功为绿色(0x00ff00)，失败为红色(0xff0000)
        """
        try:
            if not content:
                logger.warning("消息内容为空，跳过发送")
                return False

            payload = {
                "embeds": [{
                    "description": content,
                    "color": color or 0x00ff00  # 默认使用绿色
                }]
            }

            if title:
                payload["embeds"][0]["title"] = title

            if os.getenv('PROXY_URL'):
                self.proxies = {
                    'http': os.getenv('PROXY_URL'),
                    'https': os.getenv('PROXY_URL')
                }
            response = requests.post(
                self.webhook_url,
                json=payload,
                proxies=self.proxies
            )
            response.raise_for_status()
            logger.info(f"Discord消息发送成功: {content[:100]}...")
            return True
        except Exception as e:
            logger.error(f"发送Discord消息失败: {str(e)}")
            return False

    def send_success(self, content, title="任务成功"):
        """发送成功消息"""
        return self.send_message(content, title=title, color=0x00ff00)

    def send_error(self, content, title="任务失败"):
        """发送错误消息"""
        return self.send_message(content, title=title, color=0xff0000) 
    

# if __name__ == '__main__':
#     test_discord = DiscordWebhook()
#     test_discord.send_success('send_success')