
// 26.5.18View.cpp: CMy26518View 类的实现
//

#include "pch.h"
#include "framework.h"
#ifndef SHARED_HANDLERS
#include "26.5.18.h"
#endif

#include "26.5.18Doc.h"
#include "26.5.18View.h"
#include "SloganDlg.h"
#include <atlimage.h>

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

#define ID_TIMER_SCROLL 1

// CMy26518View

IMPLEMENT_DYNCREATE(CMy26518View, CView)

BEGIN_MESSAGE_MAP(CMy26518View, CView)
	ON_COMMAND(ID_FILE_PRINT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_DIRECT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_PREVIEW, &CView::OnFilePrintPreview)
	ON_COMMAND(ID_SET_SLOGAN, &CMy26518View::OnSetSlogan)
	ON_WM_TIMER()
	ON_WM_LBUTTONDBLCLK()
	ON_WM_ERASEBKGND()
END_MESSAGE_MAP()

// CMy26518View 构造/析构

CMy26518View::CMy26518View() noexcept
{
	m_nScrollOffset = 0;
	m_nTimerID = 0;
}

CMy26518View::~CMy26518View()
{
	if (m_fontSlogan.GetSafeHandle())
		m_fontSlogan.DeleteObject();
	if (m_nTimerID != 0)
		KillTimer(m_nTimerID);
	m_imgBg.Destroy();
}

BOOL CMy26518View::PreCreateWindow(CREATESTRUCT& cs)
{
	return CView::PreCreateWindow(cs);
}

void CMy26518View::OnInitialUpdate()
{
	CView::OnInitialUpdate();
	ApplySloganSettings();
}

void CMy26518View::ApplySloganSettings()
{
	CMy26518Doc* pDoc = GetDocument();
	if (!pDoc)
		return;

	if (m_nTimerID != 0)
	{
		KillTimer(m_nTimerID);
		m_nTimerID = 0;
	}

	if (m_fontSlogan.GetSafeHandle())
		m_fontSlogan.DeleteObject();

	m_fontSlogan.CreateFontIndirect(&pDoc->GetLogFont());

	m_imgBg.Destroy();
	CString strBg = pDoc->GetBgImage();
	if (!strBg.IsEmpty() && GetFileAttributes(strBg) != INVALID_FILE_ATTRIBUTES)
	{
		m_imgBg.Load(strBg);
	}

	m_nScrollOffset = 0;

	if (pDoc->IsScrollEnabled())
	{
		m_nTimerID = SetTimer(ID_TIMER_SCROLL, pDoc->GetScrollInterval(), nullptr);
	}

	Invalidate();
}

BOOL CMy26518View::OnEraseBkgnd(CDC* pDC)
{
	return TRUE;
}

// CMy26518View 绘图

void CMy26518View::OnDraw(CDC* pDC)
{
	CMy26518Doc* pDoc = GetDocument();
	ASSERT_VALID(pDoc);
	if (!pDoc)
		return;

	CRect rect;
	GetClientRect(&rect);

	CDC dcMem;
	dcMem.CreateCompatibleDC(pDC);
	CBitmap bmpMem;
	bmpMem.CreateCompatibleBitmap(pDC, rect.Width(), rect.Height());
	CBitmap* pOldBmp = dcMem.SelectObject(&bmpMem);

	if (!m_imgBg.IsNull())
	{
		m_imgBg.StretchBlt(dcMem.GetSafeHdc(), 0, 0, rect.Width(), rect.Height(),
			0, 0, m_imgBg.GetWidth(), m_imgBg.GetHeight(), SRCCOPY);
	}
	else
	{
		dcMem.FillSolidRect(&rect, RGB(240, 240, 255));
	}

	CFont* pOldFont = dcMem.SelectObject(&m_fontSlogan);
	dcMem.SetTextColor(pDoc->GetTextColor());
	dcMem.SetBkMode(TRANSPARENT);

	int nVPos = pDoc->GetVerticalPos();
	int nAlign = pDoc->GetAlignment();
	CString strText = pDoc->GetSloganText();

	CRect textRect;
	if (pDoc->IsScrollEnabled())
	{
		int nTextWidth = rect.Width();
		textRect.SetRect(m_nScrollOffset, nVPos, m_nScrollOffset + rect.Width() + 2000, nVPos + 500);
	}
	else
	{
		textRect.SetRect(0, nVPos, rect.Width(), nVPos + 500);
	}

	UINT nFormat = DT_TOP | DT_SINGLELINE;
	switch (nAlign)
	{
	case 0: nFormat |= DT_LEFT; break;
	case 1: nFormat |= DT_CENTER; break;
	case 2: nFormat |= DT_RIGHT; break;
	default: nFormat |= DT_CENTER; break;
	}

	dcMem.DrawText(strText, &textRect, nFormat);

	dcMem.SelectObject(pOldFont);

	pDC->BitBlt(0, 0, rect.Width(), rect.Height(), &dcMem, 0, 0, SRCCOPY);

	dcMem.SelectObject(pOldBmp);
}

