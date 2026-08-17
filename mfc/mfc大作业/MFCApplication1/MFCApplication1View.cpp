// MFCApplication1View.cpp : CMFCApplication1View 类的实现
// 太阳翼展开仿真 - 视图类

#include "pch.h"
#include "framework.h"
#ifndef SHARED_HANDLERS
#include "MFCApplication1.h"
#endif

#include "MFCApplication1Doc.h"
#include "MFCApplication1View.h"

#include <cmath>
#include <algorithm>

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

IMPLEMENT_DYNCREATE(CMFCApplication1View, CView)

BEGIN_MESSAGE_MAP(CMFCApplication1View, CView)
    ON_COMMAND(ID_FILE_PRINT, &CView::OnFilePrint)
    ON_COMMAND(ID_FILE_PRINT_DIRECT, &CView::OnFilePrint)
    ON_COMMAND(ID_FILE_PRINT_PREVIEW, &CView::OnFilePrintPreview)
    ON_WM_TIMER()
    ON_WM_MOUSEMOVE()
    ON_WM_LBUTTONDOWN()
    ON_WM_LBUTTONDBLCLK()
    ON_WM_SETCURSOR()
    ON_WM_ERASEBKGND()
END_MESSAGE_MAP()

// ============================================================
// 构造/析构
// ============================================================

CMFCApplication1View::CMFCApplication1View() noexcept
{
    m_bmpLoaded = false;
}

CMFCApplication1View::~CMFCApplication1View()
{
    if (m_bmpLoaded)
        m_solarWingBmp.DeleteObject();
}

BOOL CMFCApplication1View::PreCreateWindow(CREATESTRUCT& cs)
{
    return CView::PreCreateWindow(cs);
}

// ============================================================
// 布局计算
// ============================================================

void CMFCApplication1View::CalcLayout(CRect& rcPlot, CRect& rcAnim,
                                       CRect& rcForce, CRect& rcError, CRect& rcDisp) const
{
    CRect rcClient;
    GetClientRect(&rcClient);

    int margin = 5;

    // 左侧 2/3 为曲线区域, 右侧 1/3 为动画区域
    int splitX = rcClient.Width() * 2 / 3;
    rcPlot = CRect(rcClient.left + margin, rcClient.top + margin,
                   splitX - margin, rcClient.bottom - margin);
    rcAnim = CRect(splitX + margin, rcClient.top + margin,
                   rcClient.right - margin, rcClient.bottom - margin);

    // 左侧三幅图垂直平分
    int plotHeight = rcPlot.Height() / 3;
    rcForce = CRect(rcPlot.left, rcPlot.top,
                    rcPlot.right, rcPlot.top + plotHeight - 2);
    rcError = CRect(rcPlot.left, rcForce.bottom + 4,
                    rcPlot.right, rcForce.bottom + plotHeight - 2);
    rcDisp = CRect(rcPlot.left, rcError.bottom + 4,
                   rcPlot.right, rcPlot.bottom);
}

// ============================================================
// 主绘图
// ============================================================

BOOL CMFCApplication1View::OnEraseBkgnd(CDC* /*pDC*/)
{
    return TRUE;  // 禁止背景擦除，防止闪烁
}

void CMFCApplication1View::OnDraw(CDC* pDC)
{
    CMFCApplication1Doc* pDoc = GetDocument();
    ASSERT_VALID(pDoc);
    if (!pDoc) return;

    // 获取客户区
    CRect rcClient;
    GetClientRect(&rcClient);

    // 双缓冲：创建内存DC
    CDC memDC;
    memDC.CreateCompatibleDC(pDC);
    CBitmap memBmp;
    memBmp.CreateCompatibleBitmap(pDC, rcClient.Width(), rcClient.Height());
    CBitmap* pOldBmp = memDC.SelectObject(&memBmp);

    // 用背景色填充
    memDC.FillSolidRect(&rcClient, pDoc->GetAppearance().bgColor);

    // 计算布局
    CalcLayout(m_rcPlot, m_rcAnim, m_rcForce, m_rcError, m_rcDisp);
    m_bgColor = pDoc->GetAppearance().bgColor;

    // 绘制三幅曲线图到内存DC
    DrawPlotArea(memDC, m_rcForce, 0);
    DrawPlotArea(memDC, m_rcError, 1);
    DrawPlotArea(memDC, m_rcDisp, 2);

    // 绘制动画到内存DC
    DrawAnimation(memDC, m_rcAnim);

    // 一次性将内存DC复制到屏幕
    pDC->BitBlt(0, 0, rcClient.Width(), rcClient.Height(), &memDC, 0, 0, SRCCOPY);

    memDC.SelectObject(pOldBmp);
    memBmp.DeleteObject();
    memDC.DeleteDC();
}

