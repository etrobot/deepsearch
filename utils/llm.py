"""
LLM 相关工具函数
"""

import json
import time,os
import openai
import logging

def get_llm_config(scheme='openai'):
    """
    获取 LLM 服务的配置信息

    Args:
        scheme: 服务类型，支持 'openai' 和 'siliconflow'

    Returns:
        tuple: (api_key, base_url)
    """
    if scheme == 'siliconflow':
        api_key = os.environ["SILICONFLOW_API_KEY"]
        base_url = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    else:
        api_key = os.environ["OPENROUTER_API_KEY"]
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://api.openai.com/v1")

    if not api_key:
        raise ValueError(f"未找到 {scheme} 的 API Key，请在环境变量中设置")

    return api_key, base_url

def llm_gen_dict(llm: openai.Client, model: str, query: str, format: dict, stream=False, thinking=False) -> dict:
    """
    使用 LLM 生成指定格式的 Python 字典响应

    Args:
        llm: OpenAI 客户端实例
        model: 模型名称
        query: 查询内容
        format: 期望的字典格式
        stream: 是否使用流式模式

    Returns:
        dict: 生成的字典数据，失败则返回 None
    """
    # 配置日志记录器
    logger = logging.getLogger('llm_gen_dict')
    logger.setLevel(logging.DEBUG)

    # 检查是否已经有处理器，如果没有则添加
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    logger.debug(f"开始生成字典，查询内容: {query}")
    logger.info(f"stream模式: {stream}")
    prompt = f"\n请输出Python字典格式，不要使用JSON：\n{str(format)}\n"
    messages=[{
        "role": "user",
        "content": query + prompt + " 请确保输出严格的Python字典格式(长文本用三引号)，不要有额外的文本"
    }]
    if thinking:
        messages.insert(0,{"role": "system", "content": f"detailed thinking on"})

    for retry in range(3):
        logger.info(f"第{retry+1}次尝试生成字典...")
        try:
            if not stream:
                # 非流式模式
                llm_response = llm.chat.completions.create(
                    model=model,
                    messages=messages,
                )
                response_content = llm_response.choices[0].message.content
                logger.info(f"收到的完整响应: {response_content}")
            else:
                # 流式模式
                logger.info("使用流式模式接收响应，将在完成后提取字典")
                response_content = ""
                stream_response = llm.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True
                )

                first_chunk = True
                for chunk in stream_response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content_chunk = chunk.choices[0].delta.content
                        if first_chunk:
                            logger.debug("llm:", end=" ", flush=True)
                            first_chunk = False
                        logger.debug(content_chunk, end="", flush=True)
                        response_content += content_chunk
                if not first_chunk:
                    logger.debug("")  # 只在有内容时换行

                logger.info(f"流式响应完成，收集到的完整内容: {response_content}")

            # 使用正则表达式提取字典
            import re
            dict_pattern = r'({[\s\S]*})'  # 更宽松的模式，可以匹配多行字典
            dict_matches = re.search(dict_pattern, response_content, re.DOTALL)

            if dict_matches:
                dict_str = dict_matches.group(1)
                logger.info(f"提取到字典字符串: {dict_str}")
                try:
                    # 使用ast.literal_eval更安全地解析Python字典
                    import ast
                    result = ast.literal_eval(dict_str)
                    logger.info(f"成功解析字典: {result.keys()}")
                except SyntaxError as se:
                    logger.error(f"字典解析语法错误: {str(se)}")
                    # 尝试清理字典字符串
                    cleaned_dict = re.sub(r'```python|```', '', dict_str).strip()
                    logger.info(f"尝试清理后的字典: {cleaned_dict}")
                    try:
                        result = ast.literal_eval(cleaned_dict)
                        logger.info("清理后成功解析")
                    except Exception as e2:
                        logger.error(f"清理后解析仍然失败: {str(e2)}")
                        result = None
            else:
                logger.error(f"无法从响应中提取字典: {response_content}")
                result = None

            if result is not None:
                if not isinstance(result, dict):
                    if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
                        result = result[0]
                        logger.info("将列表结果转换为字典")
                    else:
                        logger.error(f"无效的响应格式，不是字典\n{result}\n")
                        result = None

            if result is not None:
                logger.info(f"第{retry+1}次尝试成功！")
                return result
            else:
                logger.warning(f"第{retry+1}次尝试失败，准备重试...")
        except Exception as e:
            logger.error(f"第{retry+1}次发生错误: {str(e)}")
            if '429' in str(e):
                logger.warning("遇到429，等待28秒后重试...")
                time.sleep(28)
            else:
                time.sleep(2)
    logger.error("三次尝试均失败，返回None")
    return None

