// MFCApplication1Doc.h : CMFCApplication1Doc 类的接口
// 太阳翼展开时变重力卸载控制仿真 - 文档类

#pragma once
#include <vector>

// 仿真状态枚举
enum SimState { SIM_STOPPED = 0, SIM_RUNNING = 1, SIM_PAUSED = 2 };

// 目标类型枚举
enum TargetType { TARGET_CONSTANT = 0, TARGET_QUADRATIC = 1 };

// 数值算法枚举
enum IntegratorType { INT_EULER = 0, INT_RK2 = 1, INT_RK4 = 2 };

// 仿真参数结构体
struct SimParams
{
    // 系统动力学参数
    double k = 3.0;              // 单位长度质量 (kg/m), 范围 1~5
    double g = 9.81;             // 重力加速度 (m/s^2), 范围 9.8~10
    double m1 = 12.0;            // 吊钩质量 (kg), 范围 10~15
    double theta = 0.02;         // 钢丝绳倾角 (deg), 范围 0~0.05

    // PID参数
    double kp = 430.7;
    double ki = 133.5;
    double kd = 141.6;

    // 目标类型及参数
    TargetType targetType = TARGET_CONSTANT;
    double ld_constant = 5.0;    // 定值目标 (m)
    double A = 0.02;             // 二次项系数 (0.015~0.025)
    double B = 0.03;             // 一次项系数 (0.02~0.04)

    // 仿真参数
    double simTime = 30.0;       // 仿真总时间 (s)
    double simStep = 0.01;       // 仿真步长 (s)
    double maxDisplacement = 10.0; // 最高位移报警值 (m)

    // 数值算法
    IntegratorType integrator = INT_RK4;
};

// 曲线外观设置
struct PlotAppearance
{
    COLORREF bgColor = RGB(30, 30, 30);     // 背景色
    LOGFONTW lfForceLabel;                   // 拉力标签字体
    LOGFONTW lfErrorLabel;                   // 误差标签字体
    LOGFONTW lfDispLabel;                    // 位移标签字体
    LOGFONTW lfTimeLabel;                    // 时间标签字体
    COLORREF colorForceLabel = RGB(255, 200, 100);   // 拉力标签颜色
    COLORREF colorErrorLabel = RGB(255, 150, 150);   // 误差标签颜色
    COLORREF colorDispLabel = RGB(150, 200, 255);    // 位移标签颜色
    COLORREF colorTimeLabel = RGB(200, 200, 200);    // 时间标签颜色
};

class CMFCApplication1Doc : public CDocument
{
protected:
    CMFCApplication1Doc() noexcept;
    DECLARE_DYNCREATE(CMFCApplication1Doc)

public:
    virtual ~CMFCApplication1Doc();

    // 仿真核心方法
    void StartSimulation();
    void PauseSimulation();
    void StopSimulation();
    void ResetSimulation();
    bool StepSimulation();  // 单步仿真, 返回是否继续
    double ComputeTargetDisplacement(double t);  // 计算目标位移
    double ComputeControlForce(double error, double errorIntegral, double errorDerivative);
    void Integrate(double dt, double force);  // 使用选定算法积分

    // 状态获取
    SimState GetSimState() const { return m_simState; }
    double GetCurrentTime() const { return m_simTime; }
    double GetCurrentDisplacement() const { return m_x1; }
    double GetCurrentVelocity() const { return m_x2; }
    double GetCurrentTarget() const { return m_currentTarget; }
    double GetCurrentForce() const { return m_currentForce; }
    double GetCurrentError() const { return m_currentError; }

    // 参数访问
    SimParams& GetParams() { return m_params; }
    PlotAppearance& GetAppearance() { return m_appearance; }

    // 历史数据访问（用于绘图）
    const std::vector<double>& GetTimeHistory() const { return m_timeHistory; }
    const std::vector<double>& GetDispHistory() const { return m_dispHistory; }
    const std::vector<double>& GetTargetHistory() const { return m_targetHistory; }
    const std::vector<double>& GetForceHistory() const { return m_forceHistory; }
    const std::vector<double>& GetErrorHistory() const { return m_errorHistory; }

    // 参数保存/读取
    void SaveParams(const CString& filePath);
    void LoadParams(const CString& filePath);

public:
    virtual BOOL OnNewDocument();
    virtual void Serialize(CArchive& ar);
#ifdef SHARED_HANDLERS
    virtual void InitializeSearchContent();
    virtual void OnDrawThumbnail(CDC& dc, LPRECT lprcBounds);
#endif

#ifdef _DEBUG
    virtual void AssertValid() const;
    virtual void Dump(CDumpContext& dc) const;
#endif

protected:
    DECLARE_MESSAGE_MAP()

private:
    // 仿真状态
    SimState m_simState = SIM_STOPPED;
    double m_simTime = 0.0;
    double m_x1 = 0.0;           // 当前位移 l
    double m_x2 = 0.0;           // 当前速度 l_dot
    double m_currentTarget = 0.0;
    double m_currentForce = 0.0;
    double m_currentError = 0.0;
    double m_errorIntegral = 0.0;
    double m_prevError = 0.0;
    bool m_alarmTriggered = false;   // 单次报警标志

    // 参数
    SimParams m_params;
    PlotAppearance m_appearance;

    // 历史数据
    std::vector<double> m_timeHistory;
    std::vector<double> m_dispHistory;
    std::vector<double> m_targetHistory;
    std::vector<double> m_forceHistory;
    std::vector<double> m_errorHistory;

    // 最大历史点数
    static const size_t MAX_HISTORY_POINTS = 50000;

    // 数值积分函数
    void IntegrateEuler(double dt, double force);
    void IntegrateRK2(double dt, double force);
    void IntegrateRK4(double dt, double force);

    // 状态方程
    double F1(double x1, double x2);
    double F2(double x1, double x2);
    double G2(double x1);

    // 初始化外观默认值
    void InitAppearanceDefaults();
};

// GetDocument 内联函数在 MFCApplication1View.h 中