// ============================================================
// 绘制单个曲线图
// ============================================================

void CMFCApplication1View::DrawPlotArea(CDC& dc, const CRect& rc, int plotIndex)
{
    CMFCApplication1Doc* pDoc = GetDocument();
    if (!pDoc) return;

    // 填充背景
    dc.FillSolidRect(&rc, m_bgColor);

    // 边框
    CPen borderPen(PS_SOLID, 1, RGB(100, 100, 100));
    CPen* pOldPen = dc.SelectObject(&borderPen);
    dc.Rectangle(&rc);
    dc.SelectObject(pOldPen);

    // 根据历史数据计算Y轴范围
    double yMin = 0, yMax = 1;
    const std::vector<double>* pHistory = nullptr;
    CString yLabel;

    switch (plotIndex)
    {
    case 0: // 拉力
        pHistory = &pDoc->GetForceHistory();
        yLabel = L"拉力(N)";
        break;
    case 1: // 误差
        pHistory = &pDoc->GetErrorHistory();
        yLabel = L"误差(m)";
        break;
    case 2: // 位移（两条曲线：实际 + 目标）
        {
            const auto& dispHist = pDoc->GetDispHistory();
            const auto& targHist = pDoc->GetTargetHistory();
            yMin = 0;
            yMax = pDoc->GetParams().maxDisplacement * 1.1;
            if (!dispHist.empty())
            {
                double maxDisp = *(std::max_element(dispHist.begin(), dispHist.end()));
                double maxTarg = *(std::max_element(targHist.begin(), targHist.end()));
                yMax = (std::max)(maxDisp, maxTarg) * 1.15;
                if (yMax < 1.0) yMax = 1.0;
            }
        }
        yLabel = L"位移(m)";
        break;
    }

    if (plotIndex != 2 && pHistory)
    {
        yMin = 0;
        yMax = 1;
        if (!pHistory->empty())
        {
            double dataMin = *(std::min_element(pHistory->begin(), pHistory->end()));
            double dataMax = *(std::max_element(pHistory->begin(), pHistory->end()));
            double margin2 = (dataMax - dataMin) * 0.15;
            if (margin2 < 0.1) margin2 = 0.5;
            yMin = dataMin - margin2;
            yMax = dataMax + margin2;
            if (plotIndex == 0) yMin = 0; // 拉力不小于0
        }
    }

    // 绘制网格和坐标轴
    DrawPlotGrid(dc, rc, yMin, yMax, yLabel, plotIndex);

    // 绘制曲线
    DrawPlotCurve(dc, rc, plotIndex);

    // 绘制鼠标标记
    DrawPlotMarkers(dc, rc, plotIndex);
}

