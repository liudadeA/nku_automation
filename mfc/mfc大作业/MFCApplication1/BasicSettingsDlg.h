// BasicSettingsDlg.h : 基本设置对话框
// 太阳翼展开仿真 - 基本设置（颜色、字体、算法）

#pragma once
#include "MFCApplication1Doc.h"

class CMFCApplication1Doc;

class CBasicSettingsDlg : public CDialogEx
{
public:
    CBasicSettingsDlg(CMFCApplication1Doc* pDoc);
    virtual ~CBasicSettingsDlg();

#ifdef AFX_DESIGN_TIME
    enum { IDD = IDD_BASIC_SETTINGS };
#endif

protected:
    virtual void DoDataExchange(CDataExchange* pDX);
    virtual BOOL OnInitDialog();
    virtual void OnOK();

    DECLARE_MESSAGE_MAP()

private:
    CMFCApplication1Doc* m_pDoc;

    // 字体对象
    CFont m_fontForce, m_fontError, m_fontDisp, m_fontTime;

    // 背景颜色
    COLORREF m_bgColor = RGB(30, 30, 30);

    // 算法选择 (0=欧拉法, 1=RK2, 2=RK4)
    int m_integratorIndex = 2;

    // 控件事件
    afx_msg void OnBnClickedBgColor();
    afx_msg void OnBnClickedFontForce();
    afx_msg void OnBnClickedFontError();
    afx_msg void OnBnClickedFontDisp();
    afx_msg void OnBnClickedFontTime();
};
