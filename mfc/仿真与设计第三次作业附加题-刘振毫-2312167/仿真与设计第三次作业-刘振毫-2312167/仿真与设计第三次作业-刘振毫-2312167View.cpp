
// 仿真与设计第三次作业-刘振毫-2312167View.cpp: C仿真与设计第三次作业刘振毫2312167View 类的实现
//

#include "pch.h"
#include "framework.h"
// SHARED_HANDLERS 可以在实现预览、缩略图和搜索筛选器句柄的
// ATL 项目中进行定义，并允许与该项目共享文档代码。
#ifndef SHARED_HANDLERS
#include "仿真与设计第三次作业-刘振毫-2312167.h"
#endif

#include "仿真与设计第三次作业-刘振毫-2312167Doc.h"
#include "仿真与设计第三次作业-刘振毫-2312167View.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif


// C仿真与设计第三次作业刘振毫2312167View

IMPLEMENT_DYNCREATE(C仿真与设计第三次作业刘振毫2312167View, CView)

BEGIN_MESSAGE_MAP(C仿真与设计第三次作业刘振毫2312167View, CView)
	// 标准打印命令
	ON_COMMAND(ID_FILE_PRINT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_DIRECT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_PREVIEW, &CView::OnFilePrintPreview)
END_MESSAGE_MAP()

// C仿真与设计第三次作业刘振毫2312167View 构造/析构

C仿真与设计第三次作业刘振毫2312167View::C仿真与设计第三次作业刘振毫2312167View() noexcept
{
	// TODO: 在此处添加构造代码

}

C仿真与设计第三次作业刘振毫2312167View::~C仿真与设计第三次作业刘振毫2312167View()
{
}

BOOL C仿真与设计第三次作业刘振毫2312167View::PreCreateWindow(CREATESTRUCT& cs)
{
	// TODO: 在此处通过修改
	//  CREATESTRUCT cs 来修改窗口类或样式

	return CView::PreCreateWindow(cs);
}

// C仿真与设计第三次作业刘振毫2312167View 绘图

void C仿真与设计第三次作业刘振毫2312167View::OnDraw(CDC* pDC)
{
	C仿真与设计第三次作业刘振毫2312167Doc* pDoc = GetDocument();
	ASSERT_VALID(pDoc);
	if (!pDoc)
		return;

	if (!pDoc->m_bDraw)
		return;

	int x1 = pDoc->m_ptTopLeft.x;
	int y1 = pDoc->m_ptTopLeft.y;
	int x2 = pDoc->m_ptBottomRight.x;
	int y2 = pDoc->m_ptBottomRight.y;

	int left   = min(x1, x2);
	int top    = min(y1, y2);
	int right  = max(x1, x2);
	int bottom = max(y1, y2);

	int penStyles[] = { PS_SOLID, PS_DASH, PS_DASHDOT };
	int nPenStyle = penStyles[pDoc->m_nLineStyle];

	LOGBRUSH lb;
	lb.lbStyle = BS_SOLID;
	lb.lbColor = pDoc->m_color;
	lb.lbHatch = 0;

	CPen pen;
	pen.Attach(::ExtCreatePen(PS_GEOMETRIC | nPenStyle | PS_ENDCAP_ROUND | PS_JOIN_ROUND, 3, &lb, 0, nullptr));
	CPen* pOldPen = pDC->SelectObject(&pen);
	CBrush* pOldBrush = (CBrush*)pDC->SelectStockObject(NULL_BRUSH);

	if (pDoc->m_nShapeType == 0) // 矩形
	{
		pDC->Rectangle(left, top, right, bottom);
	}
	else if (pDoc->m_nShapeType == 1) // 椭圆
	{
		pDC->Ellipse(left, top, right, bottom);
	}
	else if (pDoc->m_nShapeType == 2) // 直线
	{
		pDC->MoveTo(x1, y1);
		pDC->LineTo(x2, y2);
	}

	pDC->SelectObject(pOldPen);
	pDC->SelectObject(pOldBrush);

	// 在图形正下方标注图形类型及RGB颜色值
	CString strShape;
	if (pDoc->m_nShapeType == 0)
		strShape = _T("矩形");
	else if (pDoc->m_nShapeType == 1)
		strShape = _T("椭圆");
	else
		strShape = _T("直线");

	int r = GetRValue(pDoc->m_color);
	int g = GetGValue(pDoc->m_color);
	int b = GetBValue(pDoc->m_color);

	CString strLabel;
	strLabel.Format(_T("%s  RGB(%d, %d, %d)"), (LPCTSTR)strShape, r, g, b);

	int textX, textY;
	if (pDoc->m_nShapeType == 2)
	{
		textX = (x1 + x2) / 2;
		textY = max(y1, y2) + 20;
	}
	else
	{
		textX = (left + right) / 2;
		textY = bottom + 10;
	}

	pDC->SetTextAlign(TA_CENTER | TA_TOP);
	pDC->SetBkMode(TRANSPARENT);
	pDC->TextOut(textX, textY, strLabel);
}


// C仿真与设计第三次作业刘振毫2312167View 打印

BOOL C仿真与设计第三次作业刘振毫2312167View::OnPreparePrinting(CPrintInfo* pInfo)
{
	// 默认准备
	return DoPreparePrinting(pInfo);
}

void C仿真与设计第三次作业刘振毫2312167View::OnBeginPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: 添加额外的打印前进行的初始化过程
}

void C仿真与设计第三次作业刘振毫2312167View::OnEndPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: 添加打印后进行的清理过程
}


// C仿真与设计第三次作业刘振毫2312167View 诊断

#ifdef _DEBUG
void C仿真与设计第三次作业刘振毫2312167View::AssertValid() const
{
	CView::AssertValid();
}

void C仿真与设计第三次作业刘振毫2312167View::Dump(CDumpContext& dc) const
{
	CView::Dump(dc);
}

C仿真与设计第三次作业刘振毫2312167Doc* C仿真与设计第三次作业刘振毫2312167View::GetDocument() const // 非调试版本是内联的
{
	ASSERT(m_pDocument->IsKindOf(RUNTIME_CLASS(C仿真与设计第三次作业刘振毫2312167Doc)));
	return (C仿真与设计第三次作业刘振毫2312167Doc*)m_pDocument;
}
#endif //_DEBUG


// C仿真与设计第三次作业刘振毫2312167View 消息处理程序
