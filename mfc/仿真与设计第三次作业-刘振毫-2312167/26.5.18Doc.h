
// 26.5.18Doc.h: CMy26518Doc 类的接口
//

#pragma once


class CMy26518Doc : public CDocument
{
protected: // 仅从序列化创建
	CMy26518Doc() noexcept;
	DECLARE_DYNCREATE(CMy26518Doc)

// 特性
public:
	CString GetSloganText() const { return m_strSlogan; }
	LOGFONT GetLogFont() const { return m_lfSlogan; }
	COLORREF GetTextColor() const { return m_colorSlogan; }
	int GetAlignment() const { return m_nAlign; }
	int GetVerticalPos() const { return m_nVerticalPos; }
	CString GetBgImage() const { return m_strBgImage; }
	BOOL IsScrollEnabled() const { return m_bScroll; }
	int GetScrollInterval() const { return m_nScrollInterval; }

	void SetSloganText(const CString& str) { m_strSlogan = str; }
	void SetLogFont(const LOGFONT& lf) { m_lfSlogan = lf; }
	void SetTextColor(COLORREF c) { m_colorSlogan = c; }
	void SetAlignment(int n) { m_nAlign = n; }
	void SetVerticalPos(int n) { m_nVerticalPos = n; }
	void SetBgImage(const CString& str) { m_strBgImage = str; }
	void SetScrollEnabled(BOOL b) { m_bScroll = b; }
	void SetScrollInterval(int n) { m_nScrollInterval = n; }

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
	virtual ~CMy26518Doc();
#ifdef _DEBUG
	virtual void AssertValid() const;
	virtual void Dump(CDumpContext& dc) const;
#endif

protected:
	CString m_strSlogan;
	LOGFONT m_lfSlogan;
	COLORREF m_colorSlogan;
	int m_nAlign;
	int m_nVerticalPos;
	CString m_strBgImage;
	BOOL m_bScroll;
	int m_nScrollInterval;

// 生成的消息映射函数
protected:
	DECLARE_MESSAGE_MAP()

#ifdef SHARED_HANDLERS
	// 用于为搜索处理程序设置搜索内容的 Helper 函数
	void SetSearchContent(const CString& value);
#endif // SHARED_HANDLERS
};
