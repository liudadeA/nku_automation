// ParamSettingsDlg.cpp : 参数设置对话框实现

#include "pch.h"
#include "framework.h"
#include "MFCApplication1.h"
#include "ParamSettingsDlg.h"
#include "MFCApplication1Doc.h"
#include "MFCApplication1View.h"
#include "MainFrm.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

CParamSettingsDlg::CParamSettingsDlg(CMFCApplication1Doc* pDoc)
    : CDialogEx(IDD_PARAM_SETTINGS)
    , m_pDoc(pDoc)
{
}

CParamSettingsDlg::~CParamSettingsDlg()
{
}

// CLedStatic 消息映射
BEGIN_MESSAGE_MAP(CLedStatic, CStatic)
    ON_WM_PAINT()
END_MESSAGE_MAP()

void CLedStatic::OnPaint()
{
    CPaintDC dc(this);
    CRect rc; GetClientRect(&rc);
    dc.FillSolidRect(&rc, m_color);
    dc.Draw3dRect(&rc, RGB(100, 100, 100), RGB(60, 60, 60));
}

BEGIN_MESSAGE_MAP(CParamSettingsDlg, CDialogEx)
    ON_BN_CLICKED(IDC_BUTTON_START, &CParamSettingsDlg::OnBnClickedStart)
    ON_BN_CLICKED(IDC_BUTTON_PAUSE, &CParamSettingsDlg::OnBnClickedPause)
    ON_BN_CLICKED(IDC_BUTTON_STOP, &CParamSettingsDlg::OnBnClickedStop)
    ON_WM_HSCROLL()
    ON_WM_TIMER()
    ON_EN_CHANGE(IDC_EDIT_KP, &CParamSettingsDlg::OnEnChangeKp)
    ON_EN_CHANGE(IDC_EDIT_KI, &CParamSettingsDlg::OnEnChangeKi)
    ON_EN_CHANGE(IDC_EDIT_KD, &CParamSettingsDlg::OnEnChangeKd)
    ON_BN_CLICKED(IDC_RADIO_CONSTANT, &CParamSettingsDlg::OnBnClickedRadioConstant)
    ON_BN_CLICKED(IDC_RADIO_QUADRATIC, &CParamSettingsDlg::OnBnClickedRadioQuadratic)
END_MESSAGE_MAP()

void CParamSettingsDlg::DoDataExchange(CDataExchange* pDX)
{
    CDialogEx::DoDataExchange(pDX);
}

