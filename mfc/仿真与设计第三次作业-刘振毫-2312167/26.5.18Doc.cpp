
// 26.5.18Doc.cpp: CMy26518Doc 类的实现
//

#include "pch.h"
#include "framework.h"
// SHARED_HANDLERS 可以在实现预览、缩略图和搜索筛选器句柄的
// ATL 项目中进行定义，并允许与该项目共享文档代码。
#ifndef SHARED_HANDLERS
#include "26.5.18.h"
#endif

#include "26.5.18Doc.h"

#include <propkey.h>

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

// CMy26518Doc

IMPLEMENT_DYNCREATE(CMy26518Doc, CDocument)

BEGIN_MESSAGE_MAP(CMy26518Doc, CDocument)
END_MESSAGE_MAP()


// CMy26518Doc 构造/析构

CMy26518Doc::CMy26518Doc() noexcept
{
	m_strSlogan = _T("相信自己");
	memset(&m_lfSlogan, 0, sizeof(m_lfSlogan));
	m_lfSlogan.lfHeight = -48;
	m_lfSlogan.lfWeight = FW_NORMAL;
	m_lfSlogan.lfCharSet = DEFAULT_CHARSET;
	m_lfSlogan.lfQuality = CLEARTYPE_QUALITY;
	_tcscpy_s(m_lfSlogan.lfFaceName, LF_FACESIZE, _T("微软雅黑"));
	m_colorSlogan = RGB(255, 50, 50);
	m_nAlign = 1;
	m_nVerticalPos = 100;
	m_strBgImage = _T("");
	m_bScroll = FALSE;
	m_nScrollInterval = 50;
}

CMy26518Doc::~CMy26518Doc()
{
}

BOOL CMy26518Doc::OnNewDocument()
{
	if (!CDocument::OnNewDocument())
		return FALSE;

	m_strSlogan = _T("相信自己");
	memset(&m_lfSlogan, 0, sizeof(m_lfSlogan));
	m_lfSlogan.lfHeight = -48;
	m_lfSlogan.lfWeight = FW_NORMAL;
	m_lfSlogan.lfCharSet = DEFAULT_CHARSET;
	m_lfSlogan.lfQuality = CLEARTYPE_QUALITY;
	_tcscpy_s(m_lfSlogan.lfFaceName, LF_FACESIZE, _T("微软雅黑"));
	m_colorSlogan = RGB(255, 50, 50);
	m_nAlign = 1;
	m_nVerticalPos = 100;
	m_strBgImage = _T("");
	m_bScroll = FALSE;
	m_nScrollInterval = 50;

	return TRUE;
}

// CMy26518Doc 序列化

void CMy26518Doc::Serialize(CArchive& ar)
{
	if (ar.IsStoring())
	{
		ar << m_strSlogan;
		ar.Write(&m_lfSlogan, sizeof(LOGFONT));
		ar << m_colorSlogan;
		ar << m_nAlign;
		ar << m_nVerticalPos;
		ar << m_strBgImage;
		ar << m_bScroll;
		ar << m_nScrollInterval;
	}
	else
	{
		ar >> m_strSlogan;
		ar.Read(&m_lfSlogan, sizeof(LOGFONT));
		ar >> m_colorSlogan;
		ar >> m_nAlign;
		ar >> m_nVerticalPos;
		ar >> m_strBgImage;
		ar >> m_bScroll;
		ar >> m_nScrollInterval;
	}
}

#ifdef SHARED_HANDLERS

// 缩略图的支持
void CMy26518Doc::OnDrawThumbnail(CDC& dc, LPRECT lprcBounds)
{
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
void CMy26518Doc::InitializeSearchContent()
{
	CString strSearchContent;
	SetSearchContent(strSearchContent);
}

void CMy26518Doc::SetSearchContent(const CString& value)
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

// CMy26518Doc 诊断

#ifdef _DEBUG
void CMy26518Doc::AssertValid() const
{
	CDocument::AssertValid();
}

void CMy26518Doc::Dump(CDumpContext& dc) const
{
	CDocument::Dump(dc);
}
#endif //_DEBUG
