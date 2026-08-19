
// 26.4.20.shangji2View.h: CMy26420shangji2View 类的接口
//

#pragma once


class CMy26420shangji2View : public CView
{
protected: // 仅从序列化创建
	CMy26420shangji2View() noexcept;
	DECLARE_DYNCREATE(CMy26420shangji2View)

// 特性
public:
	CMy26420shangji2Doc* GetDocument() const;

// 操作
public:

// 重写
public:
	virtual void OnDraw(CDC* pDC);  // 重写以绘制该视图
	virtual BOOL PreCreateWindow(CREATESTRUCT& cs);
    virtual void OnInitialUpdate();
protected:
	virtual BOOL OnPreparePrinting(CPrintInfo* pInfo);
	virtual void OnBeginPrinting(CDC* pDC, CPrintInfo* pInfo);
	virtual void OnEndPrinting(CDC* pDC, CPrintInfo* pInfo);

// 实现
public:
	virtual ~CMy26420shangji2View();
#ifdef _DEBUG
	virtual void AssertValid() const;
	virtual void Dump(CDumpContext& dc) const;
#endif

protected:
	// windmill state copy
	float m_wmCenterX = 0;
	float m_wmCenterY = 0;
	float m_wmAngle = 0;
	int   m_wmDirection = 1;
	float m_wmSpeed = 5.0f;
	bool  m_wmRunning = false;

    UINT_PTR m_nTimerID = 0;
	BOOL m_doubleBuffered = TRUE;

	afx_msg void OnTimer(UINT_PTR nIDEvent);
	afx_msg void OnWmDirCw();
	afx_msg void OnWmDirCcw();
	afx_msg void OnWmSpeedFaster();
	afx_msg void OnWmSpeedSlower();
	afx_msg void OnWmAnimStart();
	afx_msg void OnWmAnimStop();
    afx_msg void OnLButtonDown(UINT nFlags, CPoint point);
    afx_msg BOOL OnEraseBkgnd(CDC* pDC);
// 生成的消息映射函数
protected:
	DECLARE_MESSAGE_MAP()
};

#ifndef _DEBUG  // 26.4.20.shangji2View.cpp 中的调试版本
inline CMy26420shangji2Doc* CMy26420shangji2View::GetDocument() const
   { return reinterpret_cast<CMy26420shangji2Doc*>(m_pDocument); }
#endif

