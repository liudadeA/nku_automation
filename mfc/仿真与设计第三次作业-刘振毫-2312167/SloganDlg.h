#pragma once
#include "afxdialogex.h"

class CSloganDlg : public CDialogEx
{
    DECLARE_DYNAMIC(CSloganDlg)

public:
    CSloganDlg(CWnd* pParent = nullptr);
    virtual ~CSloganDlg();

    CString m_strSlogan;
    LOGFONT m_lf;
    COLORREF m_color;
    int m_nAlign;
    int m_nVerticalPos;
    CString m_strBgImage;
    BOOL m_bScroll;
    int m_nScrollInterval;

    enum { IDD = IDD_SLOGAN_DLG };

protected:
    virtual void DoDataExchange(CDataExchange* pDX);
    virtual BOOL OnInitDialog();
    virtual void OnOK();

    afx_msg void OnFontBtn();
    afx_msg void OnColorBtn();
    afx_msg void OnBgBtn();
    afx_msg void OnAlignLeft();
    afx_msg void OnAlignCenter();
    afx_msg void OnAlignRight();
    afx_msg void OnScrollToggle();

    DECLARE_MESSAGE_MAP()
};
