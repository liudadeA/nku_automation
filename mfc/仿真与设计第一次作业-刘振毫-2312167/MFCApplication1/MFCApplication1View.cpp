
// MFCApplication1View.cpp: CMFCApplication1View 类的实现
//

#include "pch.h"
#include "framework.h"
// SHARED_HANDLERS 可以在实现预览、缩略图和搜索筛选器句柄的
// ATL 项目中进行定义，并允许与该项目共享文档代码。
#ifndef SHARED_HANDLERS
#include "MFCApplication1.h"
#endif

#include "MFCApplication1Doc.h"
#include "MFCApplication1View.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

#include <cmath>
#define PI 3.1415926

// CMFCApplication1View 类

IMPLEMENT_DYNCREATE(CMFCApplication1View, CView)

BEGIN_MESSAGE_MAP(CMFCApplication1View, CView)
	// 标准打印命令
	ON_COMMAND(ID_FILE_PRINT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_DIRECT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_PREVIEW, &CView::OnFilePrintPreview)
    ON_WM_LBUTTONDOWN()

END_MESSAGE_MAP()

// CMFCApplication1View 构造/析构

CMFCApplication1View::CMFCApplication1View() noexcept
{
// 待办：在此处添加构造代码
    m_showCross = false;
    m_clickPoint = CPoint(0,0);
    m_lastX = 0.0;
    m_lastY = 0.0;

}

CMFCApplication1View::~CMFCApplication1View()
{
}

BOOL CMFCApplication1View::PreCreateWindow(CREATESTRUCT& cs)
{
// 待办：在此处通过修改
//  CREATESTRUCT cs 来修改窗口类或样式

	return CView::PreCreateWindow(cs);
}

// CMFCApplication1View 绘图

