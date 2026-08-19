
// MFCApplication2View.cpp: CMFCApplication2View 类的实现
//

#include "pch.h"
#include "framework.h"
// SHARED_HANDLERS 可以在实现预览、缩略图和搜索筛选器句柄的
// ATL 项目中进行定义，并允许与该项目共享文档代码。
#ifndef SHARED_HANDLERS
#include "MFCApplication2.h"
#endif

#include "MFCApplication2Doc.h"
#include "MFCApplication2View.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif


// CMFCApplication2View

IMPLEMENT_DYNCREATE(CMFCApplication2View, CView)

BEGIN_MESSAGE_MAP(CMFCApplication2View, CView)
	// 标准打印命令
	ON_COMMAND(ID_FILE_PRINT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_DIRECT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_PREVIEW, &CView::OnFilePrintPreview)
END_MESSAGE_MAP()

// CMFCApplication2View 构造/析构

CMFCApplication2View::CMFCApplication2View() noexcept
{
	// TODO: 在此处添加构造代码

}

CMFCApplication2View::~CMFCApplication2View()
{
}

BOOL CMFCApplication2View::PreCreateWindow(CREATESTRUCT& cs)
{
	// TODO: 在此处通过修改
	//  CREATESTRUCT cs 来修改窗口类或样式

	return CView::PreCreateWindow(cs);
}

// CMFCApplication2View 绘图

void CMFCApplication2View::OnDraw(CDC* pDC)
{
	CMFCApplication2Doc* pDoc = GetDocument();
	ASSERT_VALID(pDoc);
	if (!pDoc)
		return;

	// 计算窗口中心
	CRect clientRect;
	GetClientRect(&clientRect);
	CPoint center = clientRect.CenterPoint();

	// 花瓣参数: 长轴 240, 短轴 80
	const int major = 240;
	const int minor = 80;
	// 花心半径 20
	const int centerR = 20;

    // 四种笔样式和四种阴影画刷
	int penStyles[4] = { PS_SOLID,PS_DASHDOT , PS_DOT ,PS_DASH };
	int hatchStyles[4] = { HS_DIAGCROSS,HS_BDIAGONAL ,HS_CROSS  ,HS_FDIAGONAL };

	// 创建画刷并绘制四个叶片
	CBrush brushes[4];
	CPen outlinePens[4];
	for (int i = 0; i < 4; ++i)
	{
		brushes[i].CreateHatchBrush(hatchStyles[i], RGB(0, 180, 0));
		outlinePens[i].CreatePen(penStyles[i], 1.5, RGB(0, 0, 0));

		CRect rc;
		switch (i)
		{
		case 0: // 上
			rc.left = center.x - minor / 2;
			rc.right = center.x + minor / 2;
			rc.top = center.y - major;
			rc.bottom = center.y;
			break;
		case 1: // 右
			rc.left = center.x;
			rc.right = center.x + major;
			rc.top = center.y - minor / 2;
			rc.bottom = center.y + minor / 2;
			break;
		case 2: // 下
			rc.left = center.x - minor / 2;
			rc.right = center.x + minor / 2;
			rc.top = center.y;
			rc.bottom = center.y + major;
			break;
		default: // 左
			rc.left = center.x - major;
			rc.right = center.x;
			rc.top = center.y - minor / 2;
			rc.bottom = center.y + minor / 2;
			break;
		}

        // 先用阴影画刷填充叶片
		CBrush* pOldBrush = pDC->SelectObject(&brushes[i]);
		pDC->Ellipse(&rc);
		pDC->SelectObject(pOldBrush);

		// 再用描边笔画轮廓，这样笔的样式更容易看出
        CPen* pOldOutlinePen = pDC->SelectObject(&outlinePens[i]);
		CBrush* pNullBrush = CBrush::FromHandle((HBRUSH)GetStockObject(NULL_BRUSH));
		CBrush* pOldB = pDC->SelectObject(pNullBrush);
		pDC->Ellipse(&rc);
		pDC->SelectObject(pOldOutlinePen);
		pDC->SelectObject(pOldB);
	}

	// 绘制花心
	CPen penCenter;
	penCenter.CreatePen(PS_SOLID, 2, RGB(0, 0, 0));
	CBrush brushCenter(RGB(255, 220, 0));
	CPen* pOldPen = pDC->SelectObject(&penCenter);
	CBrush* pOldBrush = pDC->SelectObject(&brushCenter);
	CRect rcCenter(center.x - centerR, center.y - centerR, center.x + centerR, center.y + centerR);
	pDC->Ellipse(&rcCenter);
	pDC->SelectObject(pOldPen);
	pDC->SelectObject(pOldBrush);
}


// CMFCApplication2View 打印

BOOL CMFCApplication2View::OnPreparePrinting(CPrintInfo* pInfo)
{
	// 默认准备
	return DoPreparePrinting(pInfo);
}

void CMFCApplication2View::OnBeginPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: 添加额外的打印前进行的初始化过程
}

void CMFCApplication2View::OnEndPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: 添加打印后进行的清理过程
}


// CMFCApplication2View 诊断

#ifdef _DEBUG
void CMFCApplication2View::AssertValid() const
{
	CView::AssertValid();
}

void CMFCApplication2View::Dump(CDumpContext& dc) const
{
	CView::Dump(dc);
}

CMFCApplication2Doc* CMFCApplication2View::GetDocument() const // 非调试版本是内联的
{
	ASSERT(m_pDocument->IsKindOf(RUNTIME_CLASS(CMFCApplication2Doc)));
	return (CMFCApplication2Doc*)m_pDocument;
}
#endif //_DEBUG


// CMFCApplication2View 消息处理程序
