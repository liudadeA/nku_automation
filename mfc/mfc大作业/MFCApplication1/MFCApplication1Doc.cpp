// MFCApplication1Doc.cpp : CMFCApplication1Doc 类的实现
// 太阳翼展开时变重力卸载控制仿真

#include "pch.h"
#include "framework.h"
#ifndef SHARED_HANDLERS
#include "MFCApplication1.h"
#endif

#include "MFCApplication1Doc.h"
#include "MFCApplication1View.h"

#include <propkey.h>
#include <fstream>
#include <sstream>
#include <cmath>

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

IMPLEMENT_DYNCREATE(CMFCApplication1Doc, CDocument)

BEGIN_MESSAGE_MAP(CMFCApplication1Doc, CDocument)
END_MESSAGE_MAP()

const double PI = 3.14159265358979323846;
const double DEG_TO_RAD = PI / 180.0;

// ============================================================
// 构造/析构
// ============================================================

CMFCApplication1Doc::CMFCApplication1Doc() noexcept
{
    InitAppearanceDefaults();
}

CMFCApplication1Doc::~CMFCApplication1Doc()
{
}

void CMFCApplication1Doc::InitAppearanceDefaults()
{
    // 默认标签字体 (Arial, 12pt)
    ZeroMemory(&m_appearance.lfForceLabel, sizeof(LOGFONTW));
    ZeroMemory(&m_appearance.lfErrorLabel, sizeof(LOGFONTW));
    ZeroMemory(&m_appearance.lfDispLabel, sizeof(LOGFONTW));
    ZeroMemory(&m_appearance.lfTimeLabel, sizeof(LOGFONTW));

    wcscpy_s(m_appearance.lfForceLabel.lfFaceName, LF_FACESIZE, L"Arial");
    m_appearance.lfForceLabel.lfHeight = -16;
    m_appearance.lfForceLabel.lfWeight = FW_NORMAL;

    wcscpy_s(m_appearance.lfErrorLabel.lfFaceName, LF_FACESIZE, L"Arial");
    m_appearance.lfErrorLabel.lfHeight = -16;
    m_appearance.lfErrorLabel.lfWeight = FW_NORMAL;

    wcscpy_s(m_appearance.lfDispLabel.lfFaceName, LF_FACESIZE, L"Arial");
    m_appearance.lfDispLabel.lfHeight = -16;
    m_appearance.lfDispLabel.lfWeight = FW_NORMAL;

    wcscpy_s(m_appearance.lfTimeLabel.lfFaceName, LF_FACESIZE, L"Arial");
    m_appearance.lfTimeLabel.lfHeight = -16;
    m_appearance.lfTimeLabel.lfWeight = FW_NORMAL;
}

BOOL CMFCApplication1Doc::OnNewDocument()
{
    if (!CDocument::OnNewDocument())
        return FALSE;

    ResetSimulation();
    return TRUE;
}

// ============================================================
// 系统动力学方程（仿射非线性形式）
//   状态: x = [l, i]^T = [x1, x2]^T
//   dx/dt = F(x) + G(x) * F
//   F(x) — 自由动力学项
//   G(x) — 控制增益项
//   F    — 卷扬机构提供的拉力
// ============================================================

double CMFCApplication1Doc::F1(double x1, double x2)
{
    // F1 = x2
    return x2;
}

double CMFCApplication1Doc::F2(double x1, double x2)
{
    // F2 = ( m1*g + k*g*x1/cosθ - k*x2²/cosθ ) / ( m1 + k*x1/cosθ )
    double theta_rad = m_params.theta * DEG_TO_RAD;
    double cosTheta = cos(theta_rad);
    if (cosTheta < 1e-6) cosTheta = 1e-6;

    double denom = m_params.m1 + m_params.k * x1 / cosTheta;
    if (fabs(denom) < 1e-9) denom = (denom >= 0) ? 1e-9 : -1e-9;

    double num = m_params.m1 * m_params.g
               + m_params.k * m_params.g * x1 / cosTheta
               - m_params.k * x2 * x2 / cosTheta;

    return num / denom;
}