BOOL CParamSettingsDlg::OnInitDialog()
{
    CDialogEx::OnInitDialog();

    if (!m_pDoc) return TRUE;

    SimParams& p = m_pDoc->GetParams();

    // 复制参数到本地成员
    m_k = p.k;
    m_g = p.g;
    m_m1 = p.m1;
    m_theta = p.theta;
    m_kp = p.kp;
    m_ki = p.ki;
    m_kd = p.kd;
    m_targetType = (int)p.targetType;
    m_ld_constant = p.ld_constant;
    m_A = p.A;
    m_B = p.B;
    m_simTime = p.simTime;
    m_simStep = p.simStep;
    m_maxDisp = p.maxDisplacement;

    // 先初始化PID滑动条，避免SetDlgItemTextW触发EN_CHANGE时滑块未就绪
    m_sliderKp.SubclassDlgItem(IDC_SLIDER_KP, this);
    m_sliderKi.SubclassDlgItem(IDC_SLIDER_KI, this);
    m_sliderKd.SubclassDlgItem(IDC_SLIDER_KD, this);

    m_sliderKp.SetRange(0, 5000);
    m_sliderKi.SetRange(0, 5000);
    m_sliderKd.SetRange(0, 5000);

    m_sliderKp.SetPos((int)(m_kp * 10));
    m_sliderKi.SetPos((int)(m_ki * 10));
    m_sliderKd.SetPos((int)(m_kd * 10));

    // 设置格式化数值到编辑框
    CString str;
    str.Format(L"%.2f", m_k);     SetDlgItemTextW(IDC_EDIT_K, str);
    str.Format(L"%.2f", m_g);     SetDlgItemTextW(IDC_EDIT_G, str);
    str.Format(L"%.1f", m_m1);    SetDlgItemTextW(IDC_EDIT_M1, str);
    str.Format(L"%.3f", m_theta); SetDlgItemTextW(IDC_EDIT_THETA, str);

    str.Format(L"%.1f", m_kp); SetDlgItemTextW(IDC_EDIT_KP, str);
    str.Format(L"%.1f", m_ki); SetDlgItemTextW(IDC_EDIT_KI, str);
    str.Format(L"%.1f", m_kd); SetDlgItemTextW(IDC_EDIT_KD, str);

    str.Format(L"%.2f", m_ld_constant); SetDlgItemTextW(IDC_EDIT_TARGET_VALUE, str);
    str.Format(L"%.3f", m_A); SetDlgItemTextW(IDC_EDIT_A, str);
    str.Format(L"%.3f", m_B); SetDlgItemTextW(IDC_EDIT_B, str);

    str.Format(L"%.0f", m_simTime);  SetDlgItemTextW(IDC_EDIT_SIM_TIME, str);
    str.Format(L"%.3f", m_simStep);  SetDlgItemTextW(IDC_EDIT_SIM_STEP, str);
    str.Format(L"%.2f", m_maxDisp);  SetDlgItemTextW(IDC_EDIT_MAX_DISP, str);

    // 初始化目标类型选择（0=定值, 1=二次, 其他默认定值）
    if (m_targetType == 1)
    {
        CheckRadioButton(IDC_RADIO_CONSTANT, IDC_RADIO_QUADRATIC, IDC_RADIO_QUADRATIC);
        GetDlgItem(IDC_EDIT_TARGET_VALUE)->EnableWindow(FALSE);
        GetDlgItem(IDC_EDIT_A)->EnableWindow(TRUE);
        GetDlgItem(IDC_EDIT_B)->EnableWindow(TRUE);
    }
    else
    {
        CheckRadioButton(IDC_RADIO_CONSTANT, IDC_RADIO_QUADRATIC, IDC_RADIO_CONSTANT);
        GetDlgItem(IDC_EDIT_TARGET_VALUE)->EnableWindow(TRUE);
        GetDlgItem(IDC_EDIT_A)->EnableWindow(FALSE);
        GetDlgItem(IDC_EDIT_B)->EnableWindow(FALSE);
        m_targetType = 0;  // 强制修正非法值
    }

    // LED指示灯子类化并初始化
    m_ledStatic.SubclassDlgItem(IDC_STATIC_LED, this);
    SetTimer(LED_TIMER_ID, 200, nullptr);  // 200ms 轮询仿真状态
    UpdateLedState();

    return TRUE;
}

void CParamSettingsDlg::OnOK()
{
    if (!m_pDoc) return;

    // 读取并验证所有参数
    CString str;

    // 系统动力学参数
    GetDlgItemTextW(IDC_EDIT_K, str);     double k = _wtof(str);
    GetDlgItemTextW(IDC_EDIT_G, str);     double g = _wtof(str);
    GetDlgItemTextW(IDC_EDIT_M1, str);    double m1 = _wtof(str);
    GetDlgItemTextW(IDC_EDIT_THETA, str); double theta = _wtof(str);

    if (k < 1.0 || k > 5.0)
    {
        AfxMessageBox(L"单位长度质量 k 必须在 1 ~ 5 kg/m 范围内！", MB_OK | MB_ICONERROR);
        return;
    }
    if (g < 9.8 || g > 10.0)
    {
        AfxMessageBox(L"重力加速度 g 必须在 9.8 ~ 10 m/s² 范围内！", MB_OK | MB_ICONERROR);
        return;
    }
    if (m1 < 10.0 || m1 > 15.0)
    {
        AfxMessageBox(L"吊钩质量 m1 必须在 10 ~ 15 kg 范围内！", MB_OK | MB_ICONERROR);
        return;
    }
    if (theta < 0.0 || theta > 0.05)
    {
        AfxMessageBox(L"钢丝绳倾角 theta 必须在 0 ~ 0.05° 范围内！", MB_OK | MB_ICONERROR);
        return;
    }

    // PID参数
    GetDlgItemTextW(IDC_EDIT_KP, str); double kp = _wtof(str);
    GetDlgItemTextW(IDC_EDIT_KI, str); double ki = _wtof(str);
    GetDlgItemTextW(IDC_EDIT_KD, str); double kd = _wtof(str);

    if (kp < 0 || ki < 0 || kd < 0)
    {
        AfxMessageBox(L"PID参数不能为负数！", MB_OK | MB_ICONERROR);
        return;
    }

    // 目标类型
    bool isConstant = IsDlgButtonChecked(IDC_RADIO_CONSTANT) != 0;
    double ld = 0, A = 0, B = 0;

    if (isConstant)
    {
        GetDlgItemTextW(IDC_EDIT_TARGET_VALUE, str);
        ld = _wtof(str);
        if (ld <= 0 || ld > 1000)
        {
            AfxMessageBox(L"定值目标 ld 必须在 0 ~ 1000 m 范围内！", MB_OK | MB_ICONERROR);
            return;
        }
    }
    else
    {
        GetDlgItemTextW(IDC_EDIT_A, str); A = _wtof(str);
        GetDlgItemTextW(IDC_EDIT_B, str); B = _wtof(str);

        if (A < 0.015 || A > 0.025)
        {
            AfxMessageBox(L"二次系数 A 必须在 0.015 ~ 0.025 范围内！", MB_OK | MB_ICONERROR);
            return;
        }
        if (B < 0.02 || B > 0.04)
        {
            AfxMessageBox(L"一次系数 B 必须在 0.02 ~ 0.04 范围内！", MB_OK | MB_ICONERROR);
            return;
        }
    }

    // 仿真参数
    GetDlgItemTextW(IDC_EDIT_SIM_TIME, str); double simTime = _wtof(str);
    GetDlgItemTextW(IDC_EDIT_SIM_STEP, str); double simStep = _wtof(str);
    GetDlgItemTextW(IDC_EDIT_MAX_DISP, str); double maxDisp = _wtof(str);

    if (simTime <= 0 || simStep <= 0 || maxDisp <= 0)
    {
        AfxMessageBox(L"仿真参数必须大于0！", MB_OK | MB_ICONERROR);
        return;
    }

    // 保存所有参数到文档
    SimParams& p = m_pDoc->GetParams();
    p.k = k;
    p.g = g;
    p.m1 = m1;
    p.theta = theta;
    p.kp = kp;
    p.ki = ki;
    p.kd = kd;
    p.targetType = isConstant ? TARGET_CONSTANT : TARGET_QUADRATIC;
    p.ld_constant = ld;
    p.A = A;
    p.B = B;
    p.simTime = simTime;
    p.simStep = simStep;
    p.maxDisplacement = maxDisp;

    CDialogEx::OnOK();
}

