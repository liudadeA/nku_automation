// ParamSettingsDlg.h : 参数设置对话框
// 太阳翼展开仿真 - 系统参数、PID、目标、仿真参数设置

#pragma once
#include "MFCApplication1Doc.h"

class CMFCApplication1Doc;
class CMFCApplication1View;

// 仿真状态指示灯控件
class CLedStatic : public CStatic
{
    COLORREF m_color = RGB(220, 50, 50);
public:
    void SetLedColor(COLORREF color) { m_color = color; Invalidate(); }
protected:
    afx_msg void OnPaint();
    DECLARE_MESSAGE_MAP()
};

class CParamSettingsDlg : public CDialogEx
{
public:
    CParamSettingsDlg(CMFCApplication1Doc* pDoc);
    virtual ~CParamSettingsDlg();

#ifdef AFX_DESIGN_TIME
    enum { IDD = IDD_PARAM_SETTINGS };
#endif

protected:
    virtual void DoDataExchange(CDataExchange* pDX);
    virtual BOOL OnInitDialog();
    virtual void OnOK();

    DECLARE_MESSAGE_MAP()

private:
    CMFCApplication1Doc* m_pDoc;

    // PID滑块控件
    CSliderCtrl m_sliderKp, m_sliderKi, m_sliderKd;

    // PID参数编辑框
    CEdit m_editKp, m_editKi, m_editKd;

    // 系统参数编辑框
    CEdit m_editK, m_editG, m_editM1, m_editTheta;

    // 目标参数编辑框
    CEdit m_editTargetValue, m_editA, m_editB;

    // 仿真参数编辑框
    CEdit m_editSimTime, m_editSimStep, m_editMaxDisp;

    // LED状态指示灯
    CLedStatic m_ledStatic;
    void UpdateLedState();
    void ApplyParamsToDoc();  // 将对话框当前参数推送到文档
    static const UINT_PTR LED_TIMER_ID = 200;
    afx_msg void OnTimer(UINT_PTR nIDEvent);

    // 防止滑块和编辑框相互触发无限更新
    bool m_bUpdatingControls = false;

    // 数据值
    double m_k, m_g, m_m1, m_theta;
    double m_kp, m_ki, m_kd;
    int m_targetType;  // 0=定值, 1=二次曲线
    double m_ld_constant, m_A, m_B;
    double m_simTime, m_simStep, m_maxDisp;

    // 控制按钮
    afx_msg void OnBnClickedStart();
    afx_msg void OnBnClickedPause();
    afx_msg void OnBnClickedStop();

    // 滑块滚动
    afx_msg void OnHScroll(UINT nSBCode, UINT nPos, CScrollBar* pScrollBar);

    // 编辑框变更（同步滑块）
    afx_msg void OnEnChangeKp();
    afx_msg void OnEnChangeKi();
    afx_msg void OnEnChangeKd();

    // 目标类型选择
    afx_msg void OnBnClickedRadioConstant();
    afx_msg void OnBnClickedRadioQuadratic();
};
