// BasicSettingsDlg.cpp : 基本设置对话框实现

#include "pch.h"
#include "framework.h"
#include "MFCApplication1.h"
#include "BasicSettingsDlg.h"
#include "MFCApplication1Doc.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

CBasicSettingsDlg::CBasicSettingsDlg(CMFCApplication1Doc* pDoc)
    : CDialogEx(IDD_BASIC_SETTINGS)
    , m_pDoc(pDoc)
{
}

CBasicSettingsDlg::~CBasicSettingsDlg()
{
    m_fontForce.DeleteObject();
    m_fontError.DeleteObject();
    m_fontDisp.DeleteObject();
    m_fontTime.DeleteObject();
}

BEGIN_MESSAGE_MAP(CBasicSettingsDlg, CDialogEx)
    ON_BN_CLICKED(IDC_BUTTON_BGCOLOR, &CBasicSettingsDlg::OnBnClickedBgColor)
    ON_BN_CLICKED(IDC_BUTTON_FONT_FORCE, &CBasicSettingsDlg::OnBnClickedFontForce)
    ON_BN_CLICKED(IDC_BUTTON_FONT_ERROR, &CBasicSettingsDlg::OnBnClickedFontError)
    ON_BN_CLICKED(IDC_BUTTON_FONT_DISP, &CBasicSettingsDlg::OnBnClickedFontDisp)
    ON_BN_CLICKED(IDC_BUTTON_FONT_TIME, &CBasicSettingsDlg::OnBnClickedFontTime)
END_MESSAGE_MAP()

void CBasicSettingsDlg::DoDataExchange(CDataExchange* pDX)
{
    CDialogEx::DoDataExchange(pDX);
}

BOOL CBasicSettingsDlg::OnInitDialog()
{
    CDialogEx::OnInitDialog();

    if (!m_pDoc) return TRUE;

    PlotAppearance& app = m_pDoc->GetAppearance();
    SimParams& params = m_pDoc->GetParams();

    // 初始化背景色
    m_bgColor = app.bgColor;

    // 初始化字体
    m_fontForce.CreateFontIndirectW(&app.lfForceLabel);
    m_fontError.CreateFontIndirectW(&app.lfErrorLabel);
    m_fontDisp.CreateFontIndirectW(&app.lfDispLabel);
    m_fontTime.CreateFontIndirectW(&app.lfTimeLabel);

    // 初始化算法选择
    m_integratorIndex = (int)params.integrator;

    // 更新算法单选按钮
    switch (m_integratorIndex)
    {
    case 0: CheckRadioButton(IDC_RADIO_EULER, IDC_RADIO_RK4, IDC_RADIO_EULER); break;
    case 1: CheckRadioButton(IDC_RADIO_EULER, IDC_RADIO_RK4, IDC_RADIO_RK2); break;
    case 2: CheckRadioButton(IDC_RADIO_EULER, IDC_RADIO_RK4, IDC_RADIO_RK4); break;
    }

    // 更新字体示例显示
    SetDlgItemTextW(IDC_STATIC_FONT_FORCE, L"示例: 拉力/N");
    SetDlgItemTextW(IDC_STATIC_FONT_ERROR, L"示例: 误差/m");
    SetDlgItemTextW(IDC_STATIC_FONT_DISP, L"示例: 位移/m");
    SetDlgItemTextW(IDC_STATIC_FONT_TIME, L"示例: 时间/s");

    return TRUE;
}

void CBasicSettingsDlg::OnOK()
{
    if (!m_pDoc) return;

    PlotAppearance& app = m_pDoc->GetAppearance();
    SimParams& params = m_pDoc->GetParams();

    // 保存背景色
    app.bgColor = m_bgColor;

    // 保存算法选择
    if (IsDlgButtonChecked(IDC_RADIO_EULER))
        params.integrator = INT_EULER;
    else if (IsDlgButtonChecked(IDC_RADIO_RK2))
        params.integrator = INT_RK2;
    else
        params.integrator = INT_RK4;

    CDialogEx::OnOK();
}

void CBasicSettingsDlg::OnBnClickedBgColor()
{
    CColorDialog dlg(m_bgColor, CC_FULLOPEN);
    if (dlg.DoModal() == IDOK)
    {
        m_bgColor = dlg.GetColor();
    }
}

void CBasicSettingsDlg::OnBnClickedFontForce()
{
    LOGFONTW lf;
    m_fontForce.GetLogFont(&lf);

    CFontDialog dlg(&lf, CF_SCREENFONTS | CF_EFFECTS);
    if (dlg.DoModal() == IDOK)
    {
        m_fontForce.DeleteObject();
        m_fontForce.CreateFontIndirectW(&lf);
        m_pDoc->GetAppearance().lfForceLabel = lf;
        m_pDoc->GetAppearance().colorForceLabel = dlg.GetColor();
        SetDlgItemTextW(IDC_STATIC_FONT_FORCE, L"示例: 拉力/N (已更新)");
    }
}

void CBasicSettingsDlg::OnBnClickedFontError()
{
    LOGFONTW lf;
    m_fontError.GetLogFont(&lf);

    CFontDialog dlg(&lf, CF_SCREENFONTS | CF_EFFECTS);
    if (dlg.DoModal() == IDOK)
    {
        m_fontError.DeleteObject();
        m_fontError.CreateFontIndirectW(&lf);
        m_pDoc->GetAppearance().lfErrorLabel = lf;
        m_pDoc->GetAppearance().colorErrorLabel = dlg.GetColor();
        SetDlgItemTextW(IDC_STATIC_FONT_ERROR, L"示例: 误差/m (已更新)");
    }
}

void CBasicSettingsDlg::OnBnClickedFontDisp()
{
    LOGFONTW lf;
    m_fontDisp.GetLogFont(&lf);

    CFontDialog dlg(&lf, CF_SCREENFONTS | CF_EFFECTS);
    if (dlg.DoModal() == IDOK)
    {
        m_fontDisp.DeleteObject();
        m_fontDisp.CreateFontIndirectW(&lf);
        m_pDoc->GetAppearance().lfDispLabel = lf;
        m_pDoc->GetAppearance().colorDispLabel = dlg.GetColor();
        SetDlgItemTextW(IDC_STATIC_FONT_DISP, L"示例: 位移/m (已更新)");
    }
}

void CBasicSettingsDlg::OnBnClickedFontTime()
{
    LOGFONTW lf;
    m_fontTime.GetLogFont(&lf);

    CFontDialog dlg(&lf, CF_SCREENFONTS | CF_EFFECTS);
    if (dlg.DoModal() == IDOK)
    {
        m_fontTime.DeleteObject();
        m_fontTime.CreateFontIndirectW(&lf);
        m_pDoc->GetAppearance().lfTimeLabel = lf;
        m_pDoc->GetAppearance().colorTimeLabel = dlg.GetColor();
        SetDlgItemTextW(IDC_STATIC_FONT_TIME, L"示例: 时间/s (已更新)");
    }
}