// ============================================================
// 控制按钮（转发给主框架窗口）
// ============================================================

void CParamSettingsDlg::OnBnClickedStart()
{
    ApplyParamsToDoc();  // 先推送参数到文档，再开始仿真
    CMainFrame* pFrame = dynamic_cast<CMainFrame*>(AfxGetMainWnd());
    if (pFrame)
    {
        pFrame->SendMessage(WM_COMMAND, ID_CONTROL_START, 0);
    }
    UpdateLedState();
}

void CParamSettingsDlg::OnBnClickedPause()
{
    CMainFrame* pFrame = dynamic_cast<CMainFrame*>(AfxGetMainWnd());
    if (pFrame)
    {
        pFrame->SendMessage(WM_COMMAND, ID_CONTROL_PAUSE, 0);
    }
    UpdateLedState();
}

void CParamSettingsDlg::OnBnClickedStop()
{
    CMainFrame* pFrame = dynamic_cast<CMainFrame*>(AfxGetMainWnd());
    if (pFrame)
    {
        pFrame->SendMessage(WM_COMMAND, ID_CONTROL_STOP, 0);
    }
    UpdateLedState();
}

void CParamSettingsDlg::ApplyParamsToDoc()
{
    if (!m_pDoc) return;
    SimParams& p = m_pDoc->GetParams();

    // PID 参数（滑块/编辑框实时更新的本地值）
    p.kp = m_kp;
    p.ki = m_ki;
    p.kd = m_kd;

    // 目标类型及参数
    p.targetType = (m_targetType == 1) ? TARGET_QUADRATIC : TARGET_CONSTANT;
    p.ld_constant = m_ld_constant;
    p.A = m_A;
    p.B = m_B;

    // 系统参数（从编辑框实时读取）
    CString str;
    GetDlgItemTextW(IDC_EDIT_K, str);     p.k = _wtof(str);
    GetDlgItemTextW(IDC_EDIT_G, str);     p.g = _wtof(str);
    GetDlgItemTextW(IDC_EDIT_M1, str);    p.m1 = _wtof(str);
    GetDlgItemTextW(IDC_EDIT_THETA, str); p.theta = _wtof(str);

    // 仿真参数
    GetDlgItemTextW(IDC_EDIT_SIM_TIME, str);  p.simTime = _wtof(str);
    GetDlgItemTextW(IDC_EDIT_SIM_STEP, str);  p.simStep = _wtof(str);
    GetDlgItemTextW(IDC_EDIT_MAX_DISP, str);  p.maxDisplacement = _wtof(str);
}

// ============================================================
// 仿真状态指示灯
// ============================================================

