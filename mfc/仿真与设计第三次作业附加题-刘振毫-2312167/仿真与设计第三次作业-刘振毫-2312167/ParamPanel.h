#pragma once

#include "resource.h"

class CParamPanel : public CWnd
{
public:
	CParamPanel();
	virtual ~CParamPanel();

	void SetDocument(class C仿真与设计第三次作业刘振毫2312167Doc* pDoc) { m_pDoc = pDoc; }

protected:
	DECLARE_MESSAGE_MAP()

	afx_msg int  OnCreate(LPCREATESTRUCT lpCreateStruct);
	afx_msg void OnSize(UINT nType, int cx, int cy);
	afx_msg void OnRadioRect();
	afx_msg void OnRadioEllipse();
	afx_msg void OnRadioLine();
	afx_msg void OnBtnCalc();
	afx_msg void OnBtnReset();
	afx_msg void OnBtnConfirm();
	afx_msg void OnBtnColor();
	afx_msg void OnPaint();
	afx_msg BOOL OnEraseBkgnd(CDC* pDC);
	afx_msg HBRUSH OnCtlColor(CDC* pDC, CWnd* pWnd, UINT nCtlColor);

private:
	void CreateControls();
	void LayoutControls(int cx, int cy);
	void UpdateResultVisibility();

	CBrush      m_bgBrush;
	CBrush      m_colorBrush;
	CFont       m_font;

	CButton     m_radioRect;
	CButton     m_radioEllipse;
	CButton     m_radioLine;
	CEdit       m_editX1, m_editY1, m_editX2, m_editY2;
	CComboBox   m_comboStyle;
	CButton     m_btnColor;
	CButton     m_btnCalc;
	CButton     m_btnReset;
	CButton     m_btnConfirm;
	CStatic     m_staticShape;
	CStatic     m_staticCoord;
	CStatic     m_staticStyle;
	CStatic     m_staticColorLabel;
	CStatic     m_staticArea;
	CStatic     m_staticPerimeter;
	CStatic     m_staticLength;
	CStatic     m_staticAreaVal;
	CStatic     m_staticPerimeterVal;
	CStatic     m_staticLengthVal;
	CStatic     m_labelX1, m_labelY1, m_labelX2, m_labelY2;
	CStatic     m_colorPreview;

	int         m_nShapeType;   // 0=rect, 1=ellipse, 2=line
	COLORREF    m_curColor;
	double      m_dArea, m_dPerimeter, m_dLength;

	class C仿真与设计第三次作业刘振毫2312167Doc* m_pDoc;
};
