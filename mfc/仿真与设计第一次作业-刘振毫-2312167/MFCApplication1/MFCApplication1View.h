
// MFCApplication1View.h: CMFCApplication1View 类的接口
//

#pragma once


#include <vector>
#include <utility>

class CMFCApplication1View : public CView
{
private:
    // 点击显示十字和坐标
    bool m_showCross;
    CPoint m_clickPoint; // 设备坐标
    double m_lastX; // 用户坐标
    double m_lastY;
    std::vector<std::pair<double,double>> m_points; // 持久化坐标点

protected: // 从序列化创建
	CMFCApplication1View() noexcept;
	DECLARE_DYNCREATE(CMFCApplication1View)

// 特性
public:
	CMFCApplication1Doc* GetDocument() const;

// 操作
public:

// 重写
public:
	virtual void OnDraw(CDC* pDC);  // 重写以绘制该视图
	virtual BOOL PreCreateWindow(CREATESTRUCT& cs);
protected:
	virtual BOOL OnPreparePrinting(CPrintInfo* pInfo);
	virtual void OnBeginPrinting(CDC* pDC, CPrintInfo* pInfo);
	virtual void OnEndPrinting(CDC* pDC, CPrintInfo* pInfo);

// 实现
public:
	virtual ~CMFCApplication1View();
#ifdef _DEBUG
	virtual void AssertValid() const;
	virtual void Dump(CDumpContext& dc) const;
#endif
    afx_msg void OnLButtonDown(UINT nFlags, CPoint point);
protected:

// 消息映射函数
protected:
	DECLARE_MESSAGE_MAP()
};

#ifndef _DEBUG  // MFCApplication1View.cpp 中的调试版本
inline CMFCApplication1Doc* CMFCApplication1View::GetDocument() const
   { return reinterpret_cast<CMFCApplication1Doc*>(m_pDocument); }
#endif

