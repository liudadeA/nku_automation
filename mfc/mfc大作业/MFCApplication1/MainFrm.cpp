// MainFrm.cpp : CMainFrame 类的实现
// 太阳翼展开仿真 - 主框架窗口

#include "pch.h"
#include "framework.h"
#include "MFCApplication1.h"

#include "MainFrm.h"
#include "MFCApplication1Doc.h"
#include "MFCApplication1View.h"

#include "BasicSettingsDlg.h"
#include "ParamSettingsDlg.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

IMPLEMENT_DYNCREATE(CMainFrame, CFrameWnd)

BEGIN_MESSAGE_MAP(CMainFrame, CFrameWnd)
    ON_WM_CREATE()
    ON_WM_CONTEXTMENU()
    ON_COMMAND(ID_SETTINGS_BASIC, &CMainFrame::OnSettingsBasic)
    ON_COMMAND(ID_SETTINGS_PARAM, &CMainFrame::OnSettingsParam)
    ON_COMMAND(ID_CONTROL_START, &CMainFrame::OnControlStart)
    ON_COMMAND(ID_CONTROL_PAUSE, &CMainFrame::OnControlPause)
    ON_COMMAND(ID_CONTROL_STOP, &CMainFrame::OnControlStop)
    ON_COMMAND(ID_FILE_SAVE_STEP, &CMainFrame::OnSaveStep)
    ON_COMMAND(ID_FILE_SAVE_SIN, &CMainFrame::OnSaveSin)
    ON_COMMAND(ID_FILE_LOAD_STEP, &CMainFrame::OnLoadStep)
    ON_COMMAND(ID_FILE_LOAD_SIN, &CMainFrame::OnLoadSin)
END_MESSAGE_MAP()

static UINT indicators[] =
{
    ID_SEPARATOR,
    ID_INDICATOR_CAPS,
    ID_INDICATOR_NUM,
    ID_INDICATOR_SCRL,
};

CMainFrame::CMainFrame() noexcept
{
}

CMainFrame::~CMainFrame()
{
}

int CMainFrame::OnCreate(LPCREATESTRUCT lpCreateStruct)
{
    if (CFrameWnd::OnCreate(lpCreateStruct) == -1)
        return -1;

    // 只保留状态栏，不需要工具栏
    if (!m_wndStatusBar.Create(this))
    {
        TRACE0("未能创建状态栏\n");
        return -1;
    }
    m_wndStatusBar.SetIndicators(indicators, sizeof(indicators) / sizeof(UINT));

    return 0;
}

BOOL CMainFrame::PreCreateWindow(CREATESTRUCT& cs)
{
    if (!CFrameWnd::PreCreateWindow(cs))
        return FALSE;

    cs.cx = 1200;
    cs.cy = 800;

    return TRUE;
}

CMFCApplication1Doc* CMainFrame::GetDoc()
{
    return dynamic_cast<CMFCApplication1Doc*>(GetActiveDocument());
}

CMFCApplication1View* CMainFrame::GetView()
{
    return dynamic_cast<CMFCApplication1View*>(GetActiveView());
}

// ============================================================
// 菜单命令处理
// ============================================================

void CMainFrame::OnSettingsBasic()
{
    CMFCApplication1Doc* pDoc = GetDoc();
    if (!pDoc) return;

    CBasicSettingsDlg dlg(pDoc);
    if (dlg.DoModal() == IDOK)
    {
        // 设置变更后刷新视图
        CMFCApplication1View* pView = GetView();
        if (pView)
            pView->Invalidate();
    }
}

void CMainFrame::OnSettingsParam()
{
    CMFCApplication1Doc* pDoc = GetDoc();
    CMFCApplication1View* pView = GetView();
    if (!pDoc || !pView) return;

    CParamSettingsDlg dlg(pDoc);
    if (dlg.DoModal() == IDOK)
    {
        pDoc->ResetSimulation();
        pView->Invalidate();
    }
}

