
// 26.4.20.shangji2Doc.cpp: CMy26420shangji2Doc 类的实现
//

#include "pch.h"
#include "framework.h"
// SHARED_HANDLERS 可以在实现预览、缩略图和搜索筛选器句柄的
// ATL 项目中进行定义，并允许与该项目共享文档代码。
#ifndef SHARED_HANDLERS
#include "26.4.20.shangji2.h"
#endif

#include "26.4.20.shangji2Doc.h"

#include <propkey.h>

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

// CMy26420shangji2Doc

IMPLEMENT_DYNCREATE(CMy26420shangji2Doc, CDocument)

BEGIN_MESSAGE_MAP(CMy26420shangji2Doc, CDocument)
END_MESSAGE_MAP()


// CMy26420shangji2Doc 构造/析构

CMy26420shangji2Doc::CMy26420shangji2Doc() noexcept
{
	// TODO: 在此添加一次性构造代码

}

CMy26420shangji2Doc::~CMy26420shangji2Doc()
{
}

BOOL CMy26420shangji2Doc::OnNewDocument()
{
	if (!CDocument::OnNewDocument())
		return FALSE;

	// TODO: 在此添加重新初始化代码
	// (SDI 文档将重用该文档)
    SetDefaultWindmillState();

	SetTitle(_T("四叶风车旋转程序"));

	return TRUE;
}




// CMy26420shangji2Doc 序列化

void CMy26420shangji2Doc::Serialize(CArchive& ar)
{
	if (ar.IsStoring())
	{
		// TODO: 在此添加存储代码
        ar << m_wmCenterX << m_wmCenterY << m_wmAngle << m_wmDirection << m_wmSpeed << m_wmRunning;
	}
	else
	{
		// TODO: 在此添加加载代码
        ar >> m_wmCenterX >> m_wmCenterY >> m_wmAngle >> m_wmDirection >> m_wmSpeed >> m_wmRunning;
	}
}

void CMy26420shangji2Doc::SetDefaultWindmillState()
{
	CRect rc;
	if (AfxGetMainWnd()) AfxGetMainWnd()->GetClientRect(&rc);
	m_wmCenterX = rc.Width() / 2.0f;
	m_wmCenterY = rc.Height() / 2.0f;
	m_wmAngle = 0.0f;
	m_wmDirection = 1;
	m_wmSpeed = 5.0f;
	m_wmRunning = false;
}

#ifdef SHARED_HANDLERS

// 缩略图的支持
void CMy26420shangji2Doc::OnDrawThumbnail(CDC& dc, LPRECT lprcBounds)
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
void CMy26420shangji2Doc::InitializeSearchContent()
{
	CString strSearchContent;
	// 从文档数据设置搜索内容。
	// 内容部分应由“;”分隔

	// 例如:     strSearchContent = _T("point;rectangle;circle;ole object;")；
	SetSearchContent(strSearchContent);
}

void CMy26420shangji2Doc::SetSearchContent(const CString& value)
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

// CMy26420shangji2Doc 诊断

#ifdef _DEBUG
void CMy26420shangji2Doc::AssertValid() const
{
	CDocument::AssertValid();
}

void CMy26420shangji2Doc::Dump(CDumpContext& dc) const
{
	CDocument::Dump(dc);
}
#endif //_DEBUG


// CMy26420shangji2Doc 命令
