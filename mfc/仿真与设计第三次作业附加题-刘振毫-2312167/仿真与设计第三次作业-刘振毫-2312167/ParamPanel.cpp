#include "pch.h"
#include "framework.h"
#include "ParamPanel.h"
#include "仿真与设计第三次作业-刘振毫-2312167Doc.h"
#include "仿真与设计第三次作业-刘振毫-2312167View.h"
#include "MainFrm.h"
#include <cmath>

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

BEGIN_MESSAGE_MAP(CParamPanel, CWnd)
	ON_WM_CREATE()
	ON_WM_SIZE()
	ON_WM_PAINT()
	ON_WM_ERASEBKGND()
	ON_WM_CTLCOLOR()
	ON_COMMAND(IDC_RADIO_RECT,    OnRadioRect)
	ON_COMMAND(IDC_RADIO_ELLIPSE, OnRadioEllipse)
	ON_COMMAND(IDC_RADIO_LINE,    OnRadioLine)
	ON_COMMAND(IDC_BTN_CALC,      OnBtnCalc)
	ON_COMMAND(IDC_BTN_RESET,     OnBtnReset)
	ON_COMMAND(IDC_BTN_CONFIRM,   OnBtnConfirm)
	ON_COMMAND(IDC_BTN_COLOR,     OnBtnColor)
END_MESSAGE_MAP()

CParamPanel::CParamPanel()
	: m_pDoc(nullptr)
	, m_nShapeType(0)
	, m_curColor(RGB(0, 0, 0))
	, m_dArea(0), m_dPerimeter(0), m_dLength(0)
{
	m_bgBrush.CreateSolidBrush(RGB(240, 240, 240));
	m_colorBrush.CreateSolidBrush(m_curColor);
}

CParamPanel::~CParamPanel()
{
	m_font.DeleteObject();
	m_bgBrush.DeleteObject();
	m_colorBrush.DeleteObject();
}

BOOL CParamPanel::OnEraseBkgnd(CDC* pDC)
{
	CRect rc;
	GetClientRect(&rc);
	pDC->FillRect(&rc, &m_bgBrush);
	return TRUE;
}

int CParamPanel::OnCreate(LPCREATESTRUCT lpCreateStruct)
{
	if (CWnd::OnCreate(lpCreateStruct) == -1)
		return -1;

	m_font.CreatePointFont(90, _T("Microsoft YaHei"));
	CreateControls();
	return 0;
}

