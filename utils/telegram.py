import os
import requests
from typing import Optional

class TelegramBot:
    def __init__(self):
        self.token = os.environ['TELEGRAM_BOT_TOKEN']
        self.chat_id = os.environ['TELEGRAM_CHAT_ID']
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, text: str, title: Optional[str] = None) -> None:
        """发送消息到 Telegram
        
        Args:
            text: 消息内容
            title: 可选的标题
        """
        message = f"*{title}*\n\n{text}" if title else text
        
        try:
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                }
            )
            response.raise_for_status()
            print(f"[Telegram] 消息发送成功")
        except Exception as e:
            print(f"[Telegram] 发送消息失败: {str(e)}")
            
    def send_success(self, text: str, title: Optional[str] = None) -> None:
        """发送成功消息
        
        Args:
            text: 消息内容
            title: 可选的标题
        """
        success_text = f"✅ {text}"
        self.send_message(success_text, title)
        
    def send_error(self, text: str, title: Optional[str] = None) -> None:
        """发送错误消息
        
        Args:
            text: 消息内容
            title: 可选的标题
        """
        error_text = f"❌ {text}"
        self.send_message(error_text, title) 