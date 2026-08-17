
// 26.4.13View.h: CMy26413View 类的接口
//

#pragma once


class CMy26413View : public CView
{
protected: // 仅从序列化创建
	CMy26413View() noexcept;
	DECLARE_DYNCREATE(CMy26413View)

// 特性
public:
	CMy26413Doc* GetDocument() const;

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
	virtual ~CMy26413View();
#ifdef _DEBUG
	virtual void AssertValid() const;
	virtual void Dump(CDumpContext& dc) const;
#endif

protected:

// 生成的消息映射函数
protected:
	DECLARE_MESSAGE_MAP()
public:
	afx_msg void OnLButtonDown(UINT nFlags, CPoint point);
};

#ifndef _DEBUG  // 26.4.13View.cpp 中的调试版本
inline CMy26413Doc* CMy26413View::GetDocument() const
   { return reinterpret_cast<CMy26413Doc*>(m_pDocument); }
#endif

