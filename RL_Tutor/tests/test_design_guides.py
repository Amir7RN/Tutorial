import os,sys,time,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen');os.environ.setdefault('QT_QPA_FONTDIR','C:/Windows/Fonts')
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from ctrlcore.multibody import msd_ss,sea_ss,lqr_design
from ctrlcore.pole_lesson import linear_regulator_response
class DesignLessonTests(unittest.TestCase):
 def test_exact_linear_response_and_stiff_modes(self):
  from ctrlcore.linear import StateSpace
  ss=StateSpace(np.diag([-1.,-100000.]),np.zeros((2,1)),np.eye(2),np.zeros((2,1)))
  ts,xs,us,_=linear_regulator_response(ss,np.zeros((1,2)),[1,1],1,.01)
  np.testing.assert_allclose(xs[:,0],np.exp(-ts),rtol=1e-10)
  self.assertLess(abs(xs[-1,1]),1e-10)
  ss=sea_ss(.02,.25,400);q=np.diag([.001,.001,1e6,1e6]);r=np.array([[.0001]])
  design=lqr_design(ss,q,r,x0=np.array([.2,0,.2,0]))
  ts,xs,_,_=linear_regulator_response(ss,design.K,[.2,0,.2,0],1.5,.0002)
  self.assertTrue(np.isfinite(xs).all());self.assertLess(np.linalg.norm(xs[-1]),.2)
 def test_guided_widgets_and_scale_invariance(self):
  from PySide6.QtWidgets import QApplication,QLabel
  from PySide6.QtGui import QFont,QFontDatabase
  from app import theme
  from app.pages.statefb import LQRPage
  from app.pages.ctrldesign import ObserverPage
  from app.widgets import Card
  app=QApplication.instance() or QApplication([]);QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf');app.setFont(QFont('Segoe UI',9));app.setStyleSheet(theme.QSS)
  out=Path('_shots/design-guides');out.mkdir(parents=True,exist_ok=True)
  for cls in (LQRPage,ObserverPage):
   p=cls();p.resize(1200,1000);p.show();app.processEvents()
   if cls==LQRPage:
    p._lqr_example('msd',(20,30,100,0));gains=(p.st_lk1._val.text(),p.st_lk2._val.text());line=p.c3.axes[0].lines[0].get_ydata().copy()
    p._lqr_example('msd',(20,30,100,10));self.assertEqual(gains,(p.st_lk1._val.text(),p.st_lk2._val.text()));np.testing.assert_allclose(line,p.c3.axes[0].lines[0].get_ydata(),atol=1e-8)
    for values in ((30,10,-30,-10),(40,10,-30,-10),(40,10,50,-10)):p._lqr_example('sea',values)
    for values, expected in (((20,30,20,0),(False,True)), ((10,30,100,0),(True,False)), ((20,30,100,0),(True,True))):
     p._lqr_example('msd',values);self.assertEqual(p.msd_requirements,expected)
    for values, expected in (((30,10,-30,-10),(False,True,True)), ((40,10,-30,-10),(True,False,True)), ((40,10,50,-10),(True,True,True))):
     p._lqr_example('sea',values);self.assertEqual(p.sea_requirements,expected)
    methods=('_redraw_lqr_msd','_redraw_lqr_sea')
   else:
    for values in ((60,20,0),(300,20,0),(60,0,0)):p._observer_example('velocity',values)
    for values in ((20,25,10),(-20,25,10),(20,25,60)):p._observer_example('load',values)
    self.assertAlmostEqual(float(p.st_est._val.text()),2,delta=.2)
    p._observer_example('load',(0,25,0));self.assertNotEqual(p.st_conv._val.text(),'—')
    methods=('_redraw_obs','_redraw_dob')
   for name in methods:
    start=time.perf_counter();getattr(p,name)();print(cls.__name__,name,round(time.perf_counter()-start,3),'s',flush=True)
   for i,card in enumerate(p.findChildren(Card)):
    heading=next((w.text().lower() for w in card.findChildren(QLabel) if w.objectName()=='CardTitle'),'')
    if heading.startswith(('worked problem','price the mass','tune a sea','finite difference','watch it recover','duality','lqi')):
     app.processEvents();card.grab().save(str(out/f'{cls.__name__}-{i}.png'))
   p.close()
if __name__=='__main__':unittest.main()