void CMFCApplication1View::OnDraw(CDC* pDC)
{
	CMFCApplication1Doc* pDoc = GetDocument();
	ASSERT_VALID(pDoc);
	if (!pDoc)
		return;

    // 绘图区域和坐标轴余弦曲线绘制在左上 2/3 区域
    CRect clientRect;
    GetClientRect(&clientRect);
    int plotRight = clientRect.left + (clientRect.Width() * 2) / 3; // 左上区域宽度为窗口的2/3
    int plotBottom = clientRect.top + (clientRect.Height() * 2) / 3; // 左上区域高度为窗口的2/3
    CRect plotRect(clientRect.left, clientRect.top, plotRight, plotBottom);
    // 右侧用于显示信息的区域
    CRect infoRect(plotRight, clientRect.top, clientRect.right, clientRect.bottom);

    CBrush brushBg(RGB(240, 240, 240));
    pDC->FillRect(&plotRect, &brushBg);

    // 用户坐标系定义
    const double ux_min = 0.0, ux_max = 2.0 * PI;
    const double uy_min = -1.0, uy_max = 1.0;
    const int margin = 20; // 像素边距
    int plotW = plotRect.Width() - 2 * margin;
    int plotH = plotRect.Height() - 2 * margin;
    int plotLeft = plotRect.left + margin;
    int plotTop = plotRect.top + margin;

    auto userToDevice = [&](double ux, double uy) -> CPoint {
        double rx = (ux - ux_min) / (ux_max - ux_min);
        double ry = (uy - uy_min) / (uy_max - uy_min);
        int x = plotLeft + (int)(rx * plotW + 0.5);
        int y = plotTop + (int)((1.0 - ry) * plotH + 0.5);
        return CPoint(x, y);
    };

    // 在 plotRect 内画坐标系
    CPen penAxis(PS_SOLID, 1, RGB(0, 0, 0));
    CPen* pOldPenAxis = pDC->SelectObject(&penAxis);
    // x 轴 (用户坐标)
    CPoint x0 = userToDevice(ux_min, 0.0);
    CPoint x1 = userToDevice(ux_max, 0.0);
    pDC->MoveTo(x0);
    pDC->LineTo(x1);
    // y 轴 (用户坐标)
    CPoint y0 = userToDevice(0.0, uy_min);
    CPoint y1 = userToDevice(0.0, uy_max);
    pDC->MoveTo(y0);
    pDC->LineTo(y1);

    // x 轴刻度和标签
    CString label;
    const double ticks[] = {0.0, PI/2.0, PI, 3.0*PI/2.0, 2.0*PI};
    for (double t : ticks)
    {
        CPoint pt = userToDevice(t, 0.0);
        pDC->MoveTo(pt.x, pt.y - 4);
        pDC->LineTo(pt.x, pt.y + 4);
        // x标签
        if (fabs(t - PI) < 1e-6) label = _T("π");
        else if (fabs(t - PI/2.0) < 1e-6) label = _T("π/2");
        else if (fabs(t - 3.0*PI/2.0) < 1e-6) label = _T("3π/2");
        else if (fabs(t - 2.0*PI) < 1e-6) label = _T("2π");
        CSize sz = pDC->GetTextExtent(label);
		// 放到刻度下方并水平居中
        pDC->TextOut(pt.x - sz.cx/2, pt.y + 6, label);
    }
    //
    // y 轴刻度
    for (int i = -1; i <= 1; ++i)
    {
        CPoint pt = userToDevice(0.0, (double)i);
        pDC->MoveTo(pt.x - 4, pt.y);
        pDC->LineTo(pt.x + 4, pt.y);
        label.Format(_T("%d"), i);
        CSize sz = pDC->GetTextExtent(label);
		// 把标签放在左侧
        pDC->TextOut(pt.x - sz.cx - 6, pt.y - sz.cy/2, label);
    }

    // 绘制余弦曲线
    if (plotW < 1) plotW = 1;
    if (plotH < 1) plotH = 1;
    const int samples = (plotW > 100) ? plotW : 100;
    bool first = true;
    CPoint lastPt;
    for (int i = 0; i <= samples; ++i)
    {
        double ux = ux_min + (ux_max - ux_min) * (double)i / (double)samples;
        double uy = cos(ux);
        CPoint pt = userToDevice(ux, uy);
        if (first)
        {
            lastPt = pt; first = false;
        }
        else
        {
            pDC->MoveTo(lastPt);
            pDC->LineTo(pt);
            lastPt = pt;
        }
    }

    // 绘制所有已保存的点击点并在点旁显示坐标值
    for (const auto &up : m_points)
    {
        double ux = up.first;
        double uy = up.second;
        CPoint pt = userToDevice(ux, uy);
        // 黑点
        CBrush brushDot(RGB(0,0,0));
        CBrush* pOldBrush = pDC->SelectObject(&brushDot);
        const int r = 4;
        pDC->Ellipse(pt.x - r, pt.y - r, pt.x + r, pt.y + r);
        pDC->SelectObject(pOldBrush);
        // 坐标
        CString txt;
        txt.Format(_T("(%.2f, %.2f)"), ux, uy);
        CSize tSz = pDC->GetTextExtent(txt);
        int tx = pt.x + 6;
        int ty = pt.y - tSz.cy/2;
        // 画在标点旁边
        if (tx + tSz.cx > plotRect.right - 4) tx = pt.x - tSz.cx - 6;
        pDC->TextOut(tx, ty, txt);
    }

    // 坐标轴
    CPoint arrowSize(6,6);
    // x
    pDC->MoveTo(x1.x, x1.y);
    pDC->LineTo(x1.x - 10, x1.y - 6);
    pDC->MoveTo(x1.x, x1.y);
    pDC->LineTo(x1.x - 10, x1.y + 6);
    // y
    pDC->MoveTo(y1.x, y1.y);
    pDC->LineTo(y1.x - 6, y1.y + 10);
    pDC->MoveTo(y1.x, y1.y);
    pDC->LineTo(y1.x + 6, y1.y + 10);

    pDC->SelectObject(pOldPenAxis);

    // 右侧显示坐标点信息
    CBrush brushRight(RGB(255,255,255));
    pDC->FillRect(&infoRect, &brushRight);
    CString info;
    info.Format(_T("最新坐标点：X= %.2f  Y= %.2f"), m_lastX, m_lastY);
    pDC->TextOut(infoRect.left + 10, infoRect.top + 10, info);

    // 绘制光标和标记点，使用用户坐标重新计算设备位置缩放位置正确
    if (m_showCross)
    {
    // 绘制十字光标并在曲线上标记对应点
    CPen penCross(PS_SOLID, 1, RGB(0,0,0));
    CPen* pOld = pDC->SelectObject(&penCross);
    // 根据存储的用户坐标计算设备坐标点
    CPoint crossPt = userToDevice(m_lastX, m_lastY);
    // 确保点在左侧绘图区域内
    if (plotRect.PtInRect(crossPt))
    {
        // 垂直线
        pDC->MoveTo(crossPt.x, plotRect.top);
        pDC->LineTo(crossPt.x, plotRect.bottom);
        // 水平线
        pDC->MoveTo(plotRect.left, crossPt.y);
        pDC->LineTo(plotRect.right, crossPt.y);

    }
        pDC->SelectObject(pOld);
    }

}


