import os
import sys
import unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QPA_FONTDIR','C:/Windows/Fonts')
from ctrlcore.biped_lesson import joint_growth_rates, sampled_feedback, capture_delay_limit, motion_response
from ctrlcore.multibody import PlanarLeg, leg_ss, lqr_design, bryson
from ctrlcore.linear import StateSpace


class BipedContextTests(unittest.TestCase):
    def test_poles_units_and_capture(self):
        leg=PlanarLeg();ss=leg_ss(leg);rates=joint_growth_rates(leg)
        positive=sorted(v.real for v in np.linalg.eigvals(ss.A) if v.real>0)
        np.testing.assert_allclose(sorted(rates),positive)
        self.assertEqual(int(np.argmax(rates)),1)
        self.assertAlmostEqual(capture_delay_limit(.08,.1,np.sqrt(9.81/.75)),.06170,places=4)
        self.assertEqual(capture_delay_limit(.12,.1,3.6),0)
        self.assertAlmostEqual(abs(motion_response(1,400,28,[0])[0]),1)
        self.assertLess(abs(motion_response(4,400,28,[20])[0]),abs(motion_response(1,400,28,[20])[0]))

    def test_sample_hold_exactness_and_stability(self):
        # Integrator: x[k+1] = (1-K/fs)x[k], an independent analytic check.
        ss=StateSpace(np.zeros((1,1)),np.ones((1,1)),np.ones((1,1)),np.zeros((1,1)))
        t,x,u,sat,rho=sampled_feedback(ss,np.array([[2.]]),[1],10,100,duration=.5)
        np.testing.assert_allclose(x[:,0],.8**np.arange(len(t)),atol=1e-12)
        self.assertAlmostEqual(rho,.8);self.assertEqual(sat,0)
        ss=leg_ss(PlanarLeg());res=lqr_design(ss,bryson([.05,.08,.15,.5,.8,1.5]),bryson([150]*3))
        fast=sampled_feedback(ss,res.K,[.09,0,0,0,0,0],500,150)
        slow=sampled_feedback(ss,res.K,[.09,0,0,0,0,0],5,150)
        self.assertLess(fast[-1],1);self.assertGreater(slow[-1],1)
        self.assertLess(np.linalg.norm(fast[1][-1]),np.linalg.norm(fast[1][0]))

    def test_pages_and_rendered_cards(self):
        from PySide6.QtWidgets import QApplication,QLabel,QScrollArea
        from PySide6.QtGui import QFont,QFontDatabase
        from app import theme
        from app.pages.capstone import BipedSystemsPage,BipedActuatorsPage
        from app.widgets import Card
        app=QApplication.instance() or QApplication([])
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
        app.setFont(QFont('Segoe UI',9));app.setStyleSheet(theme.QSS)
        out=ROOT/'_shots/biped-context';out.mkdir(parents=True,exist_ok=True)
        for cls in (BipedSystemsPage,BipedActuatorsPage):
            page=cls();page.resize(1280,950);page.show();app.processEvents()
            if cls is BipedSystemsPage:
                self.assertIn('8.18',page.st_pa._val.text())
                page.s_fs.setValue(5);self.assertGreater(page.sampled_radius,1)
                page.s_fs.setValue(500);self.assertLess(page.sampled_radius,1)
                for push in (0,30,100): page.s_push.setValue(push)
                page.s_push.setValue(30)
            else:
                for top in range(4):
                    page.cmb_top.setCurrentIndex(top)
                    for joint in range(3):page.cmb_joint.setCurrentIndex(joint)
                page.cmb_top.setCurrentIndex(0);page.cmb_joint.setCurrentIndex(0)
            for i,card in enumerate(page.findChildren(Card)):
                heading=next((w.text() for w in card.findChildren(QLabel) if w.objectName()=='CardTitle'),'')
                if heading.lower().startswith(('1 ·','2 ·','3 ·','4 ·','6 ·','from page','sample the')):
                    page.findChild(QScrollArea).ensureWidgetVisible(card)
                    app.processEvents();card.grab().save(str(out/f'{cls.__name__}-{i}.png'))
                for label in card.findChildren(QLabel):
                    self.assertNotIn('\\begin{',label.text(),'Formula failed to render')
            page.close()

if __name__=='__main__':unittest.main()
