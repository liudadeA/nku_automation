
// 26.4.20.shangji2View.cpp: CMy26420shangji2View 类的实现
//

#include "pch.h"
#include "framework.h"
// SHARED_HANDLERS 可以在实现预览、缩略图和搜索筛选器句柄的
// ATL 项目中进行定义，并允许与该项目共享文档代码。
#ifndef SHARED_HANDLERS
#include "26.4.20.shangji2.h"
#endif

#include "26.4.20.shangji2Doc.h"
#include "26.4.20.shangji2View.h"
#include <cmath>

#ifdef _DEBUG
#define new DEBUG_NEW
#endif


// CMy26420shangji2View

IMPLEMENT_DYNCREATE(CMy26420shangji2View, CView)

BEGIN_MESSAGE_MAP(CMy26420shangji2View, CView)
	// 标准打印命令
	ON_COMMAND(ID_FILE_PRINT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_DIRECT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_PREVIEW, &CView::OnFilePrintPreview)
    ON_WM_TIMER()
	ON_COMMAND(ID_WM_DIR_CW, &CMy26420shangji2View::OnWmDirCw)
	ON_COMMAND(ID_WM_DIR_CCW, &CMy26420shangji2View::OnWmDirCcw)
	ON_COMMAND(ID_WM_SPEED_FASTER, &CMy26420shangji2View::OnWmSpeedFaster)
	ON_COMMAND(ID_WM_SPEED_SLOWER, &CMy26420shangji2View::OnWmSpeedSlower)
	ON_COMMAND(ID_WM_ANIM_START, &CMy26420shangji2View::OnWmAnimStart)
	ON_COMMAND(ID_WM_ANIM_STOP, &CMy26420shangji2View::OnWmAnimStop)
    ON_WM_LBUTTONDOWN()
END_MESSAGE_MAP()

// CMy26420shangji2View 构造/析构

CMy26420shangji2View::CMy26420shangji2View() noexcept
{
	// TODO: 在此处添加构造代码

}

void CMy26420shangji2View::OnInitialUpdate()
{
    CView::OnInitialUpdate();
	// If document already has saved windmill center, restore it; otherwise initialize to client center
	if (auto pDoc = GetDocument())
	{
		if (pDoc->m_wmCenterX == 0.0f && pDoc->m_wmCenterY == 0.0f)
		{
			CRect rc;
			GetClientRect(&rc);
			m_wmCenterX = rc.Width() / 2.0f;
			m_wmCenterY = rc.Height() / 2.0f;
			pDoc->m_wmCenterX = m_wmCenterX;
			pDoc->m_wmCenterY = m_wmCenterY;
		}
		else
		{
			// restore from document
			m_wmCenterX = pDoc->m_wmCenterX;
			m_wmCenterY = pDoc->m_wmCenterY;
			m_wmAngle = pDoc->m_wmAngle;
			m_wmDirection = pDoc->m_wmDirection;
			m_wmSpeed = pDoc->m_wmSpeed;
			m_wmRunning = pDoc->m_wmRunning;
			if (m_wmRunning && m_nTimerID == 0) m_nTimerID = SetTimer(1, 40, nullptr);
		}
	}
}

CMy26420shangji2View::~CMy26420shangji2View()
{
}

BOOL CMy26420shangji2View::PreCreateWindow(CREATESTRUCT& cs)
{
	// TODO: 在此处通过修改
	//  CREATESTRUCT cs 来修改窗口类或样式

	return CView::PreCreateWindow(cs);
}

// CMy26420shangji2View 绘图