void CParamSettingsDlg::UpdateLedState()
{
    if (!m_pDoc) return;
    COLORREF color;
    switch (m_pDoc->GetSimState())
    {
    case SIM_RUNNING: color = RGB(0, 200, 0);    break;  // 绿色-运行中
    case SIM_PAUSED:  color = RGB(255, 180, 0);  break;  // 黄色-已暂停
    default:          color = RGB(220, 50, 50);  break;  // 红色-已停止
    }
    m_ledStatic.SetLedColor(color);
}

void CParamSettingsDlg::OnTimer(UINT_PTR nIDEvent)
{
    if (nIDEvent == LED_TIMER_ID)
        UpdateLedState();
    CDialogEx::OnTimer(nIDEvent);
}

// ============================================================
// 滑动条事件（同步编辑框）
// ============================================================

void CParamSettingsDlg::OnHScroll(UINT nSBCode, UINT nPos, CScrollBar* pScrollBar)
{
    // CSliderCtrl 不继承自 CScrollBar，dynamic_cast 会失败
    // 改用已子类化的成员滑块控件直接读取位置
    if (!pScrollBar) { CDialogEx::OnHScroll(nSBCode, nPos, pScrollBar); return; }

    int sliderId = pScrollBar->GetDlgCtrlID();

    if (sliderId == IDC_SLIDER_KP || sliderId == IDC_SLIDER_KI || sliderId == IDC_SLIDER_KD)
    {
        m_bUpdatingControls = true;  // 防止 SetDlgItemTextW 触发 EN_CHANGE 再次回调

        double val = 0;
        int editId = 0;

        if (sliderId == IDC_SLIDER_KP)  { val = m_sliderKp.GetPos() / 10.0; m_kp = val; editId = IDC_EDIT_KP; }
        if (sliderId == IDC_SLIDER_KI)  { val = m_sliderKi.GetPos() / 10.0; m_ki = val; editId = IDC_EDIT_KI; }
        if (sliderId == IDC_SLIDER_KD)  { val = m_sliderKd.GetPos() / 10.0; m_kd = val; editId = IDC_EDIT_KD; }

        CString strVal;
        strVal.Format(L"%.1f", val);
        SetDlgItemTextW(editId, strVal);

        m_bUpdatingControls = false;
    }
    else
    {
        CDialogEx::OnHScroll(nSBCode, nPos, pScrollBar);
    }
}

// ============================================================
// 编辑框变更事件（同步滑动条）
// ============================================================

void CParamSettingsDlg::OnEnChangeKp()
{
    if (m_bUpdatingControls) return;
    CString str;
    GetDlgItemTextW(IDC_EDIT_KP, str);
    double val = _wtof(str);
    if (val >= 0 && val <= 500) { m_kp = val; m_sliderKp.SetPos((int)(val * 10)); }
}

void CParamSettingsDlg::OnEnChangeKi()
{
    if (m_bUpdatingControls) return;
    CString str;
    GetDlgItemTextW(IDC_EDIT_KI, str);
    double val = _wtof(str);
    if (val >= 0 && val <= 500) { m_ki = val; m_sliderKi.SetPos((int)(val * 10)); }
}

void CParamSettingsDlg::OnEnChangeKd()
{
    if (m_bUpdatingControls) return;
    CString str;
    GetDlgItemTextW(IDC_EDIT_KD, str);
    double val = _wtof(str);
    if (val >= 0 && val <= 500) { m_kd = val; m_sliderKd.SetPos((int)(val * 10)); }
}

// ============================================================
// 目标类型选择
// ============================================================

void CParamSettingsDlg::OnBnClickedRadioConstant()
{
    CheckRadioButton(IDC_RADIO_CONSTANT, IDC_RADIO_QUADRATIC, IDC_RADIO_CONSTANT);
    GetDlgItem(IDC_EDIT_TARGET_VALUE)->EnableWindow(TRUE);
    GetDlgItem(IDC_EDIT_A)->EnableWindow(FALSE);
    GetDlgItem(IDC_EDIT_B)->EnableWindow(FALSE);
    m_targetType = 0;
}

void CParamSettingsDlg::OnBnClickedRadioQuadratic()
{
    CheckRadioButton(IDC_RADIO_CONSTANT, IDC_RADIO_QUADRATIC, IDC_RADIO_QUADRATIC);
    GetDlgItem(IDC_EDIT_TARGET_VALUE)->EnableWindow(FALSE);
    GetDlgItem(IDC_EDIT_A)->EnableWindow(TRUE);
    GetDlgItem(IDC_EDIT_B)->EnableWindow(TRUE);
    m_targetType = 1;
}
