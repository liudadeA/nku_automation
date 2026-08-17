
// 2026.4.13View.h: CMy2026413View 类的接口
//

#pragma once


class CMy2026413View : public CView
{
protected: // 仅从序列化创建
	CMy2026413View() noexcept;
	DECLARE_DYNCREATE(CMy2026413View)

// 特性
public:
	CMy2026413Doc* GetDocument() const;

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
	virtual ~CMy2026413View();
#ifdef _DEBUG
	virtual void AssertValid() const;
	virtual void Dump(CDumpContext& dc) const;
#endif

protected:

// 生成的消息映射函数
protected:
	afx_msg void OnFilePrintPreview();
	afx_msg void OnRButtonUp(UINT nFlags, CPoint point);
	afx_msg void OnContextMenu(CWnd* pWnd, CPoint point);
	DECLARE_MESSAGE_MAP()
};

#ifndef _DEBUG  // 2026.4.13View.cpp 中的调试版本
inline CMy2026413Doc* CMy2026413View::GetDocument() const
   { return reinterpret_cast<CMy2026413Doc*>(m_pDocument); }
#endif

