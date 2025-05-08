import re
from notion_client import Client

class NotionMarkdownManager:
    def __init__(self, api_key, database_id):
        self.notion = Client(auth=api_key)
        self.database_id = database_id

    def list_articles_in_status(self,status:str):
        response = self.notion.databases.query(
            **{
                "database_id": self.database_id,
                "filter": {
                    "property": "Status",
                    "status": {
                        "equals": status
                    }
                }
            }
        )
        articles = response.get('results', [])
        return articles

    def retrieve_block(self, block_id):
        return self.notion.blocks.retrieve(block_id)

    def get_page_id_from_block(self, block_id):
        """
        Retrieves the parent page ID of a given block
        Args:
            block_id (str): The ID of the block
        Returns:
            str: The ID of the parent page, or None if not found
        """
        block = self.retrieve_block(block_id)
        if block and 'parent' in block:
            parent = block['parent']
            if parent['type'] == 'page_id':
                return parent['page_id']
        return None

    def retrieve_block_children(self, block_id):
        return self.notion.blocks.children.list(block_id)

    def parse_block(self, block):
        content = ""
        block_type = block['type']

        if block_type == 'paragraph':
            content += self.format_rich_text(block['paragraph']['rich_text']) + "\n\n"

        elif block_type == 'heading_1':
            content += "# " + self.format_rich_text(block['heading_1']['rich_text']) + "\n\n"

        elif block_type == 'heading_2':
            content += "## " + self.format_rich_text(block['heading_2']['rich_text']) + "\n\n"

        elif block_type == 'heading_3':
            content += "### " + self.format_rich_text(block['heading_3']['rich_text']) + "\n\n"

        elif block_type == 'bulleted_list_item':
            content += "- " + self.format_rich_text(block['bulleted_list_item']['rich_text']) + "\n"

        elif block_type == 'numbered_list_item':
            content += "1. " + self.format_rich_text(block['numbered_list_item']['rich_text']) + "\n"

        elif block_type == 'toggle':
            content += "<details>\n<summary>" + self.format_rich_text(block['toggle']['rich_text']) + "</summary>\n"
            if block['has_children']:
                children_blocks = self.retrieve_block_children(block['id'])
                for child_block in children_blocks['results']:
                    content += self.parse_block(child_block)
            content += "\n</details>\n"

        # Add more block types as needed

        if block['has_children'] and block_type not in ['toggle']:  # For blocks that aren't toggle
            children_blocks = self.retrieve_block_children(block['id'])
            for child_block in children_blocks['results']:
                content += self.parse_block(child_block)

        return content

    def format_rich_text(self, rich_text):
        text_content = ""
        for text in rich_text:
            annotations = text['annotations']
            plain_text = text['plain_text']

            if annotations['bold']:
                plain_text = f"**{plain_text}**"
            if annotations['italic']:
                plain_text = f"*{plain_text}*"
            if annotations['strikethrough']:
                plain_text = f"~~{plain_text}~~"
            if annotations['underline']:
                plain_text = f"<u>{plain_text}</u>"
            if annotations['code']:
                plain_text = f"`{plain_text}`"

            text_content += plain_text
        return text_content

    def get_article_content(self, page_id):
        response = self.notion.blocks.children.list(page_id)
        content = ""
        for block in response['results']:
            # print(block['id'])
            content += self.parse_block(block)
        return content

    def markdown_to_notion_blocks(self, md_text):
        # 预处理 markdown 文本
        # 1. 移除连续的空行，只保留一个
        md_text = re.sub(r'\n{3,}', '\n\n', md_text)
        # 2. 移除每行开头和结尾的空白字符
        lines = [line.strip() for line in md_text.split('\n')]
        # 3. 移除空行（但保留段落之间的一个空行）
        processed_lines = []
        prev_line_empty = True  # 用于跟踪前一行是否为空
        for line in lines:
            if line:  # 非空行
                processed_lines.append(line)
                prev_line_empty = False
            elif not prev_line_empty:  # 当前行为空且前一行非空
                processed_lines.append(line)
                prev_line_empty = True
        # 4. 重新组合文本
        md_text = '\n'.join(processed_lines)
        print(f"[markdown_to_notion_blocks] 预处理后的文本行数: {len(processed_lines)}")

        def create_heading_1(text):
            return {
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            }

        def create_heading_2(text):
            return {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            }

        def create_heading_3(text):
            return {
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            }

        def create_bulleted_list_item(text):
            return {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            }

        def create_numbered_list_item(text):
            return {
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            }

        def create_quote(text):
            return {
                "object": "block",
                "type": "quote",
                "quote": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            }

        def create_link(text, href):
            return {
                "type": "text",
                "text": {
                    "content": text,
                    "link": {"url": href}
                }
            }

        def create_image_block(url):
            return {
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {
                        "url": url
                    }
                }
            }

        def parse_paragraph(text):
            # Patterns to match Markdown-style links and bold text
            link_pattern = re.compile(r'\[([^\]]+)\]\((http[^\)]+)\)')
            rich_text = []
            last_end = 0
            seen_links = set()  # To keep track of seen links and avoid duplicates

            # First, handle the links, removing <b> tags and other HTML tags from the link text
            matches = []
            for match in link_pattern.finditer(text):
                link_text, link_url = match.groups()
                # Remove HTML tags from the link text, including <b> tags
                cleaned_link_text = re.sub(r'<[^>]+>', '', link_text)
                if link_url not in seen_links:  # Check if the link is already processed
                    matches.append((match.start(), match.end(), "link", cleaned_link_text, link_url))
                    seen_links.add(link_url)  # Mark this link as seen

            bold_pattern = re.compile(r'<b>([^<]+)</b>')
            # Then handle bold tags and other matches
            # for match in bold_pattern.finditer(text):
            #     matches.append((match.start(), match.end(), "bold", match.group(1)))

            # Sort all matches by their start position
            matches = sorted(matches, key=lambda m: m[0])

            for match in matches:
                start, end, match_type = match[:3]

                # Add plain text before the match
                if start > last_end:
                    rich_text.append({"type": "text", "text": {"content": text[last_end:start]}})

                if match_type == "link":
                    # Link: clean text and add as a link
                    cleaned_link_text, link_url = match[3], match[4]
                    rich_text.append(create_link(cleaned_link_text, link_url))
                elif match_type == "bold":
                    # Bold text: add with bold annotation
                    bold_text = match[3]
                    rich_text.append({"type": "text", "text": {"content": bold_text}, "annotations": {"bold": True}})

                last_end = end

            # Add any remaining text after the last match
            if last_end < len(text):
                rich_text.append({"type": "text", "text": {"content": text[last_end:]}})

            return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": rich_text}}

        blocks = []
        lines = md_text.split("\n")
        print(f"[markdown_to_notion_blocks] 总行数: {len(lines)}")
        current_paragraph = []

        for line_idx, line in enumerate(lines):
            # 处理图片语法
            image_match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', line)
            if image_match:
                # 如果有累积的段落,先添加段落
                if current_paragraph:
                    blocks.append(parse_paragraph("\n".join(current_paragraph)))
                    current_paragraph = []
                # 添加图片块    
                blocks.append(create_image_block(image_match.group(2)))
                print(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 添加图片块")
                continue
            
            if len(line) == 0:
                # 如果当前有累积的段落文本，将其作为一个块添加
                if current_paragraph:
                    blocks.append(parse_paragraph("\n".join(current_paragraph)))
                    print(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 空行，添加累积的段落，段落行数: {len(current_paragraph)}")
                    current_paragraph = []
                continue
            
            if line.startswith(("# ", "## ", "### ", "- ", "1. ", "> ")):
                # 如果遇到特殊格式，先处理累积的段落
                if current_paragraph:
                    blocks.append(parse_paragraph("\n".join(current_paragraph)))
                    print(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 特殊格式前，添加累积的段落，段落行数: {len(current_paragraph)}")
                    current_paragraph = []
                
                # 处理特殊格式的行
                if line.startswith("# "):
                    blocks.append(create_heading_1(line[2:]))
                    print(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 添加一级标题")
                elif line.startswith("## "):
                    blocks.append(create_heading_2(line[3:]))
                    print(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 添加二级标题")
                elif line.startswith("### "):
                    blocks.append(create_heading_3(line[4:]))
                    print(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 添加三级标题")
                elif line.startswith("- "):
                    blocks.append(create_bulleted_list_item(line[2:]))
                    print(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 添加无序列表项")
                elif line.startswith("1. "):
                    blocks.append(create_numbered_list_item(line[3:]))
                    print(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 添加有序列表项")
                elif line.startswith("> "):
                    blocks.append(create_quote(line[2:]))
                    print(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 添加引用")
            else:
                # 普通文本行，添加到当前段落
                current_paragraph.append(line)
                print(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 累积到当前段落")
        
        # 处理最后剩余的段落文本
        if current_paragraph:
            blocks.append(parse_paragraph("\n".join(current_paragraph)))
            print(f"[markdown_to_notion_blocks] 处理最后剩余的段落，段落行数: {len(current_paragraph)}")

        print(f"[markdown_to_notion_blocks] 总共生成块数: {len(blocks)}")
        return blocks

    def insert_markdown_to_notion(self, md_text, title=None, cover_url=None):
        blocks = []
        if len(md_text) > 100:
            blocks = self.markdown_to_notion_blocks(md_text)
            # 如果没有传入标题，尝试从blocks中获取第一个h1标题
            if title is None and len(blocks) > 0:
                for block in blocks:
                    if block.get('type') == 'heading_1':
                        title = block['heading_1']['rich_text'][0]['text']['content']
                        print(f"从内容中提取到标题: {title}")
                        break
        
        if title is None:
            # 移除markdown图片语法
            clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', md_text)
            # 移除其他markdown语法
            clean_text = re.sub(r'[#*_~`>]', '', clean_text)
            # 移除空行
            clean_text = '\n'.join(line.strip() for line in clean_text.split('\n') if line.strip())
            # 使用第一行非空文本作为标题
            title = clean_text.split('\n')[0][:60] if clean_text else "Untitled"
            print(f"未找到标题，使用处理后的内容作为标题: {title}")

        # 创建页面参数
        create_params = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                },
                "Status": {
                    "status": {
                        "name": "Draft"
                    }
                }
            },
            "children": []  # 先创建空页面
        }

        # 如果提供了封面图片URL，添加到参数中
        if cover_url:
            create_params["cover"] = {
                "type": "external",
                "external": {
                    "url": cover_url
                }
            }

        # 创建页面
        response = self.notion.pages.create(**create_params)
        page_id = response['id']
        print(f"创建空页面成功，ID: {page_id}")

        # 分批处理块
        chunk_size = 100
        for i in range(0, len(blocks), chunk_size):
            chunk = blocks[i:i + chunk_size]
            print(f"添加第 {i//chunk_size + 1} 批块，数量: {len(chunk)}")
            self.notion.blocks.children.append(
                block_id=page_id,
                children=chunk
            )

        return page_id

    def update_markdown_to_notion(self, page_id, md_text, title=None):
        blocks = []
        if len(md_text) > 100:
            blocks = self.markdown_to_notion_blocks(md_text)
            if title is None:
                title = md_text[:60]
                if len(blocks) > 0 and 'heading_1' in blocks[0]:
                    title = blocks[0]['heading_1']['rich_text'][0]['text']['content']

        # 更新页面标题
        self.notion.pages.update(
            page_id=page_id,
            properties={
                "Name": {
                    "title": [{"text": {"content": title}}]
                },
                "Status": {
                    "status": {"name": "Draft"}
                }
            }
        )

        # 清空旧的内容
        self.clear_notion_page_content(page_id)

        # 分批处理块
        chunk_size = 100
        for i in range(0, len(blocks), chunk_size):
            chunk = blocks[i:i + chunk_size]
            self.notion.blocks.children.append(
                block_id=page_id,
                children=chunk
            )

    def clear_notion_page_content(self, page_id):
        # 获取页面的现有内容块并逐一删除
        blocks = self.notion.blocks.children.list(block_id=page_id).get('results')
        for block in blocks:
            self.notion.blocks.delete(block_id=block['id'])
    def append_blocks(self, page_id, blocks):
        """
        向页面追加新的块
        Args:
            page_id (str): 页面ID
            blocks (list): 要添加的块列表
        Returns:
            dict: API响应
        """
        return self.notion.blocks.children.append(
            block_id=page_id,
            children=blocks
        )

    def get_page_property(self, page_id, property_name):
        print(f"[get_page_property] 入参 page_id={page_id}, property_name={property_name}")
        page = self.notion.pages.retrieve(page_id=page_id)
        print(f"[get_page_property] 页面属性 keys: {list(page['properties'].keys())}")
        prop = page['properties'].get(property_name)
        if not prop:
            print(f"[get_page_property] 未找到属性: {property_name}")
            return None
        if prop['type'] == 'rich_text':
            value = ''.join([t['plain_text'] for t in prop['rich_text']])
            print(f"[get_page_property] rich_text value: {value}")
            return value
        print(f"[get_page_property] 属性类型: {prop['type']}，请根据类型自行处理")
        return prop