void CMFCApplication1View::DrawPlotGrid(CDC& dc, const CRect& rc, double yMin, double yMax,
                                         const CString& yLabel, int plotIndex)
{
    CMFCApplication1Doc* pDoc = GetDocument();
    if (!pDoc) return;

    PlotAppearance& app = pDoc->GetAppearance();
    double simTime = pDoc->GetParams().simTime;

    // X轴范围
    double xMin = 0, xMax = simTime;
    if (xMax < 1.0) xMax = 1.0;

    // 边距
    int leftMargin = 55;
    int rightMargin = 20;
    int topMargin = 10;
    int bottomMargin = 40;

    int plotLeft = rc.left + leftMargin;
    int plotRight = rc.right - rightMargin;
    int plotTop = rc.top + topMargin;
    int plotBottom = rc.bottom - bottomMargin;
    int plotWidth = plotRight - plotLeft;
    int plotHeight = plotBottom - plotTop;

    if (plotWidth <= 0 || plotHeight <= 0) return;

    // 网格线
    CPen gridPen(PS_DOT, 1, RGB(60, 60, 60));
    CPen* pOldPen = dc.SelectObject(&gridPen);

    // 水平网格线 (Y轴)
    int nYLines = 5;
    for (int i = 0; i <= nYLines; i++)
    {
        int y = plotBottom - (i * plotHeight / nYLines);
        dc.MoveTo(plotLeft, y);
        dc.LineTo(plotRight, y);

        // Y轴刻度标签（第一象限内，Y轴右侧）
        double val = yMin + (yMax - yMin) * i / nYLines;
        CString strVal;
        strVal.Format(L"%.2f", val);
        dc.SetTextColor(RGB(180, 180, 180));
        dc.SetBkMode(TRANSPARENT);
        CRect rcText(plotLeft + 3, y - 8, plotLeft + 50, y + 8);
        dc.DrawText(strVal, &rcText, DT_LEFT | DT_VCENTER | DT_SINGLELINE);
    }

    // 垂直网格线 (X轴)
    int nXLines = 5;
    for (int i = 0; i <= nXLines; i++)
    {
        int x = plotLeft + (i * plotWidth / nXLines);
        dc.MoveTo(x, plotTop);
        dc.LineTo(x, plotBottom);

        // X轴刻度标签
        double val = xMin + (xMax - xMin) * i / nXLines;
        CString strVal;
        strVal.Format(L"%.1f", val);
        dc.SetTextColor(RGB(180, 180, 180));
        CRect rcText(x - 25, plotBottom + 3, x + 25, plotBottom + 25);
        dc.DrawText(strVal, &rcText, DT_CENTER | DT_TOP | DT_SINGLELINE);
    }

    dc.SelectObject(pOldPen);

    // 坐标轴线
    CPen axisPen(PS_SOLID, 1, RGB(200, 200, 200));
    pOldPen = dc.SelectObject(&axisPen);
    dc.MoveTo(plotLeft, plotTop);
    dc.LineTo(plotLeft, plotBottom);
    dc.LineTo(plotRight, plotBottom);
    dc.SelectObject(pOldPen);

    // Y轴标签（纵轴）
    LOGFONTW* pLF = nullptr;
    COLORREF labelColor = RGB(200, 200, 200);

    switch (plotIndex)
    {
    case 0: pLF = &app.lfForceLabel; labelColor = app.colorForceLabel; break;
    case 1: pLF = &app.lfErrorLabel; labelColor = app.colorErrorLabel; break;
    case 2: pLF = &app.lfDispLabel; labelColor = app.colorDispLabel; break;
    }

    if (pLF && pLF->lfHeight != 0)
    {
        CFont font;
        font.CreateFontIndirectW(pLF);
        CFont* pOldFont = dc.SelectObject(&font);
        dc.SetTextColor(labelColor);
        // Y轴标题在左侧边距内，右对齐贴紧Y轴
        CRect rcYLabel(rc.left + 2, plotTop, plotLeft - 3, plotBottom);
        dc.DrawText(yLabel, &rcYLabel, DT_RIGHT | DT_VCENTER | DT_SINGLELINE);
        dc.SelectObject(pOldFont);
    }
    else
    {
        dc.SetTextColor(labelColor);
        // Y轴标题在左侧边距内，右对齐贴紧Y轴
        CRect rcYLabel(rc.left + 2, plotTop, plotLeft - 3, plotBottom);
        dc.DrawText(yLabel, &rcYLabel, DT_RIGHT | DT_VCENTER | DT_SINGLELINE);
    }

    // X轴标签（横轴）
    if (app.lfTimeLabel.lfHeight != 0)
    {
        CFont fontTime;
        fontTime.CreateFontIndirectW(&app.lfTimeLabel);
        CFont* pOldFont = dc.SelectObject(&fontTime);
        dc.SetTextColor(app.colorTimeLabel);
        CRect rcXLabel(plotLeft, plotBottom + 20, plotRight, rc.bottom);
        dc.DrawText(L"时间(s)", &rcXLabel, DT_CENTER | DT_TOP | DT_SINGLELINE);
        dc.SelectObject(pOldFont);
    }
    else
    {
        dc.SetTextColor(app.colorTimeLabel);
        CRect rcXLabel(plotLeft, plotBottom + 20, plotRight, rc.bottom);
        dc.DrawText(L"时间(s)", &rcXLabel, DT_CENTER | DT_TOP | DT_SINGLELINE);
    }

    // 缓存每幅图的绘图区域及Y轴范围供鼠标坐标转换
    m_curPlotLeft[plotIndex] = plotLeft;
    m_curPlotRight[plotIndex] = plotRight;
    m_curPlotTop[plotIndex] = plotTop;
    m_curPlotBottom[plotIndex] = plotBottom;
    m_curYMin[plotIndex] = yMin;
    m_curYMax[plotIndex] = yMax;
}

