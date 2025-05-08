import os,re
from utils.notion import NotionMarkdownManager
from utils.ripGrok import call_grok_api
from dotenv import load_dotenv,find_dotenv
from utils.seedream import generate_image
load_dotenv(find_dotenv())

if __name__ == '__main__':
    manager = NotionMarkdownManager(os.environ['NOTION_API_KEY'], os.environ['NOTION_DATABASE_ID'])
    noiton_pages =  manager.list_articles_in_status("Prompt")
    print(f"[main] 获取到 Notion 页面数量: {len(noiton_pages)}")
    for idx, page in enumerate(noiton_pages):
        title = page['properties']['Name']['title'][0]['plain_text']
        status = page['properties']['Status']['status']['name']
        print(f"{idx+1}: {title} (id={page['id']}, status={status})")
    choice_str = input("请选择要处理的页面序号(可用逗号或空格分隔多个): ")
    # 支持多种分隔符
    choices = re.split(r'[\s,]+', choice_str.strip())
    # 过滤空字符串，转为int，去重并排序
    choices = sorted(set(int(c) for c in choices if c.isdigit()))
    # 让用户选择语言
    lang_choice = input("请选择语言: 1. English  2. 中文 (默认1): ").strip()
    if lang_choice == "2":
        lang = "中文"
    else:
        lang = "English"
    print(f"[main] 你选择的语言: {lang}")

    print(f"[main] 你选择了以下页面序号(从1开始): {choices}")
    for idx, choice in enumerate(choices):
        # choices从1开始，转换为0-based索引
        page_idx = choice - 1
        if page_idx < 0 or page_idx >= len(noiton_pages):
            print(f"[main][警告] 序号{choice}超出范围，跳过")
            continue
        id = noiton_pages[page_idx]['id']
        status = noiton_pages[page_idx]['properties']['Status']['status']['name']
        if lang == "中文":
            title =  manager.get_page_property(id, 'intro_cn')
            opening = "本期视频将介绍" + title.replace('\n', ' ')
        elif lang == 'English':
            title =  manager.get_page_property(id, 'intro_en')
            opening = "This video will introduce " + title.replace('\n', ' ')
        todo_prompt = manager.get_article_content(id).strip()

        print(f"[main][{idx}] 处理页面: {choice}, id={id}, status={status}, title={title}, 内容长度: {len(todo_prompt)},\n介绍：{opening}")
        todo_md_path = f"projects/{id}/todo.md"
        os.makedirs(os.path.dirname(todo_md_path), exist_ok=True)

        #将英文作为默认
        if os.path.exists(todo_md_path) or lang != 'English':
            print(f"[main][{idx}] 检测到本地 {todo_md_path}，直接读取")
            with open(todo_md_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            if not md_content.strip().startswith('![thumbnail](') and lang=='English':
                image_url = generate_image(md_content)
                md_content = f'![thumbnail]({image_url})\n\n{md_content}'
                manager.insert_markdown_to_notion(md_content, title=title, cover_url=image_url)
                with open(todo_md_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
            if lang != 'English' and not os.path.exists(f"projects/{id}/script_en.json"):
                os.rename( f"projects/{id}/script.json",  f"projects/{id}/script_en.json")
        else:
            print(f"[main][{idx}] 未检测到本地 {todo_md_path}，调用 grok 接口生成内容")
            grok_result = call_grok_api(todo_prompt,'grok-3-deepsearch')
            image_url = generate_image(grok_result)
            print(f"[main][{idx}] grok 返回内容长度: {len(grok_result)}")
            print(f"[main][{idx}] grok 返回内容前500字符:\n{grok_result[:500]}")
            # 从grok_result中提取第一个标题
            md_content = f'![thumbnail]({image_url})\n\n{grok_result}'
            # 将生成的图片作为封面图片
            manager.insert_markdown_to_notion(md_content, title=title.replace('\n',' ').strip(), cover_url=image_url)
            with open(todo_md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
