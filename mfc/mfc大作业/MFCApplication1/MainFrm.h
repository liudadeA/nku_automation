// MainFrm.h : CMainFrame 类的接口
// 太阳翼展开仿真 - 主框架窗口

#pragma once

class CMFCApplication1Doc;
class CMFCApplication1View;

class CMainFrame : public CFrameWnd
{
protected:
    CMainFrame() noexcept;
    DECLARE_DYNCREATE(CMainFrame)

public:
    virtual ~CMainFrame();
    virtual BOOL PreCreateWindow(CREATESTRUCT& cs);

#ifdef _DEBUG
    virtual void AssertValid() const;
    virtual void Dump(CDumpContext& dc) const;
#endif

protected:
    CStatusBar        m_wndStatusBar;

    // 消息处理
    afx_msg int OnCreate(LPCREATESTRUCT lpCreateStruct);
    afx_msg void OnSettingsBasic();
    afx_msg void OnSettingsParam();
    afx_msg void OnControlStart();
    afx_msg void OnControlPause();
    afx_msg void OnControlStop();
    afx_msg void OnSaveStep();
    afx_msg void OnSaveSin();
    afx_msg void OnLoadStep();
    afx_msg void OnLoadSin();
    afx_msg void OnContextMenu(CWnd* pWnd, CPoint point);

    DECLARE_MESSAGE_MAP()

private:
    CMFCApplication1Doc* GetDoc();
    CMFCApplication1View* GetView();
};