void CParamPanel::CreateControls()
{
	CRect rc(0, 0, 260, 700);

	m_staticShape.Create(_T("图元类型"), WS_CHILD | WS_VISIBLE | SS_LEFT,
		CRect(10, 10, 240, 28), this);
	m_staticShape.SetFont(&m_font);

	m_radioRect.Create(_T("矩形"), WS_CHILD | WS_VISIBLE | BS_AUTORADIOBUTTON | WS_GROUP,
		CRect(20, 38, 120, 56), this, IDC_RADIO_RECT);
	m_radioEllipse.Create(_T("椭圆"), WS_CHILD | WS_VISIBLE | BS_AUTORADIOBUTTON,
		CRect(130, 38, 230, 56), this, IDC_RADIO_ELLIPSE);
	m_radioLine.Create(_T("直线"), WS_CHILD | WS_VISIBLE | BS_AUTORADIOBUTTON,
		CRect(20, 60, 120, 78), this, IDC_RADIO_LINE);

	m_radioRect.SetCheck(BST_CHECKED);

	m_staticCoord.Create(_T("坐标输入（对角点）"), WS_CHILD | WS_VISIBLE | SS_LEFT,
		CRect(10, 88, 240, 106), this);
	m_staticCoord.SetFont(&m_font);

	m_labelX1.Create(_T("左上X:"), WS_CHILD | WS_VISIBLE | SS_RIGHT,
		CRect(15, 112, 70, 130), this);
	m_editX1.Create(WS_CHILD | WS_VISIBLE | WS_BORDER | ES_AUTOHSCROLL,
		CRect(75, 110, 120, 130), this, IDC_EDIT_X1);
	m_labelY1.Create(_T("左上Y:"), WS_CHILD | WS_VISIBLE | SS_RIGHT,
		CRect(125, 112, 175, 130), this);
	m_editY1.Create(WS_CHILD | WS_VISIBLE | WS_BORDER | ES_AUTOHSCROLL,
		CRect(180, 110, 230, 130), this, IDC_EDIT_Y1);

	m_labelX2.Create(_T("右下X:"), WS_CHILD | WS_VISIBLE | SS_RIGHT,
		CRect(15, 138, 70, 156), this);
	m_editX2.Create(WS_CHILD | WS_VISIBLE | WS_BORDER | ES_AUTOHSCROLL,
		CRect(75, 136, 120, 156), this, IDC_EDIT_X2);
	m_labelY2.Create(_T("右下Y:"), WS_CHILD | WS_VISIBLE | SS_RIGHT,
		CRect(125, 138, 175, 156), this);
	m_editY2.Create(WS_CHILD | WS_VISIBLE | WS_BORDER | ES_AUTOHSCROLL,
		CRect(180, 136, 230, 156), this, IDC_EDIT_Y2);

	m_editX1.SetWindowText(_T("100"));
	m_editY1.SetWindowText(_T("100"));
	m_editX2.SetWindowText(_T("300"));
	m_editY2.SetWindowText(_T("250"));

	m_staticStyle.Create(_T("线条样式"), WS_CHILD | WS_VISIBLE | SS_LEFT,
		CRect(10, 168, 240, 186), this);
	m_staticStyle.SetFont(&m_font);

	m_comboStyle.Create(WS_CHILD | WS_VISIBLE | CBS_DROPDOWNLIST | WS_VSCROLL,
		CRect(15, 190, 230, 390), this, IDC_COMBO_STYLE);
	m_comboStyle.AddString(_T("实线"));
	m_comboStyle.AddString(_T("虚线"));
	m_comboStyle.AddString(_T("点划线"));
	m_comboStyle.SetCurSel(0);

	m_staticColorLabel.Create(_T("颜色"), WS_CHILD | WS_VISIBLE | SS_LEFT,
		CRect(10, 220, 240, 238), this);
	m_staticColorLabel.SetFont(&m_font);

	m_colorPreview.Create(_T(""), WS_CHILD | WS_VISIBLE | SS_NOTIFY | SS_SUNKEN,
		CRect(15, 244, 50, 274), this, IDC_COLOR_PREVIEW);
	m_btnColor.Create(_T("选择颜色..."), WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
		CRect(60, 244, 150, 274), this, IDC_BTN_COLOR);

	m_staticArea.Create(_T("面积: "), WS_CHILD | WS_VISIBLE | SS_LEFT,
		CRect(15, 290, 235, 310), this);
	m_staticAreaVal.Create(_T("0.00"), WS_CHILD | WS_VISIBLE | SS_LEFT,
		CRect(65, 290, 235, 310), this);

	m_staticPerimeter.Create(_T("周长: "), WS_CHILD | WS_VISIBLE | SS_LEFT,
		CRect(15, 315, 235, 335), this);
	m_staticPerimeterVal.Create(_T("0.00"), WS_CHILD | WS_VISIBLE | SS_LEFT,
		CRect(65, 315, 235, 335), this);

	m_staticLength.Create(_T("长度: "), WS_CHILD | WS_VISIBLE | SS_LEFT,
		CRect(15, 340, 235, 360), this);
	m_staticLengthVal.Create(_T("0.00"), WS_CHILD | WS_VISIBLE | SS_LEFT,
		CRect(65, 340, 235, 360), this);

	m_btnCalc.Create(_T("计算"), WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
		CRect(15, 375, 70, 400), this, IDC_BTN_CALC);
	m_btnReset.Create(_T("重置"), WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
		CRect(80, 375, 135, 400), this, IDC_BTN_RESET);
	m_btnConfirm.Create(_T("确定"), WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
		CRect(145, 375, 200, 400), this, IDC_BTN_CONFIRM);

	UpdateResultVisibility();
}

void CParamPanel::UpdateResultVisibility()
{
	BOOL bLine = (m_nShapeType == 2);
	m_staticArea.ShowWindow(bLine ? SW_HIDE : SW_SHOW);
	m_staticAreaVal.ShowWindow(bLine ? SW_HIDE : SW_SHOW);
	m_staticPerimeter.ShowWindow(bLine ? SW_HIDE : SW_SHOW);
	m_staticPerimeterVal.ShowWindow(bLine ? SW_HIDE : SW_SHOW);
	m_staticLength.ShowWindow(bLine ? SW_SHOW : SW_HIDE);
	m_staticLengthVal.ShowWindow(bLine ? SW_SHOW : SW_HIDE);
}

void CParamPanel::OnSize(UINT nType, int cx, int cy)
{
	CWnd::OnSize(nType, cx, cy);
}

void CParamPanel::OnPaint()
{
	CPaintDC dc(this);
}

HBRUSH CParamPanel::OnCtlColor(CDC* pDC, CWnd* pWnd, UINT nCtlColor)
{
	if (pWnd && ::IsWindow(pWnd->GetSafeHwnd()) && pWnd->GetDlgCtrlID() == IDC_COLOR_PREVIEW)
	{
		pDC->SetBkColor(m_curColor);
		return (HBRUSH)m_colorBrush;
	}
	return NULL;
}

