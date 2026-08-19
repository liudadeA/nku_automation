
// 仿真与设计第三次作业-刘振毫-2312167Doc.h: C仿真与设计第三次作业刘振毫2312167Doc 类的接口
//


#pragma once


class C仿真与设计第三次作业刘振毫2312167Doc : public CDocument
{
protected: // 仅从序列化创建
	C仿真与设计第三次作业刘振毫2312167Doc() noexcept;
	DECLARE_DYNCREATE(C仿真与设计第三次作业刘振毫2312167Doc)

// 特性
public:
	int      m_nShapeType;     // 0=矩形, 1=椭圆, 2=直线
	CPoint   m_ptTopLeft;
	CPoint   m_ptBottomRight;
	int      m_nLineStyle;     // 0=PS_SOLID, 1=PS_DASH, 2=PS_DASHDOT
	COLORREF m_color;
	double   m_dArea;
	double   m_dPerimeter;
	double   m_dLength;
	bool     m_bDraw;

// 操作
public:

// 重写
public:
	virtual BOOL OnNewDocument();
	virtual void Serialize(CArchive& ar);
#ifdef SHARED_HANDLERS
	virtual void InitializeSearchContent();
	virtual void OnDrawThumbnail(CDC& dc, LPRECT lprcBounds);
#endif // SHARED_HANDLERS

// 实现
public:
	virtual ~C仿真与设计第三次作业刘振毫2312167Doc();
#ifdef _DEBUG
	virtual void AssertValid() const;
	virtual void Dump(CDumpContext& dc) const;
#endif

protected:

// 生成的消息映射函数
protected:
	DECLARE_MESSAGE_MAP()

#ifdef SHARED_HANDLERS
	// 用于为搜索处理程序设置搜索内容的 Helper 函数
	void SetSearchContent(const CString& value);
#endif // SHARED_HANDLERS
};
