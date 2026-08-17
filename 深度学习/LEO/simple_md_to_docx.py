#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的Markdown到DOCX转换器
"""

import sys
import os
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH


def simple_md_to_docx(md_path, docx_path):
    """简单的Markdown到DOCX转换"""
    # 创建文档
    doc = Document()
    
    # 读取Markdown文件
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    current_paragraph = None
    in_code_block = False
    code_content = []
    
    for line in lines:
        line = line.rstrip()
        
        if not line:
            # 空行，添加新段落
            if current_paragraph and not in_code_block:
                doc.add_paragraph()
            continue
        
        if line.startswith('```'):
            # 代码块开始/结束
            if in_code_block:
                # 代码块结束
                if code_content:
                    # 添加代码段落
                    paragraph = doc.add_paragraph()
                    paragraph_run = paragraph.add_run('\n'.join(code_content))
                    paragraph_run.font.name = 'Consolas'
                    paragraph_run.font.size = Pt(10)
                    in_code_block = False
                    code_content = []
            else:
                # 代码块开始
                in_code_block = True
            continue
        
        if in_code_block:
            # 收集代码内容
            code_content.append(line)
            continue
        
        if line.startswith('# '):
            # 标题1
            heading = doc.add_heading(level=1)
            heading_run = heading.add_run(line[2:])
            heading_run.font.size = Pt(24)
            heading_run.bold = True
            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif line.startswith('## '):
            # 标题2
            heading = doc.add_heading(level=2)
            heading_run = heading.add_run(line[3:])
            heading_run.font.size = Pt(18)
            heading_run.bold = True
        elif line.startswith('### '):
            # 标题3
            heading = doc.add_heading(level=3)
            heading_run = heading.add_run(line[4:])
            heading_run.font.size = Pt(14)
            heading_run.bold = True
        elif line.startswith('#### '):
            # 标题4
            heading = doc.add_heading(level=4)
            heading_run = heading.add_run(line[5:])
            heading_run.font.size = Pt(12)
            heading_run.bold = True
        elif line.startswith('- ') or line.startswith('* '):
            # 无序列表
            paragraph = doc.add_paragraph(style='List Bullet')
            paragraph_run = paragraph.add_run(line[2:])
            paragraph_run.font.size = Pt(12)
        elif line.startswith('1. '):
            # 有序列表
            paragraph = doc.add_paragraph(style='List Number')
            paragraph_run = paragraph.add_run(line[3:])
            paragraph_run.font.size = Pt(12)
        elif line.startswith('!['):
            # 图片
            img_desc_end = line.find('](')
            img_path_start = img_desc_end + 2
            img_path_end = line.find(')', img_path_start)
            if img_desc_end != -1 and img_path_end != -1:
                img_path = line[img_path_start:img_path_end]
                if os.path.exists(img_path):
                    doc.add_picture(img_path, width=Inches(6.0))
        elif line.startswith('|'):
            # 表格
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            if cells and not any(cell.startswith('-') for cell in cells):
                # 检查是否是表格的第一行
                if not hasattr(doc, '_table_started') or not doc._table_started:
                    # 创建新表格
                    doc._table = doc.add_table(rows=0, cols=len(cells), style='Table Grid')
                    doc._table_started = True
                    is_header = True
                else:
                    is_header = False
                
                # 添加行
                table_row = doc._table.add_row()
                for i, cell in enumerate(cells):
                    table_row.cells[i].text = cell
                    if is_header:
                        table_row.cells[i].paragraphs[0].runs[0].bold = True
        elif line.startswith('|---'):
            # 表格分隔线，忽略
            continue
        else:
            # 普通段落
            paragraph = doc.add_paragraph()
            paragraph_run = paragraph.add_run(line)
            paragraph_run.font.size = Pt(12)
    
    # 保存文档
    doc.save(docx_path)
    print(f"成功将 {md_path} 转换为 {docx_path}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("用法: python simple_md_to_docx.py input.md output.docx")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    if not os.path.exists(input_path):
        print(f"错误: 输入文件 {input_path} 不存在")
        sys.exit(1)
    
    simple_md_to_docx(input_path, output_path)
