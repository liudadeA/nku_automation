
// 26.4.20.shangji3View.cpp: CMy26420shangji3View 类的实现
//

#include "pch.h"
#include "framework.h"
// SHARED_HANDLERS 可以在实现预览、缩略图和搜索筛选器句柄的
// ATL 项目中进行定义，并允许与该项目共享文档代码。
#ifndef SHARED_HANDLERS
#include "26.4.20.shangji3.h"
#endif

#include "26.4.20.shangji3Doc.h"
#include "26.4.20.shangji3View.h"
#include "MainFrm.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif


// CMy26420shangji3View

IMPLEMENT_DYNCREATE(CMy26420shangji3View, CView)

BEGIN_MESSAGE_MAP(CMy26420shangji3View, CView)
	// 标准打印命令
	ON_COMMAND(ID_FILE_PRINT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_DIRECT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_PREVIEW, &CView::OnFilePrintPreview)
    ON_WM_LBUTTONDOWN()
	ON_WM_ERASEBKGND()
END_MESSAGE_MAP()

// CMy26420shangji3View 构造/析构

CMy26420shangji3View::CMy26420shangji3View() noexcept
{
	// TODO: 在此处添加构造代码
	m_dispW = m_dispH = 0;
	m_bShowWarn = false;

}

CMy26420shangji3View::~CMy26420shangji3View()
{
}

BOOL CMy26420shangji3View::PreCreateWindow(CREATESTRUCT& cs)
{
	// TODO: 在此处通过修改
	//  CREATESTRUCT cs 来修改窗口类或样式

	return CView::PreCreateWindow(cs);
}

// CMy26420shangji3View 绘图

void CMy26420shangji3View::OnDraw(CDC* /*pDC*/)
{
	CMy26420shangji3Doc* pDoc = GetDocument();
	ASSERT_VALID(pDoc);
	if (!pDoc)
		return;
	CClientDC dc(this);
	CRect rc;
	GetClientRect(&rc);

	// 背景
	dc.FillSolidRect(&rc, GetSysColor(COLOR_WINDOW));


	if (m_image.IsNull())
		return;

	// 计算中心位置
	int x = (rc.Width() - m_dispW) / 2;
	int y = (rc.Height() - m_dispH) / 2;

	// 使用 CImage 绘制并缩放
	dc.SetStretchBltMode(HALFTONE);
	m_image.Draw(dc.GetSafeHdc(), x, y, m_dispW, m_dispH);

	if (m_bShowWarn)
	{
		CString msg = _T("不要再放大了");
		CRect textRc(0, 0, rc.Width(), 30);
		dc.SetBkMode(TRANSPARENT);
		dc.SetTextColor(RGB(255, 0, 0));
		dc.DrawText(msg, &textRc, DT_CENTER | DT_VCENTER);
	}
}

void CMy26420shangji3View::OnInitialUpdate()
{
	CView::OnInitialUpdate();

    // 加载 PNG 图片文件（位于 res\南开大学.png）
	m_bShowWarn = false;

	// 尝试从可执行目录下的 res 子目录加载图片
	TCHAR szModule[MAX_PATH];
	::GetModuleFileName(nullptr, szModule, MAX_PATH);
	CString exePath = szModule;
	int p = exePath.ReverseFind('\\');
	if (p != -1) exePath = exePath.Left(p+1);
	CString imgPath = exePath + _T("res\\南开大学.png");

	HRESULT hr = m_image.Load(imgPath);
	if (FAILED(hr) || m_image.IsNull())
	{
		// 退而求其次，尝试相对路径 res\南开大学.png
		imgPath = _T("res\\南开大学.png");
		hr = m_image.Load(imgPath);
	}

	if (m_image.IsNull())
		return;

	// 初始显示尺寸为图片原始像素尺寸
	m_dispW = m_image.GetWidth();
	m_dispH = m_image.GetHeight();

	int winW = m_dispW * 2; // 客户区宽为位图的2倍 -> 面积为位图的4倍
	int winH = m_dispH * 2;

	// 调整主窗口客户区大小
	CMainFrame* pFrame = (CMainFrame*)AfxGetMainWnd();
	if (pFrame && ::IsWindow(pFrame->GetSafeHwnd()))
	{
		CRect rcCurClient, rcCurWindow;
		pFrame->GetClientRect(&rcCurClient);
		pFrame->GetWindowRect(&rcCurWindow);
		int frameW = rcCurWindow.Width() - rcCurClient.Width();
		int frameH = rcCurWindow.Height() - rcCurClient.Height();

		pFrame->SetWindowPos(nullptr, 0,0, winW + frameW, winH + frameH, SWP_NOMOVE | SWP_NOZORDER);
	}
}

void CMy26420shangji3View::OnLButtonDown(UINT nFlags, CPoint point)
{
    // 放大为原来1.2倍
	if (m_image.IsNull())
		return;

	m_bShowWarn = false;

	// 增量
	const double factor = 1.2;
	int newW = (int)(m_dispW * factor);
	int newH = (int)(m_dispH * factor);

	// 获取客户区大小，判断是否到边界
	CRect rc;
	GetClientRect(&rc);

	if (newW > rc.Width() || newH > rc.Height())
	{
		// 达到或超出边界，显示警告，不再放大
		m_bShowWarn = true;
	}
	else
	{
		m_dispW = newW;
		m_dispH = newH;
	}

	Invalidate();

	CView::OnLButtonDown(nFlags, point);
}

BOOL CMy26420shangji3View::OnEraseBkgnd(CDC* pDC)
{
	// 避免默认擦除以减少闪烁，在OnDraw中处理背景
	return TRUE;
}


// CMy26420shangji3View 打印

BOOL CMy26420shangji3View::OnPreparePrinting(CPrintInfo* pInfo)
{
	// 默认准备
	return DoPreparePrinting(pInfo);
}

void CMy26420shangji3View::OnBeginPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: 添加额外的打印前进行的初始化过程
}

void CMy26420shangji3View::OnEndPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: 添加打印后进行的清理过程
}


// CMy26420shangji3View 诊断

#ifdef _DEBUG
void CMy26420shangji3View::AssertValid() const
{
	CView::AssertValid();
}

void CMy26420shangji3View::Dump(CDumpContext& dc) const
{
	CView::Dump(dc);
}

CMy26420shangji3Doc* CMy26420shangji3View::GetDocument() const // 非调试版本是内联的
{
	ASSERT(m_pDocument->IsKindOf(RUNTIME_CLASS(CMy26420shangji3Doc)));
	return (CMy26420shangji3Doc*)m_pDocument;
}
#endif //_DEBUG


// CMy26420shangji3View 消息处理程序
