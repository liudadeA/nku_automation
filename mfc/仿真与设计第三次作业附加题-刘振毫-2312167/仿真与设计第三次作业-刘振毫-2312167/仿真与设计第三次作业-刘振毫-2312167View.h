
// 仿真与设计第三次作业-刘振毫-2312167View.h: C仿真与设计第三次作业刘振毫2312167View 类的接口
//

#pragma once


class C仿真与设计第三次作业刘振毫2312167View : public CView
{
protected: // 仅从序列化创建
	C仿真与设计第三次作业刘振毫2312167View() noexcept;
	DECLARE_DYNCREATE(C仿真与设计第三次作业刘振毫2312167View)

// 特性
public:
	C仿真与设计第三次作业刘振毫2312167Doc* GetDocument() const;

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
	virtual ~C仿真与设计第三次作业刘振毫2312167View();
#ifdef _DEBUG
	virtual void AssertValid() const;
	virtual void Dump(CDumpContext& dc) const;
#endif

protected:

// 生成的消息映射函数
protected:
	DECLARE_MESSAGE_MAP()
};

#ifndef _DEBUG  // 仿真与设计第三次作业-刘振毫-2312167View.cpp 中的调试版本
inline C仿真与设计第三次作业刘振毫2312167Doc* C仿真与设计第三次作业刘振毫2312167View::GetDocument() const
   { return reinterpret_cast<C仿真与设计第三次作业刘振毫2312167Doc*>(m_pDocument); }
#endif

