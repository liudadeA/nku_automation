
// 26.4.20.shangji3View.h: CMy26420shangji3View 类的接口
//

#pragma once
#include <atlimage.h>


class CMy26420shangji3View : public CView
{
protected: // 仅从序列化创建
	CMy26420shangji3View() noexcept;
	DECLARE_DYNCREATE(CMy26420shangji3View)

// 新增成员: 位图显示与交互
public:
	virtual void OnInitialUpdate();
protected:
    CImage  m_image;
	int     m_dispW; // 当前显示宽度
	int     m_dispH; // 当前显示高度
	bool    m_bShowWarn;

// 特性
public:
	CMy26420shangji3Doc* GetDocument() const;

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
	virtual ~CMy26420shangji3View();
#ifdef _DEBUG
	virtual void AssertValid() const;
	virtual void Dump(CDumpContext& dc) const;
#endif

protected:

	afx_msg void OnLButtonDown(UINT nFlags, CPoint point);
	afx_msg BOOL OnEraseBkgnd(CDC* pDC);

// 生成的消息映射函数
protected:
	DECLARE_MESSAGE_MAP()
};

#ifndef _DEBUG  // 26.4.20.shangji3View.cpp 中的调试版本
inline CMy26420shangji3Doc* CMy26420shangji3View::GetDocument() const
   { return reinterpret_cast<CMy26420shangji3Doc*>(m_pDocument); }
#endif

