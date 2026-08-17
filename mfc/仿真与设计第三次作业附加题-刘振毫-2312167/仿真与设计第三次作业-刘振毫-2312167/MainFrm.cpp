
// MainFrm.cpp: CMainFrame 类的实现
//

#include "pch.h"
#include "framework.h"
#include "仿真与设计第三次作业-刘振毫-2312167.h"

#include "MainFrm.h"
#include "仿真与设计第三次作业-刘振毫-2312167Doc.h"
#include "仿真与设计第三次作业-刘振毫-2312167View.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

// CMainFrame

IMPLEMENT_DYNCREATE(CMainFrame, CFrameWnd)

BEGIN_MESSAGE_MAP(CMainFrame, CFrameWnd)
	ON_WM_CREATE()
	ON_WM_SIZE()
END_MESSAGE_MAP()

static UINT indicators[] =
{
	ID_SEPARATOR,           // 状态行指示器
	ID_INDICATOR_CAPS,
	ID_INDICATOR_NUM,
	ID_INDICATOR_SCRL,
};

// CMainFrame 构造/析构

CMainFrame::CMainFrame() noexcept
{
	// TODO: 在此添加成员初始化代码
}

CMainFrame::~CMainFrame()
{
}

int CMainFrame::OnCreate(LPCREATESTRUCT lpCreateStruct)
{
	if (CFrameWnd::OnCreate(lpCreateStruct) == -1)
		return -1;

	if (!m_wndToolBar.CreateEx(this, TBSTYLE_FLAT, WS_CHILD | WS_VISIBLE | CBRS_TOP | CBRS_GRIPPER | CBRS_TOOLTIPS | CBRS_FLYBY | CBRS_SIZE_DYNAMIC) ||
		!m_wndToolBar.LoadToolBar(IDR_MAINFRAME))
	{
		TRACE0("未能创建工具栏\n");
		return -1;      // 未能创建
	}

	if (!m_wndStatusBar.Create(this))
	{
		TRACE0("未能创建状态栏\n");
		return -1;      // 未能创建
	}
	m_wndStatusBar.SetIndicators(indicators, sizeof(indicators)/sizeof(UINT));

	// TODO: 如果不需要可停靠工具栏，则删除这三行
	m_wndToolBar.EnableDocking(CBRS_ALIGN_ANY);
	EnableDocking(CBRS_ALIGN_ANY);
	DockControlBar(&m_wndToolBar);

	// 创建参数面板 — 左侧子窗口
	if (!m_wndParamPanel.Create(_T("STATIC"), _T(""),
		WS_CHILD | WS_VISIBLE | WS_CLIPCHILDREN | WS_CLIPSIBLINGS,
		CRect(0, 0, 260, 500), this, 0))
	{
		TRACE0("未能创建参数面板\n");
		return -1;
	}

	return 0;
}

void CMainFrame::RecalcLayout(BOOL bNotify)
{
	CFrameWnd::RecalcLayout(bNotify);

	const int PANEL_WIDTH = 270;
	if (!::IsWindow(m_wndParamPanel.GetSafeHwnd()))
		return;

	CRect rcFrame;
	GetClientRect(&rcFrame);

	int panelTop = 0;
	if (::IsWindow(m_wndToolBar.GetSafeHwnd()))
	{
		CRect rcTB;
		m_wndToolBar.GetWindowRect(&rcTB);
		ScreenToClient(&rcTB);
		panelTop = rcTB.bottom;
	}

	int panelBottom = rcFrame.bottom;
	if (::IsWindow(m_wndStatusBar.GetSafeHwnd()))
	{
		CRect rcSB;
		m_wndStatusBar.GetWindowRect(&rcSB);
		ScreenToClient(&rcSB);
		panelBottom = rcSB.top;
	}

	m_wndParamPanel.SetWindowPos(nullptr, 0, panelTop,
		PANEL_WIDTH, panelBottom - panelTop,
		SWP_NOZORDER | SWP_NOACTIVATE);

	CWnd* pView = GetDlgItem(AFX_IDW_PANE_FIRST);
	if (pView && ::IsWindow(pView->GetSafeHwnd()))
	{
		pView->SetWindowPos(nullptr, PANEL_WIDTH, panelTop,
			rcFrame.right - PANEL_WIDTH, panelBottom - panelTop,
			SWP_NOZORDER | SWP_NOACTIVATE);
	}
}

void CMainFrame::OnSize(UINT nType, int cx, int cy)
{
	CFrameWnd::OnSize(nType, cx, cy);
	RecalcLayout();
}

BOOL CMainFrame::PreCreateWindow(CREATESTRUCT& cs)
{
	if( !CFrameWnd::PreCreateWindow(cs) )
		return FALSE;
	// TODO: 在此处通过修改
	//  CREATESTRUCT cs 来修改窗口类或样式

	return TRUE;
}

// CMainFrame 诊断

#ifdef _DEBUG
void CMainFrame::AssertValid() const
{
	CFrameWnd::AssertValid();
}

void CMainFrame::Dump(CDumpContext& dc) const
{
	CFrameWnd::Dump(dc);
}
#endif //_DEBUG


// CMainFrame 消息处理程序

