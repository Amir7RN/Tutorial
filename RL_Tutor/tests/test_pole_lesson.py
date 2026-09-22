"""Numerical equivalence and UI regressions for the pole-placement lesson."""
import os,time,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QPA_FONTDIR','C:/Windows/Fonts')
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from ctrlcore.pole_lesson import regulator_response,second_order_poles
from ctrlcore.multibody import msd_ss,sea_ss,simulate_feedback
from ctrlcore.linear import place_poles

class PoleLessonTests(unittest.TestCase):
 def test_canonical_poles_for_all_damping_regimes(self):
  ss=msd_ss(5,.6,20)
  for z in (.1,.9,1,1.5,2):
   poles=second_order_poles(12,z)
   np.testing.assert_allclose(np.poly(poles),[1,24*z,144],atol=1e-10)
   np.testing.assert_allclose(place_poles(ss.A,ss.B,poles),[[700,120*z-.6]],atol=1e-8)

 def test_fast_response_matches_existing_integration(self):
  for ss,x0,poles,limit in (
   (msd_ss(5,.6,20),[.05,0],second_order_poles(12,.9),5),
   (msd_ss(5,.6,20),[.05,0],second_order_poles(12,1),600),
   (sea_ss(.02,.25,400),[.2,0,.2,0],second_order_poles(40,.8)+[-120+24j,-120-24j],None)):
   gain=place_poles(ss.A,ss.B,poles)
   ref=simulate_feedback(ss,gain,x0,dur=.3,dt=.0002,u_max=limit)
   fast=regulator_response(ss,gain,x0,dur=.3,dt=.0002,u_max=limit)
   for a,b in zip(ref,fast):np.testing.assert_allclose(a,b,rtol=1e-8,atol=1e-8)

 def test_panels_keep_axes_and_sensor_does_not_resimulate(self):
  from PySide6.QtWidgets import QApplication,QScrollArea,QLabel
  from PySide6.QtGui import QFont,QFontDatabase
  from app import theme
  from app.pages.statefb import StateFeedbackPage
  from app.widgets import Card
  app=QApplication.instance() or QApplication([])
  QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf');app.setFont(QFont('Segoe UI',9));app.setStyleSheet(theme.QSS)
  p=StateFeedbackPage();p.resize(1200,1000);p.show();app.processEvents()
  for name in ('_redraw_msd','_redraw_sea'):
   if name=='_redraw_sea':p._last_sea_plot=None
   start=time.perf_counter();getattr(p,name)();print(name,round(time.perf_counter()-start,3),'seconds',flush=True)
  p._sea_example(200);p._sea_example(600)
  self.assertEqual(len(p.c2.fig.axes),4)
  result=p._sea_response
  p.cmb_sensor.setCurrentIndex(2);p._sea_timer.stop();p._redraw_sea()
  self.assertIs(result,p._sea_response)
  self.assertEqual(len(p.c2.fig.axes),4)
  self.assertIn('NOT observable',p.t2.text())
  p._msd_example(120,5)
  self.assertNotEqual(p.st_sat._val.text(), "no")
  p.s_z.setValue(150);p._msd_timer.stop();p._redraw_msd()
  self.assertEqual(p.st_check._val.text(), 'matches')
  scroll=p.findChild(QScrollArea)
  out=Path('_shots/pole-lesson');out.mkdir(parents=True,exist_ok=True)
  for i,card in enumerate(p.findChildren(Card)):
   heading=next((l.text() for l in card.findChildren(QLabel) if l.objectName()=='CardTitle'),'')
   if heading.lower().startswith(('place the poles','one motor','takeaway')):
    scroll.ensureWidgetVisible(card,0,0);app.processEvents();card.grab().save(str(out/f'card-{i}.png'))
  p.close()

if __name__=='__main__':unittest.main()
