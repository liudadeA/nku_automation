#include "pch.h"
#include "framework.h"
#include "26.5.18.h"
#include "SloganDlg.h"
#include "Resource.h"

IMPLEMENT_DYNAMIC(CSloganDlg, CDialogEx)

CSloganDlg::CSloganDlg(CWnd* pParent)
    : CDialogEx(IDD_SLOGAN_DLG, pParent)
{
    m_strSlogan = _T("相信自己");
    memset(&m_lf, 0, sizeof(m_lf));
    m_lf.lfHeight = -48;
    m_lf.lfWeight = FW_NORMAL;
    m_lf.lfCharSet = DEFAULT_CHARSET;
    m_lf.lfQuality = CLEARTYPE_QUALITY;
    _tcscpy_s(m_lf.lfFaceName, LF_FACESIZE, _T("微软雅黑"));

    m_color = RGB(255, 50, 50);
    m_nAlign = 1;
    m_nVerticalPos = 100;
    m_strBgImage = _T("");
    m_bScroll = FALSE;
    m_nScrollInterval = 50;
}

CSloganDlg::~CSloganDlg()
{
}

BEGIN_MESSAGE_MAP(CSloganDlg, CDialogEx)
    ON_BN_CLICKED(IDC_SLOGAN_FONT_BTN, &CSloganDlg::OnFontBtn)
    ON_BN_CLICKED(IDC_SLOGAN_COLOR_BTN, &CSloganDlg::OnColorBtn)
    ON_BN_CLICKED(IDC_SLOGAN_BG_BTN, &CSloganDlg::OnBgBtn)
    ON_BN_CLICKED(IDC_SLOGAN_ALIGN_LEFT, &CSloganDlg::OnAlignLeft)
    ON_BN_CLICKED(IDC_SLOGAN_ALIGN_CENTER, &CSloganDlg::OnAlignCenter)
    ON_BN_CLICKED(IDC_SLOGAN_ALIGN_RIGHT, &CSloganDlg::OnAlignRight)
    ON_BN_CLICKED(IDC_SLOGAN_SCROLL, &CSloganDlg::OnScrollToggle)
END_MESSAGE_MAP()

void CSloganDlg::DoDataExchange(CDataExchange* pDX)
{
    CDialogEx::DoDataExchange(pDX);
    DDX_Text(pDX, IDC_SLOGAN_TEXT, m_strSlogan);
    DDX_Text(pDX, IDC_SLOGAN_VPOS, m_nVerticalPos);
    DDV_MinMaxInt(pDX, m_nVerticalPos, 0, 2000);
    DDX_Text(pDX, IDC_SLOGAN_SCROLL_INTERVAL, m_nScrollInterval);
    DDV_MinMaxInt(pDX, m_nScrollInterval, 10, 500);
    DDX_Radio(pDX, IDC_SLOGAN_ALIGN_LEFT, m_nAlign);
    DDX_Check(pDX, IDC_SLOGAN_SCROLL, m_bScroll);
}

BOOL CSloganDlg::OnInitDialog()
{
    CDialogEx::OnInitDialog();

    CWnd* pWnd = GetDlgItem(IDC_SLOGAN_SCROLL_INTERVAL);
    if (pWnd) pWnd->EnableWindow(m_bScroll);

    SetWindowText(_T("标语设置"));
    SetDlgItemText(IDC_SLOGAN_FONT_BTN, _T("选择字体..."));
    SetDlgItemText(IDC_SLOGAN_COLOR_BTN, _T("选择颜色..."));
    SetDlgItemText(IDC_SLOGAN_BG_BTN, _T("选择背景图片..."));
    SetDlgItemText(IDOK, _T("确定"));
    SetDlgItemText(IDCANCEL, _T("取消"));

    if (m_nAlign < 0 || m_nAlign > 2) m_nAlign = 1;
    UpdateData(FALSE);

    return TRUE;
}

void CSloganDlg::OnOK()
{
    UpdateData(TRUE);
    CDialogEx::OnOK();
}

void CSloganDlg::OnFontBtn()
{
    UpdateData(TRUE);

    CFontDialog dlg(&m_lf, CF_EFFECTS | CF_SCREENFONTS, nullptr, this);
    dlg.m_cf.rgbColors = m_color;

    if (dlg.DoModal() == IDOK)
    {
        dlg.GetCurrentFont(&m_lf);
        m_color = dlg.GetColor();
        UpdateData(FALSE);
    }
}

void CSloganDlg::OnColorBtn()
{
    UpdateData(TRUE);

    CColorDialog dlg(m_color, CC_FULLOPEN, this);
    if (dlg.DoModal() == IDOK)
    {
        m_color = dlg.GetColor();
        UpdateData(FALSE);
    }
}

void CSloganDlg::OnBgBtn()
{
    UpdateData(TRUE);

    CFileDialog dlg(TRUE, _T("*.bmp;*.jpg;*.jpeg;*.png;*.gif"), nullptr,
        OFN_FILEMUSTEXIST | OFN_HIDEREADONLY,
        _T("图片文件 (*.bmp;*.jpg;*.png;*.gif)|*.bmp;*.jpg;*.jpeg;*.png;*.gif|所有文件 (*.*)|*.*||"),
        this);

    if (dlg.DoModal() == IDOK)
    {
        m_strBgImage = dlg.GetPathName();
        UpdateData(FALSE);
    }
}

void CSloganDlg::OnAlignLeft()
{
    m_nAlign = 0;
    UpdateData(FALSE);
}

void CSloganDlg::OnAlignCenter()
{
    m_nAlign = 1;
    UpdateData(FALSE);
}

void CSloganDlg::OnAlignRight()
{
    m_nAlign = 2;
    UpdateData(FALSE);
}

void CSloganDlg::OnScrollToggle()
{
    m_bScroll = IsDlgButtonChecked(IDC_SLOGAN_SCROLL);
    CWnd* pWnd = GetDlgItem(IDC_SLOGAN_SCROLL_INTERVAL);
    if (pWnd) pWnd->EnableWindow(m_bScroll);
}