void CMFCApplication1View::DrawPlotCurve(CDC& dc, const CRect& rc, int plotIndex)
{
    CMFCApplication1Doc* pDoc = GetDocument();
    if (!pDoc) return;

    const auto& timeHist = pDoc->GetTimeHistory();
    if (timeHist.empty()) return;

    double simTime = pDoc->GetParams().simTime;
    double xMin = 0, xMax = simTime;
    if (xMax < 1.0) xMax = 1.0;

    int leftMargin = 55, rightMargin = 20, topMargin = 10, bottomMargin = 40;
    int plotLeft = rc.left + leftMargin;
    int plotRight = rc.right - rightMargin;
    int plotTop = rc.top + topMargin;
    int plotBottom = rc.bottom - bottomMargin;
    int plotWidth = plotRight - plotLeft;
    int plotHeight = plotBottom - plotTop;

    if (plotWidth <= 0 || plotHeight <= 0) return;

    auto dataToScreen = [&](double t, double val, double yMin, double yMax) -> CPoint
    {
        int sx = plotLeft + (int)((t - xMin) / (xMax - xMin) * plotWidth);
        int sy = plotBottom - (int)((val - yMin) / (yMax - yMin) * plotHeight);
        return CPoint(sx, sy);
    };

    if (plotIndex == 0) // 拉力曲线
    {
        const auto& forceHist = pDoc->GetForceHistory();
        if (forceHist.empty() || forceHist.size() != timeHist.size()) return;

        double yMin = 0;
        double yMax = *(std::max_element(forceHist.begin(), forceHist.end())) * 1.15;
        if (yMax < 1.0) yMax = 1.0;

        CPen curvePen(PS_SOLID, 2, RGB(255, 200, 100));
        CPen* pOldPen = dc.SelectObject(&curvePen);

        CPoint pt0 = dataToScreen(timeHist[0], forceHist[0], yMin, yMax);
        dc.MoveTo(pt0);

        // 降采样绘制以提高性能
        int step = (std::max)(1, (int)timeHist.size() / 2000);
        for (size_t i = step; i < timeHist.size(); i += step)
        {
            CPoint pt = dataToScreen(timeHist[i], forceHist[i], yMin, yMax);
            dc.LineTo(pt);
        }
        if (timeHist.size() > 1 && (timeHist.size() - 1) % step != 0)
        {
            size_t last = timeHist.size() - 1;
            CPoint pt = dataToScreen(timeHist[last], forceHist[last], yMin, yMax);
            dc.LineTo(pt);
        }
        dc.SelectObject(pOldPen);
    }
    else if (plotIndex == 1) // 误差曲线
    {
        const auto& errorHist = pDoc->GetErrorHistory();
        if (errorHist.empty() || errorHist.size() != timeHist.size()) return;

        double yMin = *(std::min_element(errorHist.begin(), errorHist.end()));
        double yMax = *(std::max_element(errorHist.begin(), errorHist.end()));
        double margin2 = (yMax - yMin) * 0.15;
        if (margin2 < 0.1) margin2 = 0.5;
        yMin -= margin2;
        yMax += margin2;

        CPen curvePen(PS_SOLID, 2, RGB(255, 150, 150));
        CPen* pOldPen = dc.SelectObject(&curvePen);

        CPoint pt0 = dataToScreen(timeHist[0], errorHist[0], yMin, yMax);
        dc.MoveTo(pt0);

        int step = (std::max)(1, (int)timeHist.size() / 2000);
        for (size_t i = step; i < timeHist.size(); i += step)
        {
            CPoint pt = dataToScreen(timeHist[i], errorHist[i], yMin, yMax);
            dc.LineTo(pt);
        }
        if (timeHist.size() > 1 && (timeHist.size() - 1) % step != 0)
        {
            size_t last = timeHist.size() - 1;
            CPoint pt = dataToScreen(timeHist[last], errorHist[last], yMin, yMax);
            dc.LineTo(pt);
        }
        dc.SelectObject(pOldPen);

        // 零误差参考线
        CPen zeroPen(PS_DASH, 1, RGB(100, 200, 100));
        pOldPen = dc.SelectObject(&zeroPen);
        CPoint z0 = dataToScreen(xMin, 0.0, yMin, yMax);
        CPoint z1 = dataToScreen(xMax, 0.0, yMin, yMax);
        dc.MoveTo(z0); dc.LineTo(z1);
        dc.SelectObject(pOldPen);
    }
    else if (plotIndex == 2) // 位移曲线（两条）
    {
        const auto& dispHist = pDoc->GetDispHistory();
        const auto& targHist = pDoc->GetTargetHistory();
        if (dispHist.empty() || targHist.empty()) return;

        double yMin = 0;
        double yMax = pDoc->GetParams().maxDisplacement * 1.1;
        double maxDisp = *(std::max_element(dispHist.begin(), dispHist.end()));
        double maxTarg = *(std::max_element(targHist.begin(), targHist.end()));
        yMax = (std::max)(maxDisp, maxTarg) * 1.15;
        if (yMax < 1.0) yMax = 1.0;

        // 目标位移曲线（点划线绿色，与实线位移区分）
        CPen targetPen(PS_DASHDOT, 2, RGB(100, 255, 100));
        CPen* pOldPen = dc.SelectObject(&targetPen);
        CPoint ptT0 = dataToScreen(timeHist[0], targHist[0], yMin, yMax);
        dc.MoveTo(ptT0);
        int step = (std::max)(1, (int)timeHist.size() / 2000);
        for (size_t i = step; i < timeHist.size(); i += step)
        {
            CPoint pt = dataToScreen(timeHist[i], targHist[i], yMin, yMax);
            dc.LineTo(pt);
        }
        dc.SelectObject(pOldPen);

        // 实际位移曲线（实线蓝色）
        CPen dispPen(PS_SOLID, 2, RGB(150, 200, 255));
        pOldPen = dc.SelectObject(&dispPen);
        CPoint ptD0 = dataToScreen(timeHist[0], dispHist[0], yMin, yMax);
        dc.MoveTo(ptD0);
        for (size_t i = step; i < timeHist.size(); i += step)
        {
            CPoint pt = dataToScreen(timeHist[i], dispHist[i], yMin, yMax);
            dc.LineTo(pt);
        }
        dc.SelectObject(pOldPen);
    }
}

