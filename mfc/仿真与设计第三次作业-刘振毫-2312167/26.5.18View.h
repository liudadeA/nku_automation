
// 26.5.18View.h: CMy26518View 类的接口
//

#pragma once


class CMy26518View : public CView
{
protected: // 仅从序列化创建
	CMy26518View() noexcept;
	DECLARE_DYNCREATE(CMy26518View)

// 特性
public:
	CMy26518Doc* GetDocument() const;

// 操作
public:
	void ApplySloganSettings();

// 重写
public:
	virtual void OnDraw(CDC* pDC);
	virtual BOOL PreCreateWindow(CREATESTRUCT& cs);
	virtual void OnInitialUpdate();
protected:
	virtual BOOL OnPreparePrinting(CPrintInfo* pInfo);
	virtual void OnBeginPrinting(CDC* pDC, CPrintInfo* pInfo);
	virtual void OnEndPrinting(CDC* pDC, CPrintInfo* pInfo);

// 实现
public:
	virtual ~CMy26518View();
#ifdef _DEBUG
	virtual void AssertValid() const;
	virtual void Dump(CDumpContext& dc) const;
#endif

protected:
	CFont m_fontSlogan;
	CImage m_imgBg;
	int m_nScrollOffset;
	UINT_PTR m_nTimerID;

	afx_msg void OnSetSlogan();
	afx_msg void OnTimer(UINT_PTR nIDEvent);
	afx_msg void OnLButtonDblClk(UINT nFlags, CPoint point);
	afx_msg BOOL OnEraseBkgnd(CDC* pDC);

// 生成的消息映射函数
protected:
	DECLARE_MESSAGE_MAP()
};

#ifndef _DEBUG  // 26.5.18View.cpp 中的调试版本
inline CMy26518Doc* CMy26518View::GetDocument() const
   { return reinterpret_cast<CMy26518Doc*>(m_pDocument); }
#endif
