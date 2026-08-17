#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用python-markdown和python-docx库将Markdown转换为DOCX
"""

import re
from markdown import markdown
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

def md_to_docx(md_file_path, docx_file_path):
    """
    将Markdown文件转换为DOCX文件
    
    Args:
        md_file_path: Markdown文件路径
        docx_file_path: 输出DOCX文件路径
    """
    # 创建Document对象
    doc = Document()
    
    # 设置全局字体为微软雅黑
    for style in doc.styles:
        if hasattr(style, 'font'):
            style.font.name = 'Microsoft YaHei'
            if hasattr(style.font, '_element'):
                style.font._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
    
    # 读取Markdown文件内容
    with open(md_file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # 按行处理Markdown内容
    lines = md_content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 处理标题
        if line.startswith('# '):
            # 一级标题
            heading = doc.add_heading(level=1)
            heading_run = heading.add_run(line[2:].strip())
            heading_run.font.size = Pt(16)
            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif line.startswith('## '):
            # 二级标题
            heading = doc.add_heading(level=2)
            heading_run = heading.add_run(line[3:].strip())
            heading_run.font.size = Pt(14)
        elif line.startswith('### '):
            # 三级标题
            heading = doc.add_heading(level=3)
            heading_run = heading.add_run(line[4:].strip())
            heading_run.font.size = Pt(12)
        
        # 处理列表项
        elif line.startswith('- '):
            # 无序列表
            paragraph = doc.add_paragraph(style='List Bullet')
            add_formatted_text(paragraph, line[2:].strip())
        elif line.startswith('1. '):
            # 有序列表
            paragraph = doc.add_paragraph(style='List Number')
            add_formatted_text(paragraph, line[3:].strip())
        
        # 处理空行
        elif not line:
            doc.add_paragraph()
        
        # 处理普通段落
        else:
            paragraph = doc.add_paragraph()
            add_formatted_text(paragraph, line.strip())
        
        i += 1
    
    # 保存DOCX文件
    doc.save(docx_file_path)
    print(f"转换完成：{md_file_path} -> {docx_file_path}")

def add_formatted_text(paragraph, text):
    """
    向段落中添加格式化文本，支持粗体(** **)和斜体(* *)
    
    Args:
        paragraph: docx段落对象
        text: 要添加的文本（可能包含格式化标记）
    """
    # 处理粗体
    parts = re.split(r'(\*\*.*?\*\*)', text)
    for part in parts:
        if part.startswith('**') and part.endswith('**'):
            # 粗体文本
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        else:
            # 普通文本
            paragraph.add_run(part)

if __name__ == "__main__":
    # 转换最优控制复习资料
    md_file = "最优控制复习资料.md"
    docx_file = "最优控制复习资料.docx"
    md_to_docx(md_file, docx_file)