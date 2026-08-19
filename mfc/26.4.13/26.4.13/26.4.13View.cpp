
// 26.4.13View.cpp: CMy26413View 类的实现
//

#include "pch.h"
#include "framework.h"
// SHARED_HANDLERS 可以在实现预览、缩略图和搜索筛选器句柄的
// ATL 项目中进行定义，并允许与该项目共享文档代码。
#ifndef SHARED_HANDLERS
#include "26.4.13.h"
#endif

#include "26.4.13Doc.h"
#include "26.4.13View.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif


// CMy26413View

IMPLEMENT_DYNCREATE(CMy26413View, CView)

BEGIN_MESSAGE_MAP(CMy26413View, CView)
	// 标准打印命令
	ON_COMMAND(ID_FILE_PRINT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_DIRECT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_PREVIEW, &CView::OnFilePrintPreview)
	ON_WM_LBUTTONDOWN()
END_MESSAGE_MAP()

// CMy26413View 构造/析构

CMy26413View::CMy26413View() noexcept
{
	// TODO: 在此处添加构造代码

}

CMy26413View::~CMy26413View()
{
}

BOOL CMy26413View::PreCreateWindow(CREATESTRUCT& cs)
{
	// TODO: 在此处通过修改
	//  CREATESTRUCT cs 来修改窗口类或样式

	return CView::PreCreateWindow(cs);
}

// CMy26413View 绘图

void CMy26413View::OnDraw(CDC* pDC)
{
	CMy26413Doc* pDoc = GetDocument();
	ASSERT_VALID(pDoc);
	if (!pDoc)
		return;

	// TODO: 在此处为本机数据添加绘制代码
	pDC->TextOutW(100, 100, _T("Hello, MFC!"));
}


// CMy26413View 打印

BOOL CMy26413View::OnPreparePrinting(CPrintInfo* pInfo)
{
	// 默认准备
	return DoPreparePrinting(pInfo);
}

void CMy26413View::OnBeginPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: 添加额外的打印前进行的初始化过程
}

void CMy26413View::OnEndPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: 添加打印后进行的清理过程
}


// CMy26413View 诊断

#ifdef _DEBUG
void CMy26413View::AssertValid() const
{
	CView::AssertValid();
}

void CMy26413View::Dump(CDumpContext& dc) const
{
	CView::Dump(dc);
}

CMy26413Doc* CMy26413View::GetDocument() const // 非调试版本是内联的
{
	ASSERT(m_pDocument->IsKindOf(RUNTIME_CLASS(CMy26413Doc)));
	return (CMy26413Doc*)m_pDocument;
}
#endif //_DEBUG


// CMy26413View 消息处理程序

void CMy26413View::OnLButtonDown(UINT nFlags, CPoint point)
{
	// TODO: 在此添加消息处理程序代码和/或调用默认值

	CView::OnLButtonDown(nFlags, point);
	
	CString str;
	//str.Format(_T("鼠标左键单击了坐标(%d, %d)"), point.x, point.y);
	str.Format(TEXT("鼠标左键单击了坐标(%d, %d)"), point.x, point.y);
	MessageBox(str);
}