void CMainFrame::OnControlStart()
{
    CMFCApplication1Doc* pDoc = GetDoc();
    CMFCApplication1View* pView = GetView();
    if (!pDoc || !pView) return;

    pDoc->StartSimulation();
    pView->StartTimer();
}

void CMainFrame::OnControlPause()
{
    CMFCApplication1Doc* pDoc = GetDoc();
    CMFCApplication1View* pView = GetView();
    if (!pDoc || !pView) return;

    pDoc->PauseSimulation();
    pView->StopTimer();
}

void CMainFrame::OnControlStop()
{
    CMFCApplication1Doc* pDoc = GetDoc();
    CMFCApplication1View* pView = GetView();
    if (!pDoc || !pView) return;

    pDoc->StopSimulation();
    pView->StopTimer();
    pView->Invalidate();
}

void CMainFrame::OnSaveStep()
{
    CMFCApplication1Doc* pDoc = GetDoc();
    if (!pDoc) return;

    CFileDialog dlg(FALSE, L"txt", L"StepTest", OFN_OVERWRITEPROMPT,
                    L"参数文件 (*.txt)|*.txt|所有文件 (*.*)|*.*||", this);
    if (dlg.DoModal() == IDOK)
    {
        pDoc->SaveParams(dlg.GetPathName());
    }
}

void CMainFrame::OnSaveSin()
{
    CMFCApplication1Doc* pDoc = GetDoc();
    if (!pDoc) return;

    CFileDialog dlg(FALSE, L"txt", L"SinTest", OFN_OVERWRITEPROMPT,
                    L"参数文件 (*.txt)|*.txt|所有文件 (*.*)|*.*||", this);
    if (dlg.DoModal() == IDOK)
    {
        pDoc->SaveParams(dlg.GetPathName());
    }
}

void CMainFrame::OnLoadStep()
{
    CMFCApplication1Doc* pDoc = GetDoc();
    CMFCApplication1View* pView = GetView();
    if (!pDoc) return;

    CFileDialog dlg(TRUE, L"txt", L"StepTest", OFN_FILEMUSTEXIST,
                    L"参数文件 (*.txt)|*.txt|所有文件 (*.*)|*.*||", this);
    if (dlg.DoModal() == IDOK)
    {
        pDoc->LoadParams(dlg.GetPathName());
        if (pView)
        {
            pDoc->ResetSimulation();
            pView->Invalidate();
        }
    }
}

void CMainFrame::OnLoadSin()
{
    CMFCApplication1Doc* pDoc = GetDoc();
    CMFCApplication1View* pView = GetView();
    if (!pDoc) return;

    CFileDialog dlg(TRUE, L"txt", L"SinTest", OFN_FILEMUSTEXIST,
                    L"参数文件 (*.txt)|*.txt|所有文件 (*.*)|*.*||", this);
    if (dlg.DoModal() == IDOK)
    {
        pDoc->LoadParams(dlg.GetPathName());
        if (pView)
        {
            pDoc->ResetSimulation();
            pView->Invalidate();
        }
    }
}

void CMainFrame::OnContextMenu(CWnd* pWnd, CPoint point)
{
    // 右键快捷菜单（"控制"菜单）
    CMenu menu;
    menu.CreatePopupMenu();
    menu.AppendMenuW(MF_STRING, ID_CONTROL_START, L"开始(&S)\tAlt+S");
    menu.AppendMenuW(MF_STRING, ID_CONTROL_PAUSE, L"暂停(&P)\tAlt+P");
    menu.AppendMenuW(MF_STRING, ID_CONTROL_STOP, L"停止(&T)\tAlt+T");

    menu.TrackPopupMenu(TPM_LEFTALIGN | TPM_RIGHTBUTTON, point.x, point.y, this);
}

#ifdef _DEBUG
void CMainFrame::AssertValid() const
{
    CFrameWnd::AssertValid();
}

void CMainFrame::Dump(CDumpContext& dc) const
{
    CFrameWnd::Dump(dc);
}
#endif