double CMFCApplication1Doc::G2(double x1)
{
    // G2 = -1 / ( m1 + k*x1/cosθ )
    double theta_rad = m_params.theta * DEG_TO_RAD;
    double cosTheta = cos(theta_rad);
    if (cosTheta < 1e-6) cosTheta = 1e-6;

    double denom = m_params.m1 + m_params.k * x1 / cosTheta;
    if (fabs(denom) < 1e-9) denom = (denom >= 0) ? 1e-9 : -1e-9;

    return -1.0 / denom;
}

// ============================================================
// 目标位移计算
// ============================================================

double CMFCApplication1Doc::ComputeTargetDisplacement(double t)
{
    if (m_params.targetType == TARGET_CONSTANT)
    {
        return m_params.ld_constant;
    }
    else
    {
        // ld = A * t^2 + B * t
        return m_params.A * t * t + m_params.B * t;
    }
}

// ============================================================
// PID控制器
// ============================================================

double CMFCApplication1Doc::ComputeControlForce(double error, double errorIntegral, double errorDerivative)
{
    double force = m_params.kp * error + m_params.ki * errorIntegral + m_params.kd * errorDerivative;
    // 钢丝绳只能拉不能推，拉力不能为负
    if (force < 0.0) force = 0.0;
    return force;
}


// ============================================================
// 数值积分方法
// ============================================================

void CMFCApplication1Doc::Integrate(double dt, double force)
{
    switch (m_params.integrator)
    {
    case INT_EULER:
        IntegrateEuler(dt, force);
        break;
    case INT_RK2:
        IntegrateRK2(dt, force);
        break;
    case INT_RK4:
        IntegrateRK4(dt, force);
        break;
    default:
        IntegrateRK4(dt, force);
        break;
    }
}

void CMFCApplication1Doc::IntegrateEuler(double dt, double force)
{
    // 欧拉法: x_{n+1} = x_n + dt * (F(x_n) + G(x_n) * force)
    double f1 = F1(m_x1, m_x2);
    double f2 = F2(m_x1, m_x2);
    double g2 = G2(m_x1);

    double dx1 = f1;
    double dx2 = f2 + g2 * force;

    m_x1 += dt * dx1;
    m_x2 += dt * dx2;
}

void CMFCApplication1Doc::IntegrateRK2(double dt, double force)
{
    // 二阶中点法 (RK2)
    // k1 = f(x_n, u_n)
    // k2 = f(x_n + 0.5*dt*k1, u_n)
    // x_{n+1} = x_n + dt * k2

    double f1_1 = F1(m_x1, m_x2);
    double f2_1 = F2(m_x1, m_x2);
    double g2_1 = G2(m_x1);

    double k1_x1 = f1_1;
    double k1_x2 = f2_1 + g2_1 * force;

    // 半步预测
    double x1_mid = m_x1 + 0.5 * dt * k1_x1;
    double x2_mid = m_x2 + 0.5 * dt * k1_x2;

    double f1_2 = F1(x1_mid, x2_mid);
    double f2_2 = F2(x1_mid, x2_mid);
    double g2_2 = G2(x1_mid);

    double k2_x1 = f1_2;
    double k2_x2 = f2_2 + g2_2 * force;

    m_x1 += dt * k2_x1;
    m_x2 += dt * k2_x2;
}

