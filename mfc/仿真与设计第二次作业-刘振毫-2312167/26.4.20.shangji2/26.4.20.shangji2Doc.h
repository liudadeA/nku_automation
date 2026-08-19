
// 26.4.20.shangji2Doc.h: CMy26420shangji2Doc 类的接口
//


#pragma once


class CMy26420shangji2Doc : public CDocument
{
protected: // 仅从序列化创建
	CMy26420shangji2Doc() noexcept;
	DECLARE_DYNCREATE(CMy26420shangji2Doc)

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
	virtual ~CMy26420shangji2Doc();
#if 1
	// 风车状态
	float m_wmCenterX = 0.0f;
	float m_wmCenterY = 0.0f;
	float m_wmAngle = 0.0f;
	int   m_wmDirection = 1; // 1 clockwise, -1 counter
	float m_wmSpeed = 5.0f; // degrees per tick
	bool  m_wmRunning = false;

	void SetDefaultWindmillState();
#endif
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
