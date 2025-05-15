import os
import logging
from pyairtable import Api, Table

logger = logging.getLogger(__name__)

class AirtableManager:
    def __init__(self, api_key, base_id, table_name):
        """
        初始化 Airtable 管理器

        Args:
            api_key (str): Airtable API 密钥
            base_id (str): Airtable base ID
            table_name (str): 表名
        """
        logger.info(f"[AirtableManager.__init__] 初始化 AirtableManager: base_id={base_id}, table_name={table_name}")
        self.table = Table(api_key, base_id, table_name)

    def list_pending_prompts(self):
        """
        获取所有状态为 Ready 的 prompts

        Returns:
            list: 包含状态为 Ready 的 prompt 记录列表
        """
        logger.info("[AirtableManager.list_pending_prompts] 开始获取 Ready 状态的 prompts")
        records = self.table.all(formula="{status} = 'Ready'")
        logger.debug(f"[AirtableManager.list_pending_prompts] 原始记录: {records}")
        logger.info(f"[AirtableManager.list_pending_prompts] 找到 {len(records)} 条 Ready 状态的记录")

        formatted_records = []
        for record in records:
            fields = record['fields']
            logger.debug(f"[AirtableManager.list_pending_prompts] 处理记录字段: {fields}")
            formatted_record = {
                'id': record['id'],
                'properties': {
                    'Status': {'status': {'name': fields.get('status', 'Ready')}},
                    'cover_url': fields.get('cover_url'),
                    'prompt': fields.get('Name', '') + '\n\n' + fields.get('prompt', '')
                }
            }
            formatted_records.append(formatted_record)

        return formatted_records

    def update_record(self, record_id, fields):
        """
        更新记录

        Args:
            record_id (str): 记录 ID
            fields (dict): 要更新的字段
        """
        logger.info(f"[AirtableManager.update_record] 更新记录 {record_id}, 字段: {fields}")
        return self.table.update(record_id, fields)