void CMFCApplication1View::DrawPlotMarkers(CDC& dc, const CRect& rc, int plotIndex)
{
    auto& markers = m_markers[plotIndex].markers;
    for (auto& m : markers)
    {
        // 在标记位置绘制十字光标
        CPen markerPen(PS_SOLID, 1, RGB(255, 255, 0));
        CPen* pOldPen = dc.SelectObject(&markerPen);
        dc.MoveTo(m.pos.x - 5, m.pos.y);
        dc.LineTo(m.pos.x + 5, m.pos.y);
        dc.MoveTo(m.pos.x, m.pos.y - 5);
        dc.LineTo(m.pos.x, m.pos.y + 5);
        dc.SelectObject(pOldPen);

        // 显示坐标值
        dc.SetTextColor(RGB(255, 255, 0));
        dc.SetBkMode(TRANSPARENT);
        dc.TextOutW(m.pos.x + 8, m.pos.y - 8, m.label);
    }
}

// ============================================================
// 动画绘制（右侧 1/3 区域）
// ============================================================

void CMFCApplication1View::DrawAnimation(CDC& dc, const CRect& rc)
{
    CMFCApplication1Doc* pDoc = GetDocument();
    if (!pDoc) return;

    // 背景
    dc.FillSolidRect(&rc, RGB(40, 40, 50));

    // 边框
    CPen borderPen(PS_SOLID, 1, RGB(100, 100, 120));
    CPen* pOldPen = dc.SelectObject(&borderPen);
    dc.Rectangle(&rc);
    dc.SelectObject(pOldPen);

    int cx = rc.CenterPoint().x;
    int bottom = rc.bottom - 30;
    int top = rc.top + 10;

    double maxDisp = pDoc->GetParams().maxDisplacement;
    double curDisp = pDoc->GetCurrentDisplacement();
    double curTarget = pDoc->GetCurrentTarget();

    if (maxDisp < 0.1) maxDisp = 10.0;

    // 动画范围
    int animBottom = bottom;
    int animTop = top + 50;
    int animHeight = animBottom - animTop;

    // 安全限制比例
    double dispRatio = curDisp / maxDisp;
    if (dispRatio > 1.0) dispRatio = 1.0;
    if (dispRatio < 0.0) dispRatio = 0.0;

    double targRatio = curTarget / maxDisp;
    if (targRatio > 1.0) targRatio = 1.0;
    if (targRatio < 0.0) targRatio = 0.0;

    // 太阳翼位置（Y坐标，底在上）
    int wingY = animBottom - (int)(dispRatio * animHeight);
    int targetY = animBottom - (int)(targRatio * animHeight);

    if (wingY < animTop) wingY = animTop;
    if (wingY > animBottom - 20) wingY = animBottom - 20;

    // 目标线高度钳位（防止目标为0时线条溢出底部）
    if (targetY < animTop) targetY = animTop;
    if (targetY > animBottom - 10) targetY = animBottom - 10;

    // --- 绘制卷扬机构（两个椭圆） ---
    CBrush winchBrush(RGB(120, 120, 120));
    CBrush* pOldBrush = dc.SelectObject(&winchBrush);

    int winchRadius = 15;
    int winch1X = cx - 40;
    int winch2X = cx + 40;
    int winchY = animTop - 10;

    dc.Ellipse(winch1X - winchRadius, winchY - winchRadius / 2,
               winch1X + winchRadius, winchY + winchRadius / 2);
    dc.Ellipse(winch2X - winchRadius, winchY - winchRadius / 2,
               winch2X + winchRadius, winchY + winchRadius / 2);
    dc.SelectObject(pOldBrush);

    // --- 绘制钢丝绳 ---
    // 实际位移对应的钢丝绳（实线）
    CPen cablePen1(PS_SOLID, 2, RGB(180, 180, 200));
    pOldPen = dc.SelectObject(&cablePen1);
    dc.MoveTo(winch1X, winchY);
    dc.LineTo(cx - 25, wingY);
    dc.MoveTo(winch2X, winchY);
    dc.LineTo(cx + 25, wingY);
    dc.SelectObject(pOldPen);

    // 目标位移对应的钢丝绳（虚线参考）
    CPen cablePen2(PS_DOT, 1, RGB(100, 255, 100));
    pOldPen = dc.SelectObject(&cablePen2);
    dc.MoveTo(winch1X, winchY);
    dc.LineTo(cx - 20, targetY);
    dc.MoveTo(winch2X, winchY);
    dc.LineTo(cx + 20, targetY);
    dc.SelectObject(pOldPen);

    // --- 绘制太阳翼（矩形） ---
    CRect wingRect(cx - 40, wingY - 15, cx + 40, wingY + 15);

    CBrush wingBrush(RGB(200, 180, 50));
    pOldBrush = dc.SelectObject(&wingBrush);
    CPen wingPen(PS_SOLID, 2, RGB(255, 220, 80));
    pOldPen = dc.SelectObject(&wingPen);
    dc.Rectangle(&wingRect);
    dc.SelectObject(pOldPen);
    dc.SelectObject(pOldBrush);

    // 太阳翼文字标识
    dc.SetTextColor(RGB(0, 0, 0));
    dc.SetBkMode(TRANSPARENT);
    CFont wingFont;
    wingFont.CreateFontW(-12, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE,
                          DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                          DEFAULT_QUALITY, DEFAULT_PITCH, L"Arial");
    CFont* pOldFont = dc.SelectObject(&wingFont);
    dc.DrawText(L"太阳翼", &wingRect, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
    dc.SelectObject(pOldFont);

    // --- 太阳翼展开后下方蓝色区域（展开程度越大，蓝色面积越大） ---
    {
        int blueTop = wingRect.bottom;  // 太阳翼底部
        int blueBottom = animBottom;
        if (blueTop < blueBottom)
        {
            // 太阳翼下方区域渐变蓝色：上半浅蓝，下半深蓝
            int halfY = blueTop + (blueBottom - blueTop) / 2;
            dc.FillSolidRect(rc.left + 2, blueTop, rc.Width() - 4, halfY - blueTop,
                             RGB(50, 120, 200));       // 上半：浅蓝
            dc.FillSolidRect(rc.left + 2, halfY, rc.Width() - 4, blueBottom - halfY,
                             RGB(20, 60, 160));        // 下半：深蓝
        }
    }

    // --- 实时数据显示 ---
    dc.SetTextColor(RGB(0, 0, 0));
    dc.SetBkMode(TRANSPARENT);

    CString strCurDisp, strCurTarget;
    strCurDisp.Format(L"当前位移: %.3f m", curDisp);
    strCurTarget.Format(L"目标位移: %.3f m", curTarget);

    dc.TextOutW(rc.left + 10, rc.bottom - 80, strCurDisp);
    dc.TextOutW(rc.left + 10, rc.bottom - 60, strCurTarget);

    // 位移比例条
    int barX = rc.left + 10;
    int barW = rc.Width() - 20;
    int barY = rc.bottom - 25;
    int barH = 12;

    // 背景条
    dc.FillSolidRect(barX, barY, barW, barH, RGB(80, 80, 80));

    // 实际位移填充
    int fillW = (int)(dispRatio * barW);
    if (fillW > barW) fillW = barW;
    dc.FillSolidRect(barX, barY, fillW, barH, RGB(150, 200, 255));

    // 目标位移标记
    int targX = barX + (int)(targRatio * barW);
    CPen targMarkPen(PS_SOLID, 2, RGB(100, 255, 100));
    pOldPen = dc.SelectObject(&targMarkPen);
    dc.MoveTo(targX, barY - 2);
    dc.LineTo(targX, barY + barH + 2);
    dc.SelectObject(pOldPen);

    // 标题
    dc.SetTextColor(RGB(200, 200, 200));
    dc.TextOutW(cx - 50, rc.top + 5, L"太阳翼展开动画");
}

// ============================================================
// 定时器
// ============================================================

void CMFCApplication1View::StartTimer()
{
    if (!m_timerRunning)
    {
        // 新仿真开始时清除所有鼠标标记
        for (int i = 0; i < 3; i++)
            m_markers[i].markers.clear();

        SetTimer(TIMER_SIM, 20, nullptr);  // ~50fps
        m_timerRunning = true;
    }
}

void CMFCApplication1View::StopTimer()
{
    if (m_timerRunning)
    {
        KillTimer(TIMER_SIM);
        m_timerRunning = false;
    }
}

void CMFCApplication1View::OnTimer(UINT_PTR nIDEvent)
{
    if (nIDEvent == TIMER_SIM)
    {
        CMFCApplication1Doc* pDoc = GetDocument();
        if (!pDoc) return;

        if (pDoc->GetSimState() == SIM_RUNNING)
        {
            // 每个定时器周期推进固定仿真时间（独立于真实时钟）
            double advanceTime = 0.05;  // 每帧推进50ms仿真时间
            double dt = pDoc->GetParams().simStep;
            int steps = (std::max)(1, (int)(advanceTime / dt));

            for (int i = 0; i < steps; i++)
            {
                if (!pDoc->StepSimulation())
                {
                    // 仿真时间到，自然结束（也可能位移超限但仍继续观察稳定性）
                    StopTimer();
                    break;
                }
            }
            Invalidate();  // 触发重绘
        }
    }

    CView::OnTimer(nIDEvent);
}

// ============================================================
// 鼠标交互
// ============================================================

int CMFCApplication1View::HitTestPlot(const CPoint& point) const
{
    if (m_rcForce.PtInRect(point)) return 0;
    if (m_rcError.PtInRect(point)) return 1;
    if (m_rcDisp.PtInRect(point)) return 2;
    return -1;
}

BOOL CMFCApplication1View::OnSetCursor(CWnd* pWnd, UINT nHitTest, UINT message)
{
    CPoint pt;
    GetCursorPos(&pt);
    ScreenToClient(&pt);

    int plotIdx = HitTestPlot(pt);
    if (plotIdx >= 0)
    {
        // 检查是否在绘图区域内（非边距区域）
        int leftMargin = 55, rightMargin = 20, topMargin = 10, bottomMargin = 40;
        const CRect* prc = nullptr;
        switch (plotIdx)
        {
        case 0: prc = &m_rcForce; break;
        case 1: prc = &m_rcError; break;
        case 2: prc = &m_rcDisp; break;
        }
        if (prc)
        {
            CRect plotArea(prc->left + leftMargin, prc->top + topMargin,
                           prc->right - rightMargin, prc->bottom - bottomMargin);
            if (plotArea.PtInRect(pt))
            {
                ::SetCursor(::LoadCursorW(nullptr, IDC_CROSS));
                return TRUE;
            }
        }
    }
    return CView::OnSetCursor(pWnd, nHitTest, message);
}

void CMFCApplication1View::OnMouseMove(UINT nFlags, CPoint point)
{
    // 鼠标移动时OnSetCursor已处理光标切换
    CView::OnMouseMove(nFlags, point);
}

void CMFCApplication1View::OnLButtonDown(UINT nFlags, CPoint point)
{
    CMFCApplication1Doc* pDoc = GetDocument();
    if (!pDoc) return;

    int plotIdx = HitTestPlot(point);
    if (plotIdx < 0) return;

    // 使用缓存的绘图区域（对应被点击的图）
    int plotLeft = m_curPlotLeft[plotIdx];
    int plotRight = m_curPlotRight[plotIdx];
    int plotTop2 = m_curPlotTop[plotIdx];
    int plotBottom2 = m_curPlotBottom[plotIdx];

    if (plotLeft == 0 && plotRight == 0) return;

    CRect plotArea(plotLeft, plotTop2, plotRight, plotBottom2);
    if (!plotArea.PtInRect(point)) return;

    // 将屏幕坐标转换为数据坐标
    double simTime = pDoc->GetParams().simTime;
    double xMin = 0, xMax = simTime;
    if (xMax < 1.0) xMax = 1.0;

    double t = xMin + (double)(point.x - plotArea.left) / plotArea.Width() * (xMax - xMin);
    double yVal = m_curYMin[plotIdx] + (m_curYMax[plotIdx] - m_curYMin[plotIdx])
                  * (1.0 - (double)(point.y - plotArea.top) / plotArea.Height());

    // 添加标记点
    CMarkerPoint mp;
    mp.pos = point;
    mp.timeVal = t;
    mp.dataVal = yVal;

    switch (plotIdx)
    {
    case 0: mp.label.Format(L"t=%.2fs, F=%.2fN", t, yVal); break;
    case 1: mp.label.Format(L"t=%.2fs, e=%.3fm", t, yVal); break;
    case 2: mp.label.Format(L"t=%.2fs, l=%.3fm", t, yVal); break;
    }

    m_markers[plotIdx].markers.push_back(mp);
    Invalidate();

    CView::OnLButtonDown(nFlags, point);
}

void CMFCApplication1View::OnLButtonDblClk(UINT nFlags, CPoint point)
{
    int plotIdx = HitTestPlot(point);
    if (plotIdx >= 0)
    {
        // 双击清除该图内所有标记点
        m_markers[plotIdx].markers.clear();
        Invalidate();
    }

    CView::OnLButtonDblClk(nFlags, point);
}

// ============================================================
// 打印支持
// ============================================================

BOOL CMFCApplication1View::OnPreparePrinting(CPrintInfo* pInfo)
{
    return DoPreparePrinting(pInfo);
}

void CMFCApplication1View::OnBeginPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
}

void CMFCApplication1View::OnEndPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
}

// ============================================================
// 诊断
// ============================================================

#ifdef _DEBUG
void CMFCApplication1View::AssertValid() const
{
    CView::AssertValid();
}

void CMFCApplication1View::Dump(CDumpContext& dc) const
{
    CView::Dump(dc);
}

CMFCApplication1Doc* CMFCApplication1View::GetDocument() const
{
    ASSERT(m_pDocument->IsKindOf(RUNTIME_CLASS(CMFCApplication1Doc)));
    return (CMFCApplication1Doc*)m_pDocument;
}
#endif