void CParamPanel::OnRadioRect()
{
	m_nShapeType = 0;
	UpdateResultVisibility();
}

void CParamPanel::OnRadioEllipse()
{
	m_nShapeType = 1;
	UpdateResultVisibility();
}

void CParamPanel::OnRadioLine()
{
	m_nShapeType = 2;
	UpdateResultVisibility();
}

void CParamPanel::OnBtnColor()
{
	CColorDialog dlg(m_curColor, CC_FULLOPEN, this);
	if (dlg.DoModal() == IDOK)
	{
		m_curColor = dlg.GetColor();
		m_colorBrush.DeleteObject();
		m_colorBrush.CreateSolidBrush(m_curColor);
		m_colorPreview.Invalidate();
	}
}

void CParamPanel::OnBtnCalc()
{
	CString sx1, sy1, sx2, sy2;
	m_editX1.GetWindowText(sx1);
	m_editY1.GetWindowText(sy1);
	m_editX2.GetWindowText(sx2);
	m_editY2.GetWindowText(sy2);

	double x1 = _tstof(sx1);
	double y1 = _tstof(sy1);
	double x2 = _tstof(sx2);
	double y2 = _tstof(sy2);

	double w = fabs(x2 - x1);
	double h = fabs(y2 - y1);
	double len = sqrt(w * w + h * h);

	m_dArea = 0;
	m_dPerimeter = 0;
	m_dLength = 0;

	CString strVal;

	if (m_nShapeType == 0) // 矩形
	{
		m_dArea = w * h;
		m_dPerimeter = 2.0 * (w + h);

		strVal.Format(_T("%.2f"), m_dArea);
		m_staticAreaVal.SetWindowText(strVal);
		strVal.Format(_T("%.2f"), m_dPerimeter);
		m_staticPerimeterVal.SetWindowText(strVal);
	}
	else if (m_nShapeType == 1) // 椭圆
	{
		const double PI = 3.14159265358979323846;
		double a = w / 2.0;
		double b = h / 2.0;
		m_dArea = PI * a * b;
		m_dPerimeter = PI * (3.0 * (a + b) - sqrt((3.0 * a + b) * (a + 3.0 * b)));

		strVal.Format(_T("%.2f"), m_dArea);
		m_staticAreaVal.SetWindowText(strVal);
		strVal.Format(_T("%.2f"), m_dPerimeter);
		m_staticPerimeterVal.SetWindowText(strVal);
	}
	else if (m_nShapeType == 2) // 直线
	{
		m_dLength = len;

		strVal.Format(_T("%.2f"), m_dLength);
		m_staticLengthVal.SetWindowText(strVal);
	}
}

void CParamPanel::OnBtnReset()
{
	m_dArea = 0;
	m_dPerimeter = 0;
	m_dLength = 0;
	m_staticAreaVal.SetWindowText(_T("0.00"));
	m_staticPerimeterVal.SetWindowText(_T("0.00"));
	m_staticLengthVal.SetWindowText(_T("0.00"));
}

void CParamPanel::OnBtnConfirm()
{
	if (!m_pDoc)
	{
		CMainFrame* pFrame = DYNAMIC_DOWNCAST(CMainFrame, GetParent());
		if (pFrame)
			m_pDoc = DYNAMIC_DOWNCAST(C仿真与设计第三次作业刘振毫2312167Doc, pFrame->GetActiveDocument());
	}
	if (!m_pDoc)
		return;

	CString sx1, sy1, sx2, sy2;
	m_editX1.GetWindowText(sx1);
	m_editY1.GetWindowText(sy1);
	m_editX2.GetWindowText(sx2);
	m_editY2.GetWindowText(sy2);

	m_pDoc->m_nShapeType   = m_nShapeType;
	m_pDoc->m_ptTopLeft.x  = (int)_tstof(sx1);
	m_pDoc->m_ptTopLeft.y  = (int)_tstof(sy1);
	m_pDoc->m_ptBottomRight.x = (int)_tstof(sx2);
	m_pDoc->m_ptBottomRight.y = (int)_tstof(sy2);
	m_pDoc->m_nLineStyle    = m_comboStyle.GetCurSel();
	m_pDoc->m_color          = m_curColor;
	m_pDoc->m_dArea          = m_dArea;
	m_pDoc->m_dPerimeter     = m_dPerimeter;
	m_pDoc->m_dLength        = m_dLength;
	m_pDoc->m_bDraw          = true;
	m_pDoc->UpdateAllViews(nullptr);
}
