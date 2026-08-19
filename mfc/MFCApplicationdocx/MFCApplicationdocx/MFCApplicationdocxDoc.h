
// MFCApplicationdocxDoc.h: CMFCApplicationdocxDoc 类的接口
//


#pragma once


class CMFCApplicationdocxDoc : public CDocument
{
private:
	int m_nColorIndex;// 代表颜色
public:
	void SetColor(int index);
	int GetColor();

private:
	CString m_str;
	// 显示的字符串
	CPoint m_point;
	// 鼠标点击位置
public:
	void Set(CPoint point, CString string);
	void Get(CPoint& point, CString& string);

protected: // 仅从序列化创建
	CMFCApplicationdocxDoc() noexcept;
	DECLARE_DYNCREATE(CMFCApplicationdocxDoc)

// 特性
public:

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
	virtual ~CMFCApplicationdocxDoc();
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
