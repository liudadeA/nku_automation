
// 2026.4.13View.cpp: CMy2026413View 类的实现
//

#include "pch.h"
#include "framework.h"
// SHARED_HANDLERS 可以在实现预览、缩略图和搜索筛选器句柄的
// ATL 项目中进行定义，并允许与该项目共享文档代码。
#ifndef SHARED_HANDLERS
#include "2026.4.13.h"
#endif

#include "2026.4.13Doc.h"
#include "2026.4.13View.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif


// CMy2026413View

IMPLEMENT_DYNCREATE(CMy2026413View, CView)

BEGIN_MESSAGE_MAP(CMy2026413View, CView)
	// 标准打印命令
	ON_COMMAND(ID_FILE_PRINT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_DIRECT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_PREVIEW, &CMy2026413View::OnFilePrintPreview)
	ON_WM_CONTEXTMENU()
	ON_WM_RBUTTONUP()
END_MESSAGE_MAP()

// CMy2026413View 构造/析构

CMy2026413View::CMy2026413View() noexcept
{
	// TODO: 在此处添加构造代码

}

CMy2026413View::~CMy2026413View()
{
}

BOOL CMy2026413View::PreCreateWindow(CREATESTRUCT& cs)
{
	// TODO: 在此处通过修改
	//  CREATESTRUCT cs 来修改窗口类或样式

	return CView::PreCreateWindow(cs);
}

// CMy2026413View 绘图

void CMy2026413View::OnDraw(CDC* /*pDC*/)
{
	CMy2026413Doc* pDoc = GetDocument();
	ASSERT_VALID(pDoc);
	if (!pDoc)
		return;

	// TODO: 在此处为本机数据添加绘制代码
}


// CMy2026413View 打印


void CMy2026413View::OnFilePrintPreview()
{
#ifndef SHARED_HANDLERS
	AFXPrintPreview(this);
#endif
}

BOOL CMy2026413View::OnPreparePrinting(CPrintInfo* pInfo)
{
	// 默认准备
	return DoPreparePrinting(pInfo);
}

void CMy2026413View::OnBeginPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: 添加额外的打印前进行的初始化过程
}

void CMy2026413View::OnEndPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: 添加打印后进行的清理过程
}

void CMy2026413View::OnRButtonUp(UINT /* nFlags */, CPoint point)
{
	ClientToScreen(&point);
	OnContextMenu(this, point);
}

void CMy2026413View::OnContextMenu(CWnd* /* pWnd */, CPoint point)
{
#ifndef SHARED_HANDLERS
	theApp.GetContextMenuManager()->ShowPopupMenu(IDR_POPUP_EDIT, point.x, point.y, this, TRUE);
#endif
}


// CMy2026413View 诊断

#ifdef _DEBUG
void CMy2026413View::AssertValid() const
{
	CView::AssertValid();
}

void CMy2026413View::Dump(CDumpContext& dc) const
{
	CView::Dump(dc);
}

CMy2026413Doc* CMy2026413View::GetDocument() const // 非调试版本是内联的
{
	ASSERT(m_pDocument->IsKindOf(RUNTIME_CLASS(CMy2026413Doc)));
	return (CMy2026413Doc*)m_pDocument;
}
#endif //_DEBUG


// CMy2026413View 消息处理程序