void CMFCApplication1Doc::IntegrateRK4(double dt, double force)
{
    // 四阶经典Runge-Kutta方法
    // k1 = f(x_n, u_n)
    // k2 = f(x_n + 0.5*dt*k1, u_n)
    // k3 = f(x_n + 0.5*dt*k2, u_n)
    // k4 = f(x_n + dt*k3, u_n)
    // x_{n+1} = x_n + dt*(k1 + 2*k2 + 2*k3 + k4)/6

    // k1
    double f1_1 = F1(m_x1, m_x2);
    double f2_1 = F2(m_x1, m_x2);
    double g2_1 = G2(m_x1);
    double k1_x1 = f1_1;
    double k1_x2 = f2_1 + g2_1 * force;

    // k2
    double x1_2 = m_x1 + 0.5 * dt * k1_x1;
    double x2_2 = m_x2 + 0.5 * dt * k1_x2;
    double f1_2 = F1(x1_2, x2_2);
    double f2_2 = F2(x1_2, x2_2);
    double g2_2 = G2(x1_2);
    double k2_x1 = f1_2;
    double k2_x2 = f2_2 + g2_2 * force;

    // k3
    double x1_3 = m_x1 + 0.5 * dt * k2_x1;
    double x2_3 = m_x2 + 0.5 * dt * k2_x2;
    double f1_3 = F1(x1_3, x2_3);
    double f2_3 = F2(x1_3, x2_3);
    double g2_3 = G2(x1_3);
    double k3_x1 = f1_3;
    double k3_x2 = f2_3 + g2_3 * force;

    // k4
    double x1_4 = m_x1 + dt * k3_x1;
    double x2_4 = m_x2 + dt * k3_x2;
    double f1_4 = F1(x1_4, x2_4);
    double f2_4 = F2(x1_4, x2_4);
    double g2_4 = G2(x1_4);
    double k4_x1 = f1_4;
    double k4_x2 = f2_4 + g2_4 * force;

    m_x1 += dt * (k1_x1 + 2.0 * k2_x1 + 2.0 * k3_x1 + k4_x1) / 6.0;
    m_x2 += dt * (k1_x2 + 2.0 * k2_x2 + 2.0 * k3_x2 + k4_x2) / 6.0;
}

// ============================================================
// 仿真控制
// ============================================================

void CMFCApplication1Doc::ResetSimulation()
{
    m_simTime = 0.0;
    m_x1 = 0.0;
    m_x2 = 0.0;
    m_currentTarget = ComputeTargetDisplacement(0.0);
    m_currentForce = 0.0;
    m_currentError = -m_currentTarget;  // x1 - target = 0 - target
    m_errorIntegral = 0.0;
    m_prevError = m_currentError;
    m_alarmTriggered = false;

    m_timeHistory.clear();
    m_dispHistory.clear();
    m_targetHistory.clear();
    m_forceHistory.clear();
    m_errorHistory.clear();

    // 记录 t=0 初始状态
    m_timeHistory.push_back(0.0);
    m_dispHistory.push_back(m_x1);
    m_targetHistory.push_back(m_currentTarget);
    m_forceHistory.push_back(0.0);
    m_errorHistory.push_back(m_currentError);

    m_simState = SIM_STOPPED;
}

void CMFCApplication1Doc::StartSimulation()
{
    if (m_simState == SIM_STOPPED)
    {
        ResetSimulation();
    }
    m_simState = SIM_RUNNING;
}

void CMFCApplication1Doc::PauseSimulation()
{
    if (m_simState == SIM_RUNNING)
        m_simState = SIM_PAUSED;
}

void CMFCApplication1Doc::StopSimulation()
{
    m_simState = SIM_STOPPED;
}