def get_llm_client(scheme='openai'):
    """
    获取 OpenAI 或其他 LLM 服务的客户端

    Args:
        scheme: 客户端类型，支持 'openai' 和 'siliconflow'

    Returns:
        openai.Client: 配置好的客户端实例
    """
    # 设置日志记录器
    logger = logging.getLogger('get_llm_client')

    try:
        apikey, base_url = get_llm_config(scheme)

        # 打印日志但隐藏完整 API Key
        if apikey:
            masked_key = apikey[:4] + "..." + apikey[-4:] if len(apikey) > 8 else "***"
            logger.info(f"使用 {scheme} API Key: {masked_key}")
        else:
            logger.warning(f"警告: 未找到 {scheme} API Key")

        if base_url:
            logger.info(f"使用 API 基础 URL: {base_url}")

        client = openai.Client(api_key=apikey, base_url=base_url)
        logger.info(f"已成功初始化 {scheme} 客户端")
        return client
    except Exception as e:
        logger.error(f"初始化 {scheme} 客户端出错: {e}")
        raise

def process_subtitle_to_sentences(csv_lines_txt: str, client: openai.Client) -> dict:
    """
    处理字幕内容并生成摘要

    Args:
        csv_lines_txt: CSV格式的字幕内容
        client: OpenAI 客户端实例

    Returns:
        dict: 包含处理后的字幕和摘要的字典，失败则返回原始CSV文本
    """
    logger = logging.getLogger('process_subtitle')

    try:
        # 定义期望的输出格式
        keywords_format = {
            "a-c": "a sentence of the video script lines",
            "b-f": "another sentence of the video script lines, the line number can be overlap",
            "...": "..."
        }

        # 构建提示词
        prompt = f'''{csv_lines_txt}
        base on the video info, combine the video script above into sentences following the original tone and language with linenumbers, MUST fix the wrong spelling in the scripts following the info
        '''

        # 获取LLM模型名称
        llm_model = 'gpt-4o-mini'

        # 生成摘要
        video_script = llm_gen_dict(client, llm_model, prompt, keywords_format)
        video_summary = client.chat.completions.create(
            model=llm_model,
            messages=[{"role": "user","content": csv_lines_txt +' summarize the video above into keypoints'}],
            stream=False
        )
        return {
            "video_script": video_script,
            "summary": video_summary.choices[0].message.content
        }

    except Exception as e:
        logger.error(f"LLM处理失败: {str(e)}")
        logger.error(f"错误详情: {e.__class__.__name__}")
        # 如果LLM处理失败，返回原始CSV格式
        return None


def img2txt(img_url: str, image_promt: str, client: openai.Client = None) -> str:
    """
    将图片转换为文本描述

    Args:
        img_url: 图片的URL或base64编码的图片数据
        image_promt: 图片描述提示词

    Returns:
        str: 图片描述
    """
    logger = logging.getLogger('img2txt')

    if client is None:
        client = get_llm_client()

    # 检查并确保 img_url 格式正确
    if img_url.startswith('data:'):
        # 验证 base64 格式是否正确
        if not img_url.startswith('data:image/'):
            logger.error("图片格式不正确")
            return "错误: 图片格式不正确"
    else:
        # 记录URL处理
        logger.debug(f"处理图片URL: {img_url[:30]}...")

    # 构造请求内容
    request_content = [
        {"type": "image_url", "image_url": {"url": img_url}},
        {"type": "text", "text": image_promt}
    ]

    try:
        logger.info(f"开始请求图像描述，提示词: {image_promt}")
        response = client.chat.completions.create(
                    model="deepseek-ai/deepseek-vl2",
                    messages=[{
                        "role": "user",
                        "content": request_content
                    }],
            )
        img_desc = response.choices[0].message.content
        logger.info("成功获取图像描述")
        return img_desc
    except Exception as e:
        error_type = e.__class__.__name__
        error_msg = str(e)
        # 尝试打印完整错误消息，便于调试
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            logger.error(f"API 响应内容: {e.response.text}")
        elif hasattr(e, 'json'):
            logger.error(f"API 错误详情: {e.json()}")
        logger.error(f"处理图片时出错: {error_type} - {error_msg}")
        return f"处理图片时出错: {error_type} - {error_msg[:100]}"

# if __name__=='__main__':
#     test = get_llm_client().chat.completions.create(
#         model='gpt-4o-mini',
#         messages=[{'role':'user','content':'hello'}]
#     )
#     print(test)