// CMy26518View 打印

BOOL CMy26518View::OnPreparePrinting(CPrintInfo* pInfo)
{
	return DoPreparePrinting(pInfo);
}

void CMy26518View::OnBeginPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
}

void CMy26518View::OnEndPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
}

// CMy26518View 消息处理程序

void CMy26518View::OnSetSlogan()
{
	CMy26518Doc* pDoc = GetDocument();
	if (!pDoc)
		return;

	CSloganDlg dlg(this);

	dlg.m_strSlogan = pDoc->GetSloganText();
	dlg.m_lf = pDoc->GetLogFont();
	dlg.m_color = pDoc->GetTextColor();
	dlg.m_nAlign = pDoc->GetAlignment();
	dlg.m_nVerticalPos = pDoc->GetVerticalPos();
	dlg.m_strBgImage = pDoc->GetBgImage();
	dlg.m_bScroll = pDoc->IsScrollEnabled();
	dlg.m_nScrollInterval = pDoc->GetScrollInterval();

	if (dlg.DoModal() == IDOK)
	{
		pDoc->SetSloganText(dlg.m_strSlogan);
		pDoc->SetLogFont(dlg.m_lf);
		pDoc->SetTextColor(dlg.m_color);
		pDoc->SetAlignment(dlg.m_nAlign);
		pDoc->SetVerticalPos(dlg.m_nVerticalPos);
		pDoc->SetBgImage(dlg.m_strBgImage);
		pDoc->SetScrollEnabled(dlg.m_bScroll);
		pDoc->SetScrollInterval(dlg.m_nScrollInterval);

		pDoc->SetModifiedFlag(TRUE);
		ApplySloganSettings();
	}
}

void CMy26518View::OnLButtonDblClk(UINT nFlags, CPoint point)
{
	OnSetSlogan();
	CView::OnLButtonDblClk(nFlags, point);
}

void CMy26518View::OnTimer(UINT_PTR nIDEvent)
{
	if (nIDEvent == ID_TIMER_SCROLL)
	{
		CRect rect;
		GetClientRect(&rect);
		m_nScrollOffset -= 2;
		if (m_nScrollOffset < -rect.Width())
			m_nScrollOffset = rect.Width();
		Invalidate();
	}

	CView::OnTimer(nIDEvent);
}

// CMy26518View 诊断

#ifdef _DEBUG
void CMy26518View::AssertValid() const
{
	CView::AssertValid();
}

void CMy26518View::Dump(CDumpContext& dc) const
{
	CView::Dump(dc);
}

CMy26518Doc* CMy26518View::GetDocument() const // 非调试版本是内联的
{
	ASSERT(m_pDocument->IsKindOf(RUNTIME_CLASS(CMy26518Doc)));
	return (CMy26518Doc*)m_pDocument;
}
#endif //_DEBUG
