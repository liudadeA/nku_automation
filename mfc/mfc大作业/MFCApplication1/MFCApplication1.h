// MFCApplication1.h : MFCApplication1 应用程序的主头文件

#pragma once

#ifndef __AFXWIN_H__
    #error "在包含此文件之前包含 'pch.h' 以生成 PCH"
#endif

#include "resource.h"

class CMFCApplication1App : public CWinApp
{
public:
    CMFCApplication1App() noexcept;

    virtual BOOL InitInstance();
    virtual int ExitInstance();

    afx_msg void OnAppAbout();
    DECLARE_MESSAGE_MAP()
};

extern CMFCApplication1App theApp;
