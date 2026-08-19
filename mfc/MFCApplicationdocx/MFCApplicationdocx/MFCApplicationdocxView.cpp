
// MFCApplicationdocxView.cpp: CMFCApplicationdocxView 类的实现
//

#include "pch.h"
#include "framework.h"
// SHARED_HANDLERS 可以在实现预览、缩略图和搜索筛选器句柄的
// ATL 项目中进行定义，并允许与该项目共享文档代码。
#ifndef SHARED_HANDLERS
#include "MFCApplicationdocx.h"
#endif

#include "MFCApplicationdocxDoc.h"
#include "MFCApplicationdocxView.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif


// CMFCApplicationdocxView

IMPLEMENT_DYNCREATE(CMFCApplicationdocxView, CView)

BEGIN_MESSAGE_MAP(CMFCApplicationdocxView, CView)
	// 标准打印命令
	ON_COMMAND(ID_FILE_PRINT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_DIRECT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_PREVIEW, &CMFCApplicationdocxView::OnFilePrintPreview)
	ON_WM_CONTEXTMENU()
	ON_WM_RBUTTONUP()
	ON_WM_LBUTTONDOWN()
	ON_COMMAND(ID_OPT_BLACK, &CMFCApplicationdocxView::OnOptBlack)
	ON_COMMAND(ID_OPT_BLUE, &CMFCApplicationdocxView::OnOptBlue)
	ON_COMMAND(ID_OPT_EMPTY, &CMFCApplicationdocxView::OnOptEmpty)
	ON_COMMAND(ID_OPT_RED, &CMFCApplicationdocxView::OnOptRed)
	ON_COMMAND(ID_OPT_GREEN, &CMFCApplicationdocxView::OnOptGreen)
   ON_UPDATE_COMMAND_UI(ID_OPT_BLACK, &CMFCApplicationdocxView::OnUpdateOptBlack)
	ON_UPDATE_COMMAND_UI(ID_OPT_RED, &CMFCApplicationdocxView::OnUpdateOptRed)
   ON_UPDATE_COMMAND_UI(ID_OPT_BLUE, &CMFCApplicationdocxView::OnUpdateOptBlue)
	ON_UPDATE_COMMAND_UI(ID_OPT_GREEN, &CMFCApplicationdocxView::OnUpdateOptGreen)
END_MESSAGE_MAP()

// CMFCApplicationdocxView 构造/析构

CMFCApplicationdocxView::CMFCApplicationdocxView() noexcept
{
	// TODO: 在此处添加构造代码
	m_nColors[0] = RGB(0, 0, 0);
	m_nColors[1] = RGB(255, 0, 0);
	m_nColors[2] = RGB(0, 255, 0);
	m_nColors[3] = RGB(0, 0, 255);
}

CMFCApplicationdocxView::~CMFCApplicationdocxView()
{
}

BOOL CMFCApplicationdocxView::PreCreateWindow(CREATESTRUCT& cs)
{
	// TODO: 在此处通过修改
	//  CREATESTRUCT cs 来修改窗口类或样式

	return CView::PreCreateWindow(cs);
}




// CMFCApplicationdocxView 绘图

void CMFCApplicationdocxView::OnDraw(CDC* pDC)
{
	CMFCApplicationdocxDoc* pDoc = GetDocument();
	ASSERT_VALID(pDoc);
	if (!pDoc)
		return;

	// TODO: 在此处为本机数据添加绘制代码
	pDC->SetTextColor(m_nColors[pDoc->GetColor()]);

	CPoint pt;
	CString str;
	pDoc->Get(pt, str);
	pDC->TextOut(pt.x, pt.y, str);

}


// CMFCApplicationdocxView 打印


void CMFCApplicationdocxView::OnFilePrintPreview()
{
#ifndef SHARED_HANDLERS
	AFXPrintPreview(this);
#endif
}

BOOL CMFCApplicationdocxView::OnPreparePrinting(CPrintInfo* pInfo)
{
	// 默认准备
	return DoPreparePrinting(pInfo);
}

void CMFCApplicationdocxView::OnBeginPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: 添加额外的打印前进行的初始化过程
}

void CMFCApplicationdocxView::OnEndPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: 添加打印后进行的清理过程
}

void CMFCApplicationdocxView::OnRButtonUp(UINT /* nFlags */, CPoint point)
{
	ClientToScreen(&point);
	OnContextMenu(this, point);
}