bool CMFCApplication1Doc::StepSimulation()
{
    if (m_simState != SIM_RUNNING)
        return false;

    if (m_simTime >= m_params.simTime)
    {
        StopSimulation();
        return false;
    }

    double dt = m_params.simStep;

    // 当前目标
    m_currentTarget = ComputeTargetDisplacement(m_simTime);

    // 误差计算（实际-目标：正误差=已超调需制动）
    m_currentError = m_x1 - m_currentTarget;

    // 条件积分：只在误差小于阈值时累积，防止接近阶段积分饱和
    double integralThreshold = 1.0;  // 误差在 ±1m 以内才积分
    if (fabs(m_currentError) < integralThreshold)
        m_errorIntegral += m_currentError * dt;
    // 超出阈值时冻结积分（不清零，避免丢失已积累的有效积分）

    // 积分项钳位
    double maxIntegral = 200.0;
    if (m_errorIntegral > maxIntegral)  m_errorIntegral = maxIntegral;
    if (m_errorIntegral < -maxIntegral) m_errorIntegral = -maxIntegral;

    double errorDerivative = (m_currentError - m_prevError) / dt;

    // PID控制力
    m_currentForce = ComputeControlForce(m_currentError, m_errorIntegral, errorDerivative);

    // 数值积分
    Integrate(dt, m_currentForce);

    // 数值保护：检测NaN/Inf
    if (std::isnan(m_x1) || std::isinf(m_x1) || std::isnan(m_x2) || std::isinf(m_x2))
    {
        StopSimulation();
        return false;
    }

    // 位移和速度限幅，防止数值爆炸
    // x1下限：denom = m1 + k*x1/cosθ > 0 → x1 > -m1*cosθ/k ≈ -4.0
    if (m_x1 > 1e4)   m_x1 = 1e4;
    if (m_x1 < -3.0)  m_x1 = -3.0;   // 避免分母为0导致NaN
    if (m_x2 > 1e4)  m_x2 = 1e4;
    if (m_x2 < -1e4) m_x2 = -1e4;

    // 位移超限报警（单次触发）
    if (!m_alarmTriggered && m_x1 >= m_params.maxDisplacement)
    {
        m_alarmTriggered = true;
        StopSimulation();
        CString msg;
        msg.Format(L"太阳翼位移已达到设定的最高值 %.2f m！\n\n当前位移: %.3f m\n当前时间: %.2f s\n\n仿真已停止。",
                   m_params.maxDisplacement, m_x1, m_simTime);
        AfxMessageBox(msg, MB_OK | MB_ICONWARNING);
        return false;
    }

    m_prevError = m_currentError;

    // 时间推进到本步结束后
    m_simTime += dt;

    // 重算积分后的目标与误差（m_x1 已被 Integrate 更新）
    m_currentTarget = ComputeTargetDisplacement(m_simTime);
    m_currentError = m_x1 - m_currentTarget;

    // 记录本步结束后的状态
    if (m_timeHistory.size() < MAX_HISTORY_POINTS
        && !std::isnan(m_x1) && !std::isnan(m_x2))
    {
        m_timeHistory.push_back(m_simTime);
        m_dispHistory.push_back(m_x1);
        m_targetHistory.push_back(m_currentTarget);
        m_forceHistory.push_back(m_currentForce);
        m_errorHistory.push_back(m_currentError);
    }

    return true;
}

// ============================================================
// 序列化 / 参数保存与读取
// ============================================================

void CMFCApplication1Doc::Serialize(CArchive& ar)
{
    if (ar.IsStoring())
    {
        // 使用专用的保存/读取方法
    }
    else
    {
    }
}

void CMFCApplication1Doc::SaveParams(const CString& filePath)
{
    CStringA pathA(filePath);
    std::ofstream ofs(pathA.GetString());
    if (!ofs.is_open())
    {
        AfxMessageBox(L"无法保存文件！", MB_OK | MB_ICONERROR);
        return;
    }

    SimParams& p = m_params;

    ofs << "k=" << p.k << "\n";
    ofs << "g=" << p.g << "\n";
    ofs << "m1=" << p.m1 << "\n";
    ofs << "theta=" << p.theta << "\n";
    ofs << "kp=" << p.kp << "\n";
    ofs << "ki=" << p.ki << "\n";
    ofs << "kd=" << p.kd << "\n";
    ofs << "targetType=" << (int)p.targetType << "\n";
    ofs << "ld_constant=" << p.ld_constant << "\n";
    ofs << "A=" << p.A << "\n";
    ofs << "B=" << p.B << "\n";
    ofs << "simTime=" << p.simTime << "\n";
    ofs << "simStep=" << p.simStep << "\n";
    ofs << "maxDisplacement=" << p.maxDisplacement << "\n";
    ofs << "integrator=" << (int)p.integrator << "\n";

    ofs.close();
}