// CMFCApplication1View 打印

BOOL CMFCApplication1View::OnPreparePrinting(CPrintInfo* pInfo)
{
	// 默认准备
	return DoPreparePrinting(pInfo);
}

void CMFCApplication1View::OnBeginPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: 添加额外的打印前进行的初始化过程
}

void CMFCApplication1View::OnEndPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: 添加打印后进行的清理过程
}


// CMFCApplication1View 诊断

#ifdef _DEBUG
void CMFCApplication1View::AssertValid() const
{
	CView::AssertValid();
}

void CMFCApplication1View::Dump(CDumpContext& dc) const
{
	CView::Dump(dc);
}

CMFCApplication1Doc* CMFCApplication1View::GetDocument() const // 非调试版本是内联的
{
	ASSERT(m_pDocument->IsKindOf(RUNTIME_CLASS(CMFCApplication1Doc)));
	return (CMFCApplication1Doc*)m_pDocument;
}
#endif //_DEBUG


// CMFCApplication1View 消息处理程序

void CMFCApplication1View::OnLButtonDown(UINT nFlags, CPoint point)
{
    // 记录点击点并计算用户坐标
    CRect clientRect; GetClientRect(&clientRect);
    int plotRight = clientRect.left + (clientRect.Width() * 2) / 3;
    int plotBottom = clientRect.top + (clientRect.Height() * 2) / 3;
    CRect plotRect(clientRect.left, clientRect.top, plotRight, plotBottom);
    m_clickPoint = point;
    if (plotRect.PtInRect(point))
    {
        m_showCross = true;

        const int margin = 20;
        const double ux_min = 0.0, ux_max = 2.0 * PI;
        const double uy_min = -1.0, uy_max = 1.0;
        int plotW = plotRect.Width() - 2 * margin;
        int plotH = plotRect.Height() - 2 * margin;
        int plotLeft = plotRect.left + margin;
        int plotTop = plotRect.top + margin;
        // 计算用户坐标
        double rx = (double)(point.x - plotLeft) / (double)plotW;
        double ry = 1.0 - (double)(point.y - plotTop) / (double)plotH;
        if (rx < 0.0) rx = 0.0; if (rx > 1.0) rx = 1.0;
        if (ry < 0.0) ry = 0.0; if (ry > 1.0) ry = 1.0;
        m_lastX = ux_min + rx * (ux_max - ux_min);
        m_lastY = uy_min + ry * (uy_max - uy_min);
        // 保存该点
        m_points.push_back(std::make_pair(m_lastX, m_lastY));
        // 计算该用户坐标对应的设备坐标
        double rxs = (m_lastX - ux_min) / (ux_max - ux_min);
        double rys = (m_lastY - uy_min) / (uy_max - uy_min);
        int dx = plotLeft + (int)(rxs * plotW + 0.5);
        int dy = plotTop + (int)((1.0 - rys) * plotH + 0.5);
        m_clickPoint = CPoint(dx, dy);
    }
    else
    {
        m_showCross = false;
    }
    Invalidate();
    CView::OnLButtonDown(nFlags, point);
}

