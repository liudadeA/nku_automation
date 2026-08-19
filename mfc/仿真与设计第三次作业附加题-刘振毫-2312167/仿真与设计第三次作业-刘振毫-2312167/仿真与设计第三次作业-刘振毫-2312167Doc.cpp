
// 仿真与设计第三次作业-刘振毫-2312167Doc.cpp: C仿真与设计第三次作业刘振毫2312167Doc 类的实现
//

#include "pch.h"
#include "framework.h"
// SHARED_HANDLERS 可以在实现预览、缩略图和搜索筛选器句柄的
// ATL 项目中进行定义，并允许与该项目共享文档代码。
#ifndef SHARED_HANDLERS
#include "仿真与设计第三次作业-刘振毫-2312167.h"
#endif

#include "仿真与设计第三次作业-刘振毫-2312167Doc.h"

#include <propkey.h>

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

// C仿真与设计第三次作业刘振毫2312167Doc

IMPLEMENT_DYNCREATE(C仿真与设计第三次作业刘振毫2312167Doc, CDocument)

BEGIN_MESSAGE_MAP(C仿真与设计第三次作业刘振毫2312167Doc, CDocument)
END_MESSAGE_MAP()


// C仿真与设计第三次作业刘振毫2312167Doc 构造/析构

C仿真与设计第三次作业刘振毫2312167Doc::C仿真与设计第三次作业刘振毫2312167Doc() noexcept
{
	m_nShapeType = 0;
	m_ptTopLeft = CPoint(0, 0);
	m_ptBottomRight = CPoint(0, 0);
	m_nLineStyle = 0;
	m_color = RGB(0, 0, 0);
	m_dArea = 0;
	m_dPerimeter = 0;
	m_dLength = 0;
	m_bDraw = false;
}

C仿真与设计第三次作业刘振毫2312167Doc::~C仿真与设计第三次作业刘振毫2312167Doc()
{
}

BOOL C仿真与设计第三次作业刘振毫2312167Doc::OnNewDocument()
{
	if (!CDocument::OnNewDocument())
		return FALSE;

	// TODO: 在此添加重新初始化代码
	// (SDI 文档将重用该文档)

	return TRUE;
}




// C仿真与设计第三次作业刘振毫2312167Doc 序列化

void C仿真与设计第三次作业刘振毫2312167Doc::Serialize(CArchive& ar)
{
	if (ar.IsStoring())
	{
		// TODO: 在此添加存储代码
	}
	else
	{
		// TODO: 在此添加加载代码
	}
}

#ifdef SHARED_HANDLERS

// 缩略图的支持
void C仿真与设计第三次作业刘振毫2312167Doc::OnDrawThumbnail(CDC& dc, LPRECT lprcBounds)
{
	// 修改此代码以绘制文档数据
	dc.FillSolidRect(lprcBounds, RGB(255, 255, 255));

	CString strText = _T("TODO: implement thumbnail drawing here");
	LOGFONT lf;

	CFont* pDefaultGUIFont = CFont::FromHandle((HFONT) GetStockObject(DEFAULT_GUI_FONT));
	pDefaultGUIFont->GetLogFont(&lf);
	lf.lfHeight = 36;

	CFont fontDraw;
	fontDraw.CreateFontIndirect(&lf);

	CFont* pOldFont = dc.SelectObject(&fontDraw);
	dc.DrawText(strText, lprcBounds, DT_CENTER | DT_WORDBREAK);
	dc.SelectObject(pOldFont);
}

// 搜索处理程序的支持
void C仿真与设计第三次作业刘振毫2312167Doc::InitializeSearchContent()
{
	CString strSearchContent;
	// 从文档数据设置搜索内容。
	// 内容部分应由“;”分隔

	// 例如:     strSearchContent = _T("point;rectangle;circle;ole object;")；
	SetSearchContent(strSearchContent);
}

void C仿真与设计第三次作业刘振毫2312167Doc::SetSearchContent(const CString& value)
{
	if (value.IsEmpty())
	{
		RemoveChunk(PKEY_Search_Contents.fmtid, PKEY_Search_Contents.pid);
	}
	else
	{
		CMFCFilterChunkValueImpl *pChunk = nullptr;
		ATLTRY(pChunk = new CMFCFilterChunkValueImpl);
		if (pChunk != nullptr)
		{
			pChunk->SetTextValue(PKEY_Search_Contents, value, CHUNK_TEXT);
			SetChunkValue(pChunk);
		}
	}
}

#endif // SHARED_HANDLERS

// C仿真与设计第三次作业刘振毫2312167Doc 诊断

#ifdef _DEBUG
void C仿真与设计第三次作业刘振毫2312167Doc::AssertValid() const
{
	CDocument::AssertValid();
}

void C仿真与设计第三次作业刘振毫2312167Doc::Dump(CDumpContext& dc) const
{
	CDocument::Dump(dc);
}
#endif //_DEBUG


// C仿真与设计第三次作业刘振毫2312167Doc 命令
