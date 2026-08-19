
// MFCApplicationdocxView.h: CMFCApplicationdocxView 类的接口
//

#pragma once

class CMFCApplicationdocxDoc;


class CMFCApplicationdocxView : public CView
{
private:
	COLORREF m_nColors[4]; // 颜色值
protected: // 仅从序列化创建
	CMFCApplicationdocxView() noexcept;
	DECLARE_DYNCREATE(CMFCApplicationdocxView)

// 特性
public:
	CMFCApplicationdocxDoc* GetDocument() const;

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
	virtual ~CMFCApplicationdocxView();
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
public:
	afx_msg void OnLButtonDown(UINT nFlags, CPoint point);
	afx_msg void OnOptBlack();
	afx_msg void OnOptBlue();
	afx_msg void OnOptEmpty();
	afx_msg void OnOptRed();
	afx_msg void OnOptGreen();
  afx_msg void OnUpdateOptBlack(CCmdUI* pCmdUI);
	afx_msg void OnUpdateOptRed(CCmdUI* pCmdUI);
  afx_msg void OnUpdateOptBlue(CCmdUI* pCmdUI);
	afx_msg void OnUpdateOptGreen(CCmdUI* pCmdUI);
};

#ifndef _DEBUG  // MFCApplicationdocxView.cpp 中的调试版本
inline CMFCApplicationdocxDoc* CMFCApplicationdocxView::GetDocument() const
   { return reinterpret_cast<CMFCApplicationdocxDoc*>(m_pDocument); }
#endif

