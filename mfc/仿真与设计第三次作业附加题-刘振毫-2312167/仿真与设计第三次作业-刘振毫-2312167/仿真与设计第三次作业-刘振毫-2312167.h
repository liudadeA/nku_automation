
// 仿真与设计第三次作业-刘振毫-2312167.h: 仿真与设计第三次作业-刘振毫-2312167 应用程序的主头文件
//
#pragma once

#ifndef __AFXWIN_H__
	#error "在包含此文件之前包含 'pch.h' 以生成 PCH"
#endif

#include "resource.h"       // 主符号


// C仿真与设计第三次作业刘振毫2312167App:
// 有关此类的实现，请参阅 仿真与设计第三次作业-刘振毫-2312167.cpp
//

class C仿真与设计第三次作业刘振毫2312167App : public CWinApp
{
public:
	C仿真与设计第三次作业刘振毫2312167App() noexcept;


// 重写
public:
	virtual BOOL InitInstance();
	virtual int ExitInstance();

// 实现
	afx_msg void OnAppAbout();
	DECLARE_MESSAGE_MAP()
};

extern C仿真与设计第三次作业刘振毫2312167App theApp;