void CMFCApplicationdocxView::OnContextMenu(CWnd* /* pWnd */, CPoint point)
{
	// use correct document type
	CMFCApplicationdocxDoc* pDoc = GetDocument();

	CMenu menu;
	// Load the menu resource that exists in resource.h (use IDR_MENU1 which contains the POP entries)
	if (menu.LoadMenu(IDR_MENU1)) {
		CMenu* pPopMenu = menu.GetSubMenu(0);
		if (pPopMenu != nullptr) {
			// 设置单选按钮 based on document color
			pPopMenu->CheckMenuRadioItem(ID_OPT_BLACK, ID_OPT_BLUE,
				ID_OPT_BLACK + pDoc->GetColor(), MF_BYCOMMAND);
			pPopMenu->TrackPopupMenu(TPM_LEFTALIGN | TPM_RIGHTBUTTON, point.x, point.y, this);
		}
	}

#ifndef SHARED_HANDLERS
	theApp.GetContextMenuManager()->ShowPopupMenu(IDR_POPUP_EDIT, point.x, point.y, this, TRUE);
#endif
}


// CMFCApplicationdocxView 诊断

#ifdef _DEBUG
void CMFCApplicationdocxView::AssertValid() const
{
	CView::AssertValid();
}

void CMFCApplicationdocxView::Dump(CDumpContext& dc) const
{
	CView::Dump(dc);
}

CMFCApplicationdocxDoc* CMFCApplicationdocxView::GetDocument() const // 非调试版本是内联的
{
	ASSERT(m_pDocument->IsKindOf(RUNTIME_CLASS(CMFCApplicationdocxDoc)));
	return (CMFCApplicationdocxDoc*)m_pDocument;
}
#endif //_DEBUG


// CMFCApplicationdocxView 消息处理程序

void CMFCApplicationdocxView::OnLButtonDown(UINT nFlags, CPoint point)
{
	// TODO: 在此添加消息处理程序代码和/或调用默认值
	CMFCApplicationdocxDoc* pDoc = GetDocument();
	CString str;
	str.Format(_T("鼠标单击位置：(%d,%d)"), point.x, point.y);
	pDoc->Set(point, str);
	Invalidate();
	CView::OnLButtonDown(nFlags, point);
}

void CMFCApplicationdocxView::OnOptBlack()
{
	// TODO: 在此添加命令处理程序代码
    CMFCApplicationdocxDoc* pDoc = GetDocument();
	pDoc->SetColor(0);
	pDoc->UpdateAllViews(NULL);
}

void CMFCApplicationdocxView::OnOptBlue()
{
	// TODO: 在此添加命令处理程序代码
    CMFCApplicationdocxDoc* pDoc = GetDocument();
	pDoc->SetColor(3);
	pDoc->UpdateAllViews(NULL);
}

void CMFCApplicationdocxView::OnOptEmpty()
{
	// TODO: 在此添加命令处理程序代码
    CMFCApplicationdocxDoc* pDoc = GetDocument();
	pDoc->Set(CPoint(0,0), _T(""));
	pDoc->UpdateAllViews(NULL);
}

void CMFCApplicationdocxView::OnUpdateOptBlack(CCmdUI* pCmdUI) {
	CMFCApplicationdocxDoc* pDoc = GetDocument();
	pCmdUI->SetRadio(pDoc->GetColor() == 0);
}

void CMFCApplicationdocxView::OnUpdateOptRed(CCmdUI* pCmdUI) {
	CMFCApplicationdocxDoc* pDoc = GetDocument();
	pCmdUI->SetRadio(pDoc->GetColor() == 1);
}

void CMFCApplicationdocxView::OnUpdateOptBlue(CCmdUI* pCmdUI) {
	CMFCApplicationdocxDoc* pDoc = GetDocument();
	pCmdUI->SetRadio(pDoc->GetColor() == 3);
}

void CMFCApplicationdocxView::OnUpdateOptGreen(CCmdUI* pCmdUI) {
	CMFCApplicationdocxDoc* pDoc = GetDocument();
	pCmdUI->SetRadio(pDoc->GetColor() == 2);
}


void CMFCApplicationdocxView::OnOptRed()
{
	// TODO: 在此添加命令处理程序代码
}

void CMFCApplicationdocxView::OnOptGreen()
{
	// TODO: 在此添加命令处理程序代码
}