void CMy26420shangji2View::OnDraw(CDC* pDC)
{
	CMy26420shangji2Doc* pDoc = GetDocument();
	ASSERT_VALID(pDoc);
	if (!pDoc)
		return;

	// initialize from document once
	if (m_wmCenterX == 0 && m_wmCenterY == 0)
	{
		m_wmCenterX = pDoc->m_wmCenterX;
		m_wmCenterY = pDoc->m_wmCenterY;
		m_wmAngle = pDoc->m_wmAngle;
		m_wmDirection = pDoc->m_wmDirection;
		m_wmSpeed = pDoc->m_wmSpeed;
		m_wmRunning = pDoc->m_wmRunning;
		if (m_wmRunning && m_nTimerID == 0) m_nTimerID = SetTimer(1, 40, nullptr);
	}

	CRect rc;
	GetClientRect(&rc);

	CDC memDC;
	memDC.CreateCompatibleDC(pDC);
	CBitmap bmp;
	bmp.CreateCompatibleBitmap(pDC, rc.Width(), rc.Height());
	CBitmap* pOldBmp = memDC.SelectObject(&bmp);

	memDC.FillSolidRect(&rc, RGB(255,255,255));

	int bladeLen = min(rc.Width(), rc.Height()) / 5;
	int bladeWid = bladeLen / 2;

	// draw 4 blades
	for (int i = 0; i < 4; i++)
	{
		double a = (m_wmAngle + i * 90.0) * 3.14159265358979323846 / 180.0;
		double cosA = cos(a), sinA = sin(a);
		POINT poly[3];
        // triangular blade: base near center (two points), tip outward
		double inner = max(10, bladeLen / 5); // base distance from center
		double x1 = inner, y1 = -bladeWid/2.0;
		double x2 = inner, y2 = bladeWid/2.0;
		double xt = bladeLen, yt = 0;
		poly[0].x = (int)(m_wmCenterX + x1 * cosA - y1 * sinA);
		poly[0].y = (int)(m_wmCenterY + x1 * sinA + y1 * cosA);
		poly[1].x = (int)(m_wmCenterX + x2 * cosA - y2 * sinA);
		poly[1].y = (int)(m_wmCenterY + x2 * sinA + y2 * cosA);
		poly[2].x = (int)(m_wmCenterX + xt * cosA - yt * sinA);
		poly[2].y = (int)(m_wmCenterY + xt * sinA + yt * cosA);
		CBrush brush(RGB(173,216,230));
		CBrush* pOldBrush = memDC.SelectObject(&brush);
		memDC.Polygon(poly, 3);
		memDC.SelectObject(pOldBrush);
	}

	// draw pivot
	int pivot = 10;
	CBrush b2(RGB(169,169,169));
	CBrush* pOldBrush2 = memDC.SelectObject(&b2);
	memDC.Ellipse((int)(m_wmCenterX-pivot), (int)(m_wmCenterY-pivot), (int)(m_wmCenterX+pivot), (int)(m_wmCenterY+pivot));
	memDC.SelectObject(pOldBrush2);

    // draw status text
	CString status;
	status.Format(_T("运行: %s    方向: %s    速度: %.2fdeg/tick    角度: %.1f    中心:(%.0f,%.0f)"),
		m_wmRunning? _T("是") : _T("否"),
		m_wmDirection>0? _T("顺时针") : _T("逆时针"),
		m_wmSpeed, m_wmAngle, m_wmCenterX, m_wmCenterY);
	CFont font;
	font.CreatePointFont(80, _T("Arial"));
	CFont* pOldFont = memDC.SelectObject(&font);
	memDC.SetTextColor(RGB(0,0,0));
	memDC.SetBkMode(TRANSPARENT);
	memDC.TextOutW(10, 10, status);
	memDC.TextOutW(10, 30, _T("快捷键: Alt+C 顺时针  Alt+R 逆时针  Alt+G 加速  Alt+D 减速  Alt+S 开始  Alt+T 停止"));
	memDC.SelectObject(pOldFont);

	pDC->BitBlt(0,0,rc.Width(), rc.Height(), &memDC, 0,0, SRCCOPY);

	memDC.SelectObject(pOldBmp);
}

