import re
from notion_client import Client
import logging

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
        logging.debug(f"[markdown_to_notion_blocks] 预处理后的文本行数: {len(processed_lines)}")

        def parse_rich_text(text):
            """将文本解析为带有格式的rich_text"""
            # 匹配 Markdown 链接和粗体
            link_pattern = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')  # 链接
            bold_pattern = re.compile(r'\*\*(.+?)\*\*')  # 粗体，非贪婪匹配
            html_bold_pattern = re.compile(r'<b>(.+?)</b>')  # HTML粗体

            matches = []
            
            # 收集链接匹配
            for match in link_pattern.finditer(text):
                link_text, link_url = match.groups()
                # 清除链接文本中的HTML标签
                cleaned_link_text = re.sub(r'<[^>]+>', '', link_text)
                matches.append((match.start(), match.end(), "link", cleaned_link_text, link_url))
            
            # 收集粗体匹配
            for match in bold_pattern.finditer(text):
                matches.append((match.start(), match.end(), "bold", match.group(1)))
            
            # 收集HTML粗体匹配
            for match in html_bold_pattern.finditer(text):
                matches.append((match.start(), match.end(), "bold", match.group(1)))
            
            # 按位置排序
            matches = sorted(matches, key=lambda m: m[0])
            
            # 移除重叠匹配
            non_overlapping = []
            for match in matches:
                start, end = match[0], match[1]
                # 检查是否与之前的匹配重叠
                overlap = False
                for prev in non_overlapping:
                    if (start < prev[1] and end > prev[0]):
                        overlap = True
                        break
                if not overlap:
                    non_overlapping.append(match)
            
            # 构建rich_text
            rich_text = []
            last_end = 0
            for match in non_overlapping:
                start, end, match_type = match[0], match[1], match[2]
                
                # 添加匹配前的文本
                if start > last_end:
                    rich_text.append({"type": "text", "text": {"content": text[last_end:start]}})
                
                if match_type == "link":
                    link_text, url = match[3], match[4]
                    # 检查链接文本中是否包含粗体
                    bold_in_link = re.search(r'\*\*(.+?)\*\*', link_text)
                    if bold_in_link:
                        # 链接+粗体
                        bold_text = bold_in_link.group(1)
                        rich_text.append({
                            "type": "text", 
                            "text": {"content": bold_text, "link": {"url": url}},
                            "annotations": {"bold": True}
                        })
                    else:
                        # 普通链接
                        rich_text.append({
                            "type": "text", 
                            "text": {"content": link_text, "link": {"url": url}}
                        })
                elif match_type == "bold":
                    bold_text = match[3]
                    # 检查粗体中是否包含链接
                    link_in_bold = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', bold_text)
                    if link_in_bold:
                        # 粗体+链接
                        link_text, url = link_in_bold.groups()
                        rich_text.append({
                            "type": "text", 
                            "text": {"content": link_text, "link": {"url": url}},
                            "annotations": {"bold": True}
                        })
                    else:
                        # 普通粗体
                        rich_text.append({
                            "type": "text", 
                            "text": {"content": bold_text},
                            "annotations": {"bold": True}
                        })
                
                last_end = end
            
            # 添加最后一段文本
            if last_end < len(text):
                rich_text.append({"type": "text", "text": {"content": text[last_end:]}})
            
            # 移除空内容
            rich_text = [rt for rt in rich_text if rt["text"]["content"]]
            
            return rich_text
        
        def create_paragraph(text):
            """创建段落块"""
            rich_text = parse_rich_text(text)
            return {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": rich_text}
            }
        
        def create_heading_1(text):
            """创建一级标题块"""
            rich_text = parse_rich_text(text)
            return {
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": rich_text}
            }
        
        def create_heading_2(text):
            """创建二级标题块"""
            rich_text = parse_rich_text(text)
            return {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": rich_text}
            }
        
        def create_heading_3(text):
            """创建三级标题块"""
            rich_text = parse_rich_text(text)
            return {
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": rich_text}
            }
        
        def create_bulleted_list_item(text):
            """创建无序列表项"""
            rich_text = parse_rich_text(text)
            return {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": rich_text}
            }
        
        def create_numbered_list_item(text):
            """创建有序列表项"""
            rich_text = parse_rich_text(text)
            return {
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": rich_text}
            }
        
        def create_quote(text):
            """创建引用块"""
            rich_text = parse_rich_text(text)
            return {
                "object": "block",
                "type": "quote",
                "quote": {"rich_text": rich_text}
            }
        
        def create_image_block(url):
            """创建图片块"""
            return {
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {"url": url}
                }
            }
        
        def create_table_block(rows):
            """创建表格块"""
            if not rows or not rows[0]:
                return None
            
            # 确保至少有两行（表头+数据）
            if len(rows) < 2:
                rows.append([""] * len(rows[0]))
            
            # 处理表格单元格中的格式化文本
            processed_rows = []
            for row in rows:
                processed_row = []
                for cell in row:
                    # 为每个单元格处理格式化文本
                    rich_text = parse_rich_text(cell)
                    processed_row.append(rich_text)
                processed_rows.append(processed_row)
            
            return {
                "object": "block",
                "type": "table",
                "table": {
                    "table_width": len(rows[0]),
                    "has_column_header": True,
                    "has_row_header": False,
                    "children": [
                        {
                            "type": "table_row",
                            "table_row": {"cells": processed_rows[i]}
                        } for i in range(len(processed_rows))
                    ]
                }
            }
        
        blocks = []
        lines = md_text.split("\n")
        logging.debug(f"[markdown_to_notion_blocks] 总行数: {len(lines)}")
        
        current_paragraph = []
        table_rows = []
        in_table = False
        
        for line_idx, line in enumerate(lines):
            # 处理表格
            if line.strip() and '|' in line:
                # 检查是否为表格分隔行
                separator_pattern = re.compile(r'^[\s]*\|[-:\s|]*\|[\s]*$')
                if separator_pattern.match(line):
                    # 标记为表格，跳过分隔行
                    in_table = True
                    continue
                
                # 处理表格行
                if in_table or (line.strip().startswith('|') and line.strip().endswith('|')):
                    # 处理累积的段落
                    if current_paragraph:
                        blocks.append(create_paragraph("\n".join(current_paragraph)))
                        current_paragraph = []
                    
                    # 处理表格单元格
                    cells = [cell.strip() for cell in line.strip().split('|')]
                    if cells[0] == '':
                        cells = cells[1:]
                    if cells[-1] == '':
                        cells = cells[:-1]
                    
                    table_rows.append(cells)
                    in_table = True
                    continue
                elif in_table:
                    # 表格结束
                    if table_rows:
                        blocks.append(create_table_block(table_rows))
                        logging.debug(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 添加表格，行数: {len(table_rows)}")
                        table_rows = []
                    in_table = False
            
            # 表格结束处理
            if in_table and not line.strip():
                if table_rows:
                    blocks.append(create_table_block(table_rows))
                    logging.debug(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 表格后空行，添加表格，行数: {len(table_rows)}")
                    table_rows = []
                in_table = False
            
            # 处理图片
            image_match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', line)
            if image_match:
                if current_paragraph:
                    blocks.append(create_paragraph("\n".join(current_paragraph)))
                    current_paragraph = []
                
                blocks.append(create_image_block(image_match.group(2)))
                logging.debug(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 添加图片块")
                continue
            
            # 处理空行
            if not line.strip():
                if current_paragraph:
                    blocks.append(create_paragraph("\n".join(current_paragraph)))
                    logging.debug(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 空行，添加段落，段落行数: {len(current_paragraph)}")
                    current_paragraph = []
                continue
            
            # 处理特殊格式行
            if line.startswith(("# ", "## ", "### ", "- ", "1. ", "> ")):
                if current_paragraph:
                    blocks.append(create_paragraph("\n".join(current_paragraph)))
                    logging.debug(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 特殊格式前，添加段落，段落行数: {len(current_paragraph)}")
                    current_paragraph = []
                
                if line.startswith("# "):
                    blocks.append(create_heading_1(line[2:]))
                    logging.debug(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 添加一级标题")
                elif line.startswith("## "):
                    blocks.append(create_heading_2(line[3:]))
                    logging.debug(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 添加二级标题")
                elif line.startswith("### "):
                    blocks.append(create_heading_3(line[4:]))
                    logging.debug(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 添加三级标题")
                elif line.startswith("- "):
                    blocks.append(create_bulleted_list_item(line[2:]))
                    logging.debug(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 添加无序列表项")
                elif line.startswith("1. "):
                    blocks.append(create_numbered_list_item(line[3:]))
                    logging.debug(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 添加有序列表项")
                elif line.startswith("> "):
                    blocks.append(create_quote(line[2:]))
                    logging.debug(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 添加引用")
            else:
                # 普通文本行
                current_paragraph.append(line)
                logging.debug(f"[markdown_to_notion_blocks] 第{line_idx+1}行: 累积到当前段落")
        
        # 处理剩余内容
        if in_table and table_rows:
            blocks.append(create_table_block(table_rows))
            logging.debug(f"[markdown_to_notion_blocks] 处理文件末尾的表格，行数: {len(table_rows)}")
        elif current_paragraph:
            blocks.append(create_paragraph("\n".join(current_paragraph)))
            logging.debug(f"[markdown_to_notion_blocks] 处理最后剩余的段落，段落行数: {len(current_paragraph)}")
        
        logging.debug(f"[markdown_to_notion_blocks] 总共生成块数: {len(blocks)}")
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
                        logging.info(f"从内容中提取到标题: {title}")
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
            logging.info(f"未找到标题，使用处理后的内容作为标题: {title}")

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
        logging.info(f"创建空页面成功，ID: {page_id}")

        # 分批处理块
        chunk_size = 100
        for i in range(0, len(blocks), chunk_size):
            chunk = blocks[i:i + chunk_size]
            logging.info(f"添加第 {i//chunk_size + 1} 批块，数量: {len(chunk)}")
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
        logging.debug(f"[get_page_property] 入参 page_id={page_id}, property_name={property_name}")
        page = self.notion.pages.retrieve(page_id=page_id)
        logging.debug(f"[get_page_property] 页面属性 keys: {list(page['properties'].keys())}")
        prop = page['properties'].get(property_name)
        if not prop:
            logging.debug(f"[get_page_property] 未找到属性: {property_name}")
            return None
        if prop['type'] == 'rich_text':
            value = ''.join([t['plain_text'] for t in prop['rich_text']])
            logging.debug(f"[get_page_property] rich_text value: {value}")
            return value
        logging.debug(f"[get_page_property] 属性类型: {prop['type']}，请根据类型自行处理")
        return prop

    def update_page_last_edited_time(self, page_id):
        """
        更新页面的 Last edited time 为当前时间
        Args:
            page_id (str): 页面ID
        """
        logging.info(f"[update_page_last_edited_time] 更新页面 Last edited time: {page_id}")
        try:
            # 通过更新一个空的属性来触发 Last edited time 的更新
            self.notion.pages.update(
                page_id=page_id,
                properties={}
            )
            logging.info(f"[update_page_last_edited_time] 更新成功")
            return True
        except Exception as e:
            logging.error(f"[update_page_last_edited_time] 更新失败: {str(e)}")
            return False
