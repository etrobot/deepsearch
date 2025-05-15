import os,logging

def check_required_env_vars():
    """检查必需的环境变量是否已设置"""
    required_env_vars = [
        'NOTION_API_KEY',
        'NOTION_DATABASE_ID',
        'OPENROUTER_API_KEY',
        'OPENROUTER_BASE_URL',
        'GROK3API',
        'GROK_API_KEY',
        'AIRTABLE_KEY',
        'AIRTABLE_BASE_ID',
        'DAILY_TIME',
        'DISCORD_WEBHOOK_ID'
    ]
    missing_vars = []
    for var in required_env_vars:
        value = os.environ.get(var)
        logging.debug(f"检查环境变量 {var}: {'已设置' if value else '未设置'}")
        if not value:
            missing_vars.append(var)
    if missing_vars:
        error_msg = f"缺少必需的环境变量: {', '.join(missing_vars)}"
        logging.error(error_msg)
        raise EnvironmentError(error_msg)