void CMy26420shangji2View::OnTimer(UINT_PTR nIDEvent)
{
	if (nIDEvent == m_nTimerID && m_wmRunning)
	{
		m_wmAngle += m_wmSpeed * m_wmDirection;
		if (m_wmAngle > 360.0f || m_wmAngle < -360.0f) m_wmAngle = fmod(m_wmAngle, 360.0f);
		// sync to document
		CMy26420shangji2Doc* pDoc = GetDocument();
		if (pDoc)
		{
			pDoc->m_wmAngle = m_wmAngle;
			pDoc->m_wmDirection = m_wmDirection;
			pDoc->m_wmSpeed = m_wmSpeed;
			pDoc->m_wmRunning = m_wmRunning;
			pDoc->m_wmCenterX = m_wmCenterX;
			pDoc->m_wmCenterY = m_wmCenterY;
		}
        Invalidate(FALSE);
	}
	CView::OnTimer(nIDEvent);
}

void CMy26420shangji2View::OnWmDirCw()
{
	m_wmDirection = 1;
	if (auto pDoc = GetDocument()) pDoc->m_wmDirection = m_wmDirection;
}

void CMy26420shangji2View::OnWmDirCcw()
{
	m_wmDirection = -1;
	if (auto pDoc = GetDocument()) pDoc->m_wmDirection = m_wmDirection;
}

void CMy26420shangji2View::OnWmSpeedFaster()
{
	m_wmSpeed = max(0.1f, m_wmSpeed * 1.25f);
	if (auto pDoc = GetDocument()) pDoc->m_wmSpeed = m_wmSpeed;
}

void CMy26420shangji2View::OnWmSpeedSlower()
{
	m_wmSpeed = max(0.1f, m_wmSpeed * 0.8f);
	if (auto pDoc = GetDocument()) pDoc->m_wmSpeed = m_wmSpeed;
}

void CMy26420shangji2View::OnWmAnimStart()
{
	m_wmRunning = true;
	if (m_nTimerID == 0) m_nTimerID = SetTimer(1, 40, nullptr);
	if (auto pDoc = GetDocument()) pDoc->m_wmRunning = m_wmRunning;
}

void CMy26420shangji2View::OnWmAnimStop()
{
	m_wmRunning = false;
	if (m_nTimerID != 0) { KillTimer(m_nTimerID); m_nTimerID = 0; }
	if (auto pDoc = GetDocument()) pDoc->m_wmRunning = m_wmRunning;
}

void CMy26420shangji2View::OnLButtonDown(UINT nFlags, CPoint point)
{
	// move center to clicked point
	m_wmCenterX = (float)point.x;
	m_wmCenterY = (float)point.y;
	if (auto pDoc = GetDocument())
	{
		pDoc->m_wmCenterX = m_wmCenterX;
		pDoc->m_wmCenterY = m_wmCenterY;
	}
    Invalidate(FALSE);
	CView::OnLButtonDown(nFlags, point);
}

BOOL CMy26420shangji2View::OnEraseBkgnd(CDC* pDC)
{
	// prevent background erase to reduce flicker
	return TRUE;
}


// CMy26420shangji2View 打印

BOOL CMy26420shangji2View::OnPreparePrinting(CPrintInfo* pInfo)
{
	// 默认准备
	return DoPreparePrinting(pInfo);
}

void CMy26420shangji2View::OnBeginPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: 添加额外的打印前进行的初始化过程
}

void CMy26420shangji2View::OnEndPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: 添加打印后进行的清理过程
}


// CMy26420shangji2View 诊断

#ifdef _DEBUG
void CMy26420shangji2View::AssertValid() const
{
	CView::AssertValid();
}

void CMy26420shangji2View::Dump(CDumpContext& dc) const
{
	CView::Dump(dc);
}

CMy26420shangji2Doc* CMy26420shangji2View::GetDocument() const // 非调试版本是内联的
{
	ASSERT(m_pDocument->IsKindOf(RUNTIME_CLASS(CMy26420shangji2Doc)));
	return (CMy26420shangji2Doc*)m_pDocument;
}
#endif //_DEBUG


// CMy26420shangji2View 消息处理程序