void CMFCApplication1Doc::LoadParams(const CString& filePath)
{
    CStringA pathA(filePath);
    std::ifstream ifs(pathA.GetString());
    if (!ifs.is_open())
    {
        AfxMessageBox(L"无法打开文件！", MB_OK | MB_ICONERROR);
        return;
    }

    SimParams& p = m_params;
    std::string line;
    int tempInt = 0;

    while (std::getline(ifs, line))
    {
        size_t eqPos = line.find('=');
        if (eqPos == std::string::npos) continue;

        std::string key = line.substr(0, eqPos);
        std::string val = line.substr(eqPos + 1);

        if (key == "k") p.k = atof(val.c_str());
        else if (key == "g") p.g = atof(val.c_str());
        else if (key == "m1") p.m1 = atof(val.c_str());
        else if (key == "theta") p.theta = atof(val.c_str());
        else if (key == "kp") p.kp = atof(val.c_str());
        else if (key == "ki") p.ki = atof(val.c_str());
        else if (key == "kd") p.kd = atof(val.c_str());
        else if (key == "targetType") { tempInt = atoi(val.c_str()); p.targetType = (TargetType)tempInt; }
        else if (key == "ld_constant") p.ld_constant = atof(val.c_str());
        else if (key == "A") p.A = atof(val.c_str());
        else if (key == "B") p.B = atof(val.c_str());
        else if (key == "simTime") p.simTime = atof(val.c_str());
        else if (key == "simStep") p.simStep = atof(val.c_str());
        else if (key == "maxDisplacement") p.maxDisplacement = atof(val.c_str());
        else if (key == "integrator") { tempInt = atoi(val.c_str()); p.integrator = (IntegratorType)tempInt; }
    }

    ifs.close();
    ResetSimulation();
}

// ============================================================
// 诊断
// ============================================================

#ifdef _DEBUG
void CMFCApplication1Doc::AssertValid() const
{
    CDocument::AssertValid();
}

void CMFCApplication1Doc::Dump(CDumpContext& dc) const
{
    CDocument::Dump(dc);
}
#endif

#ifdef SHARED_HANDLERS
void CMFCApplication1Doc::OnDrawThumbnail(CDC& dc, LPRECT lprcBounds)
{
    dc.FillSolidRect(lprcBounds, RGB(255, 255, 255));
    CString strText = L"太阳翼展开仿真";
    LOGFONT lf;
    CFont* pDefaultGUIFont = CFont::FromHandle((HFONT)GetStockObject(DEFAULT_GUI_FONT));
    pDefaultGUIFont->GetLogFont(&lf);
    lf.lfHeight = 36;
    CFont fontDraw;
    fontDraw.CreateFontIndirect(&lf);
    CFont* pOldFont = dc.SelectObject(&fontDraw);
    dc.DrawText(strText, lprcBounds, DT_CENTER | DT_WORDBREAK);
    dc.SelectObject(pOldFont);
}

void CMFCApplication1Doc::InitializeSearchContent()
{
    CString strSearchContent;
    SetSearchContent(strSearchContent);
}

void CMFCApplication1Doc::SetSearchContent(const CString& value)
{
    if (value.IsEmpty())
    {
        RemoveChunk(PKEY_Search_Contents.fmtid, PKEY_Search_Contents.pid);
    }
    else
    {
        CMFCFilterChunkValueImpl* pChunk = nullptr;
        ATLTRY(pChunk = new CMFCFilterChunkValueImpl);
        if (pChunk != nullptr)
        {
            pChunk->SetTextValue(PKEY_Search_Contents, value, CHUNK_TEXT);
            SetChunkValue(pChunk);
        }
    }
}
#endif
