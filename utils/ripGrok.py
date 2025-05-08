import re,os
import openai

def call_grok_api(todo_content, model="grok-3"):
    url = os.environ['GROK3API']
    client = openai.Client(api_key=os.environ['GROK_API_KEY'], base_url=url)
    resp = client.chat.completions.create(
        messages=[{"role": "user", "content": todo_content}],
        model=model,
        stream=True
    )
    response_content = ''
    first_chunk = True
    for chunk in resp:
        if chunk.choices and chunk.choices[0].delta.content:
            content_chunk = chunk.choices[0].delta.content
            print(content_chunk, end="", flush=True)
            response_content += content_chunk
    if not first_chunk:
        print()  # 只在有内容时换行
    # 提取带属性的<xaiArtifact>标签包裹的内容
    artifact_pattern = r'<xaiArtifact\b[^>]*>(.*?)</xaiArtifact>'
    artifact_matches = re.findall(artifact_pattern, response_content, re.DOTALL)
    return '\n'.join(artifact_matches) if artifact_matches else '---'.join(response_content.split('---')[1:])


    # 用正则从md中提取所有的 [描述]（推特链接），提取成tweet_id，info（日期和作者），summary
    links_dict = {}  # 使用字典替代列表，以链接作为键
    # 正则表达式查找包含 https://x.com/ 的行
    pattern = r'.*\((https://x\.com/[^)]+)\).*'
    # 兼容两种日期格式：2025年10月10日 和 2025-10-10
    date_pattern = r'(\d{4}[年-]\d{1,2}[月-]\d{1,2}日?)'

    for line in todo.split('\n'):
        # 先去除所有markdown符号，保留基本文本内容
        clean_line = re.sub(r'[*_~`#>]', '', line)

        match = re.search(pattern, clean_line)
        if match:
            tweet_link = match.group(1)
            tweet_id = tweet_link.split('/')[-1]

            # 提取日期信息（如果有）
            date_match = re.search(date_pattern, clean_line)
            date = date_match.group(1) if date_match else ""

            # 提取作者信息
            author_match = re.search(r'@([^\s)]+)', clean_line)
            author = author_match.group(1) if author_match else ""

            summary = re.sub(r'\s+', ' ', clean_line).strip()  # 统一空格并去除首尾空格

            # 提取不带https://x.com/的链接作为键
            key = tweet_link.replace('https://x.com/', '')

            # 如果是新链接或者当前行字数比已存储的更多，则更新记录
            if key not in links_dict or len(clean_line) > len(links_dict[key]['original_line']):
                links_dict[key] = {
                    "tweet_id": tweet_id,
                    "link": tweet_link,
                    "info": f"{date} - @{author}",
                    "summary": summary.replace('https://x.com/',''),
                    "original_line": clean_line  # 保存原始行用于比较长度
                }

    # 将字典转换为列表（去除original_line字段）
    links = []
    for key, data in links_dict.items():
        links.append({
            "tweet_id": data["tweet_id"],
            "link": data["link"],
            "info": data["info"],
            "summary": data["summary"]
        })

    print(f"总共提取到 {len(links)} 条不重复推文")

    # 添加日志，便于调试
    for i, link_data in enumerate(links):
        print(f"提取到的第{i+1}条推文:")
        print(f"  ID: {link_data['tweet_id']}")
        print(f"  链接: {link_data['link']}")
        print(f"  信息: {link_data['info']}")
        print(f"  摘要: {link_data['summary']}")

    return links