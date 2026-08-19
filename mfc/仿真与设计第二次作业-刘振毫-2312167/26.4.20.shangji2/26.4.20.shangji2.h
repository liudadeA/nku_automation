
// 26.4.20.shangji2.h: 26.4.20.shangji2 应用程序的主头文件
//
#pragma once

#ifndef __AFXWIN_H__
	#error "在包含此文件之前包含 'pch.h' 以生成 PCH"
#endif

#include "resource.h"       // 主符号


// CMy26420shangji2App:
// 有关此类的实现，请参阅 26.4.20.shangji2.cpp
//

class CMy26420shangji2App : public CWinApp
{
public:
	CMy26420shangji2App() noexcept;


// 重写
public:
	virtual BOOL InitInstance();
	virtual int ExitInstance();

// 实现
	afx_msg void OnAppAbout();
	DECLARE_MESSAGE_MAP()
};

extern CMy26420shangji2App theApp;
