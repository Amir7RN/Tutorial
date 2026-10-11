"""Numerical invariants and navigation for the spatial teaching arm."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import unittest
import numpy as np
from PySide6.QtWidgets import QApplication

from app.widgets.rigid_arm_lab import arm_pose, spatial_example, RigidArmLab, LAB_PAGES


class ArmLabTests(unittest.TestCase):
    def test_link_lengths_rotation_and_table_constraint(self):
        for elbow in np.linspace(0, 150, 15):
            for constrained in (False, True):
                P, R, _ = arm_pose(np.radians([37, 20, elbow, 55]), constrained)
                np.testing.assert_allclose(np.linalg.norm(np.diff(P, axis=0), axis=1), [.8, .65])
                np.testing.assert_allclose(R.T @ R, np.eye(3), atol=1e-14)
                self.assertAlmostEqual(np.linalg.det(R), 1)
                if constrained:
                    self.assertAlmostEqual(P[-1, 2], 1)

    def test_elbow_velocity_matches_finite_difference(self):
        from ctrlcore.robokin import rot_exp
        q = np.radians([37, 20, 65, 55])
        P, _, _ = arm_pose(q)
        dq = np.array([0, 0, 1e-6, 0])
        numerical = (arm_pose(q+dq)[0][-1]-arm_pose(q-dq)[0][-1])/2e-6
        omega = rot_exp([0, 0, q[0]]) @ [0, -1., 0]
        np.testing.assert_allclose(numerical, np.cross(omega, P[-1]-P[1]), atol=1e-9)

    def test_twist_wrench_power_and_motion(self):
        P, R, _ = arm_pose(np.radians([30, 15, 65, 25]))
        for mode in range(3):
            moved, V, F, Vb, Fb = spatial_example(R, P[-1], mode, .7)
            self.assertAlmostEqual(V@F, Vb@Fb)
            self.assertGreater(np.linalg.norm(moved[:3,3]-P[-1]), .01)
            np.testing.assert_allclose(Fb[:3], 0, atol=1e-14)

    def test_all_capstone_steps_and_controls_render(self):
        app = QApplication.instance() or QApplication([])
        lab = RigidArmLab(capstone=True)
        lab.resize(1100, 900)
        lab.show()
        for lesson in range(8):
            lab.lesson.setCurrentIndex(lesson)
            for index in (0, 1):
                lab.constraint.setCurrentIndex(index)
                for slider, _ in lab.sliders:
                    slider.setValue(slider.minimum())
                    slider.setValue(slider.maximum())
            app.processEvents()
            lab.cv.draw()
            self.assertFalse(lab.cv.grab().isNull())
        lab.reset()
        lab.close()

    def test_only_requested_lessons_are_targeted(self):
        from app.pages import LESSON_CLASSES
        self.assertEqual(tuple(p.__name__ for p in LESSON_CLASSES[113:121]), LAB_PAGES)

    def test_page_integration_and_summary(self):
        from app.pages import PAGE_CLASSES, LESSON_CLASSES
        app = QApplication.instance() or QApplication([])
        page = LESSON_CLASSES[113]()
        self.assertFalse(hasattr(page, 'lesson_animation'))
        self.assertEqual(page.rigid_arm_lab.lesson.currentIndex(), 0)
        page.close()
        summary_type = next(c for c in PAGE_CLASSES if getattr(c, 'IS_SUMMARY', False)
                            and c.SECTION == page.SECTION)
        summary = summary_type()
        self.assertEqual(summary.arm_capstone.lesson.count(), 8)
        self.assertTrue(summary.arm_capstone.lesson.isEnabled())
        summary.close()
        app.processEvents()


if __name__ == '__main__':
    unittest.main()
