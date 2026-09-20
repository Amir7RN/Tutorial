"""Check prerequisite direction, recap coverage and the numerical SEA explanations."""
import math
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from app.pages import LESSON_CLASSES, PAGE_CLASSES, CONNECTIONS
from app.pages.section_summaries import RECAPS, get_movie
from ctrlcore.sea_teaching import SeaModel


class LessonConnectionsTests(unittest.TestCase):
    def test_every_original_lesson_has_an_earlier_connection(self):
        classes={c.__name__:c for c in LESSON_CLASSES}
        self.assertEqual(set(CONNECTIONS),set(classes))
        self.assertEqual([c.NUM for c in LESSON_CLASSES],list(range(1,96)))
        for key,connection in CONNECTIONS.items():
            self.assertTrue(connection.text)
            if classes[key].NUM>1:self.assertTrue(connection.previous)
            for previous in connection.previous:
                self.assertLess(classes[previous].NUM,classes[key].NUM)

    def test_every_section_ends_with_three_worked_movies(self):
        summaries=[c for c in PAGE_CLASSES if getattr(c,'IS_SUMMARY',False)]
        self.assertEqual(len(PAGE_CLASSES),115)
        self.assertEqual({c.SECTION for c in summaries},set(RECAPS))
        for i,c in enumerate(PAGE_CLASSES):
            if getattr(c,'IS_SUMMARY',False):
                self.assertEqual(PAGE_CLASSES[i-1].SECTION,c.SECTION)
                self.assertTrue(i==len(PAGE_CLASSES)-1 or PAGE_CLASSES[i+1].SECTION!=c.SECTION)
                self.assertGreaterEqual(len(RECAPS[c.SECTION]),3)
                for heading,text,num,key in RECAPS[c.SECTION]:
                    self.assertGreater(len(text),100)
                    self.assertGreaterEqual(len(get_movie(key).steps),3)

    def test_sea_antiresonances_are_port_specific(self):
        m=SeaModel()
        # Swap drive and sensor: different numerator zeros, nonzero cross response.
        xm,xl=m.harmonic(m.wn,'motor')
        self.assertAlmostEqual(abs(xm),0)
        self.assertGreater(abs(xl),0)
        self.assertAlmostEqual((-m.k*xl).real,1) # reaction balances motor torque
        xm,xl=m.harmonic(m.wa,'load')
        self.assertAlmostEqual(abs(xl),0)
        self.assertGreater(abs(xm),0)
        self.assertAlmostEqual((m.k*xm).real,-1)
        self.assertTrue(math.isinf(m.apparent_inertia(m.wa)))
        self.assertAlmostEqual(m.wr**2,m.wn**2+m.wa**2)
        with self.assertRaises(ValueError):m.harmonic(m.wr,'load')
        with self.assertRaises(ValueError):m.imposed_motor(m.wn)
        # Damping turns the exact driving-point zero into a nonzero dip.
        self.assertGreater(abs(m.harmonic(m.wa,'load',.6)[1]),1e-8)

    def test_sea_motion_satisfies_both_torque_equations(self):
        m=SeaModel()
        for w in (10,50,80,140,400):
            for drive in ('motor','load'):
                for damping in (0,.6):
                    xm,xl=m.harmonic(w,drive,damping)
                    spring=complex(m.k,damping*w)*(xm-xl)
                    self.assertAlmostEqual(abs(-m.jm*w*w*xm+spring-(drive=='motor')),0,places=9)
                    self.assertAlmostEqual(abs(-m.jl*w*w*xl-spring-(drive=='load')),0,places=9)
        self.assertAlmostEqual(m.apparent_inertia(.01),m.jm+m.jl,places=7)
        self.assertAlmostEqual(m.apparent_inertia(1e6),m.jl,places=7)
        self.assertAlmostEqual(SeaModel(k=1200).wr,2*m.wr)


if __name__=='__main__':unittest.main()
