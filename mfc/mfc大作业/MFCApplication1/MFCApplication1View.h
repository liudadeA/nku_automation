// MFCApplication1View.h : CMFCApplication1View 类的接口
// 太阳翼展开仿真 - 视图类

#pragma once
#include <vector>
#include <afxwin.h>
#include "MFCApplication1Doc.h"

// 鼠标标记点结构（用于曲线图点击显示坐标）
struct CMarkerPoint
{
    CPoint pos;
    double timeVal;
    double dataVal;
    CString label;
};

// 每个曲线图的标记点集合
struct CPlotMarkers
{
    std::vector<CMarkerPoint> markers;
};

class CMFCApplication1View : public CView
{
protected:
    CMFCApplication1View() noexcept;
    DECLARE_DYNCREATE(CMFCApplication1View)

public:
    CMFCApplication1Doc* GetDocument() const;

public:
    virtual void OnDraw(CDC* pDC);
    virtual BOOL PreCreateWindow(CREATESTRUCT& cs);

    // 定时器控制
    void StartTimer();
    void StopTimer();

protected:
    virtual BOOL OnPreparePrinting(CPrintInfo* pInfo);
    virtual void OnBeginPrinting(CDC* pDC, CPrintInfo* pInfo);
    virtual void OnEndPrinting(CDC* pDC, CPrintInfo* pInfo);

public:
    virtual ~CMFCApplication1View();
#ifdef _DEBUG
    virtual void AssertValid() const;
    virtual void Dump(CDumpContext& dc) const;
#endif

protected:
    DECLARE_MESSAGE_MAP()

    // 消息处理
    afx_msg void OnTimer(UINT_PTR nIDEvent);
    afx_msg void OnMouseMove(UINT nFlags, CPoint point);
    afx_msg void OnLButtonDown(UINT nFlags, CPoint point);
    afx_msg void OnLButtonDblClk(UINT nFlags, CPoint point);
    afx_msg BOOL OnSetCursor(CWnd* pWnd, UINT nHitTest, UINT message);
    afx_msg BOOL OnEraseBkgnd(CDC* pDC);

private:
    // 布局计算
    void CalcLayout(CRect& rcPlot, CRect& rcAnim,
                    CRect& rcForce, CRect& rcError, CRect& rcDisp) const;

    // 绘图函数
    void DrawPlotArea(CDC& dc, const CRect& rc, int plotIndex);
    void DrawPlotGrid(CDC& dc, const CRect& rc, double yMin, double yMax,
                      const CString& yLabel, int plotIndex);
    void DrawPlotCurve(CDC& dc, const CRect& rc, int plotIndex);
    void DrawPlotMarkers(CDC& dc, const CRect& rc, int plotIndex);
    void DrawAnimation(CDC& dc, const CRect& rc);

    // 判断鼠标在哪个图 (0=拉力, 1=误差, 2=位移, -1=无)
    int HitTestPlot(const CPoint& point) const;

    // 定时器
    static const UINT_PTR TIMER_SIM = 1;
    bool m_timerRunning = false;

    // 布局缓存（在OnDraw时更新）
    CRect m_rcForce, m_rcError, m_rcDisp, m_rcAnim, m_rcPlot;

    // 鼠标标记 (0=拉力, 1=误差, 2=位移)
    CPlotMarkers m_markers[3];

    // 背景色
    COLORREF m_bgColor = RGB(30, 30, 30);

    // 太阳翼位图
    CBitmap m_solarWingBmp;
    bool m_bmpLoaded = false;

    // 每幅图的绘图区域及Y轴范围缓存（用于鼠标坐标转换）
    int m_curPlotLeft[3] = {}, m_curPlotRight[3] = {}, m_curPlotTop[3] = {}, m_curPlotBottom[3] = {};
    double m_curYMin[3] = {}, m_curYMax[3] = {1, 1, 1};
};

#ifndef _DEBUG
inline CMFCApplication1Doc* CMFCApplication1View::GetDocument() const
   { return reinterpret_cast<CMFCApplication1Doc*>(m_pDocument); }
#endif
