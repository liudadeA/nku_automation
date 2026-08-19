#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用python-markdown和python-docx库将Markdown转换为DOCX
"""

import markdown
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import RGBColor
from docx.enum.style import WD_STYLE_TYPE


def md_to_docx(md_file_path, docx_file_path):
    """
    将Markdown文件转换为DOCX文件
    
    Args:
        md_file_path: Markdown文件路径
        docx_file_path: 输出DOCX文件路径
    """
    # 创建Document对象
    doc = Document()
    
    # 设置全局字体样式
    styles = doc.styles
    
    # 设置正文样式
    normal_style = styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(12)  # 小四号字
    normal_style.font._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    
    # 设置段落样式
    normal_style.paragraph_format.line_spacing = 1.5  # 1.5倍行间距
    
    # 读取Markdown文件内容
    with open(md_file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # 按行处理内容
    lines = md_content.split('\n')
    
    for line in lines:
        line = line.strip()
        
        if not line:
            doc.add_paragraph()
        elif line.startswith('# '):
            # 一级标题 - 题目
            heading = doc.add_heading(level=0)  # 使用level 0创建更突出的标题
            heading_run = heading.add_run(line[2:])
            heading_run.font.name = 'Times New Roman'
            heading_run.font.size = Pt(16)  # 三号字
            heading_run.font.bold = True
            heading_run.font._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif line.startswith('**姓名** **学号** **专业** **班级**'):
            # 个人信息
            para = doc.add_paragraph()
            para_run = para.add_run(line)
            para_run.font.name = 'Times New Roman'
            para_run.font.size = Pt(10.5)  # 五号字
            para_run.font._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif line.startswith('## 摘  要'):
            # 摘要标题
            heading = doc.add_heading(level=2)
            heading_run = heading.add_run(line[3:])
            heading_run.font.name = 'Times New Roman'
            heading_run.font.size = Pt(14)  # 四号字
            heading_run.font.bold = True
            heading_run.font._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif line.startswith('**关键词**：'):
            # 关键词
            para = doc.add_paragraph()
            # 关键词三个字
            key_run = para.add_run('关键词：')
            key_run.font.name = 'Times New Roman'
            key_run.font.size = Pt(12)  # 小四号字
            key_run.font.bold = True
            key_run.font._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
            # 关键词内容
            content_run = para.add_run(line[6:])
            content_run.font.name = 'Times New Roman'
            content_run.font.size = Pt(12)  # 小四号字
            content_run.font._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        elif line.startswith('## '):
            # 二级标题 - 正文章节标题
            heading = doc.add_heading(level=2)
            heading_run = heading.add_run(line[3:])
            heading_run.font.name = 'Times New Roman'
            heading_run.font.size = Pt(13)  # 小三号字
            heading_run.font.bold = True
            heading_run.font._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
        elif line.startswith('### '):
            # 三级标题 - 正文小节标题
            heading = doc.add_heading(level=3)
            heading_run = heading.add_run(line[4:])
            heading_run.font.name = 'Times New Roman'
            heading_run.font.size = Pt(12)  # 小四号字
            heading_run.font.bold = True
            heading_run.font._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
        elif line.startswith('- '):
            # 无序列表
            para = doc.add_paragraph(style='List Bullet')
            para_run = para.add_run(line[2:])
            para_run.font.name = 'Times New Roman'
            para_run.font.size = Pt(12)  # 小四号字
            para_run.font._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        elif line.startswith('1. '):
            # 有序列表
            para = doc.add_paragraph(style='List Number')
            para_run = para.add_run(line[3:])
            para_run.font.name = 'Times New Roman'
            para_run.font.size = Pt(12)  # 小四号字
            para_run.font._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        else:
            # 普通段落 - 正文内容
            para = doc.add_paragraph()
            para_run = para.add_run(line)
            para_run.font.name = 'Times New Roman'
            para_run.font.size = Pt(12)  # 小四号字
            para_run.font._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    
    # 保存DOCX文件
    doc.save(docx_file_path)
    print(f"转换完成：{md_file_path} -> {docx_file_path}")


if __name__ == "__main__":
    # 转换3_with_format.md到3_with_format.docx
    md_file = "3_with_format.md"
    docx_file = "3_with_format.docx"
    md_to_docx(md_file, docx_file)