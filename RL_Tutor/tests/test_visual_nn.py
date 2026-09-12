"""Numerical checks for the values taught by the visual network lessons."""
import unittest
from copy import deepcopy

import numpy as np

from rlcore.visual_nn import TraceNet, gait, reference, supervised, ddpg_snapshot


class VisualNetworkTests(unittest.TestCase):
    def test_all_parameter_gradients_against_finite_differences(self):
        x = gait([.13, .32, .56, .87])
        for activation in ('tanh', 'relu', 'linear'):
            for bn, training in ((False, False), (True, False), (True, True)):
                net = TraceNet(activation=activation, bn=bn)
                pred = net.forward(x, training)
                net.backward((pred-reference(x))/len(x))
                params = list(zip(net.W, net.gW))+list(zip(net.b, net.gb))
                if bn:
                    params += [(net.gamma, net.ggamma), (net.beta, net.gbeta)]
                def loss():
                    return .5*np.mean(np.sum((net.forward(x, training)-reference(x))**2, axis=1))
                for p, g in params:
                    for index in np.ndindex(p.shape):
                        old = p[index]
                        p[index] = old+1e-6
                        plus = loss()
                        p[index] = old-1e-6
                        minus = loss()
                        p[index] = old
                        self.assertAlmostEqual(g[index], (plus-minus)/2e-6, places=6)

    def test_ddpg_actor_gradient_and_frozen_critic(self):
        d = ddpg_snapshot()
        actor, critic = d['actor'], deepcopy(d['fitted'])
        frozen = [w.copy() for w in critic.W]
        def objective():
            a = actor.forward(d['x'])
            return -critic.forward(np.c_[d['x'], a]).mean()
        for p, g in zip(actor.W, actor.gW):
            for index in np.ndindex(p.shape):
                old = p[index]
                p[index] = old+1e-6
                plus = objective()
                p[index] = old-1e-6
                minus = objective()
                p[index] = old
                self.assertAlmostEqual(g[index], (plus-minus)/2e-6, places=6)
        for old, new in zip(frozen, critic.W):
            np.testing.assert_array_equal(old, new)

    def test_target_mask_soft_update_and_loss(self):
        d = ddpg_snapshot(terminal=True)
        np.testing.assert_array_equal(d['y'], d['reward'])
        d = ddpg_snapshot()
        self.assertLess(np.mean((d['fitted_q']-d['y'])**2), np.mean((d['q']-d['y'])**2))
        self.assertGreater(d['new_q'].mean(), d['policy_q'].mean())
        for target, online, soft in ((d['target_actor'], d['updated'], d['soft']),
                                     (d['target_critic'], d['fitted'], d['soft_c'])):
            for old, new, blended in zip(target.W, online.W, soft.W):
                np.testing.assert_allclose(blended, .95*old+.05*new)
        for training in (True, False):
            d = supervised(bn=True, training=training)
            self.assertLess(d['loss_after'], d['loss'])


if __name__ == '__main__':
    unittest.main()
