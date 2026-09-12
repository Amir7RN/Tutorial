"""Deterministic numerical microscopes for the gait/network visual lessons.

Synthetic signals and untrained small networks, not a biomechanical model.
Gradients use the derivative of the mean loss (exactly one batch reduction).
"""
from copy import deepcopy

import numpy as np


LIMITS = np.array([40., 25.])  # illustrative ankle / knee torque scales
FEATURES = ['ankle angle', 'knee angle', 'ankle velocity', 'knee velocity',
            'sin phase', 'cos phase']


def gait(phase):
    p = np.asarray(phase, dtype=float).reshape(-1) * 2 * np.pi
    return np.column_stack([.5*np.sin(p), .6*np.sin(p-.7),
                            .5*np.cos(p), .6*np.cos(p-.7), np.sin(p), np.cos(p)])


def reference(x):
    """Arbitrary bounded teaching targets in normalized torque units."""
    return np.column_stack([.55*x[:, 4] + .15*x[:, 0],
                            -.4*x[:, 5] + .2*x[:, 1]])


class TraceNet:
    def __init__(self, sizes=(6, 4, 3, 2), activation='tanh', bn=False, seed=4):
        rng = np.random.default_rng(seed)
        self.W = [rng.normal(0, .6, (a, b)) for a, b in zip(sizes, sizes[1:])]
        self.b = [np.full(b, .08) for b in sizes[1:]]
        self.activation, self.bn = activation, bn
        self.gamma = np.ones(sizes[1])
        self.beta = np.zeros(sizes[1])
        calibration = gait(np.linspace(0, 1, 64, endpoint=False)) @ self.W[0] + self.b[0] if sizes[0] == 6 else np.zeros((2, sizes[1]))
        self.mean, self.var = calibration.mean(0), calibration.var(0) + .05

    def forward(self, x, training=False):
        self.cache = []
        for i, (w, b) in enumerate(zip(self.W, self.b)):
            z = x @ w + b
            u = z.copy()
            norm = None
            if i == 0 and self.bn:
                mean, var = (z.mean(0), z.var(0)) if training else (self.mean, self.var)
                inv = 1/np.sqrt(var + 1e-5)
                norm = (z-mean)*inv
                u = self.gamma*norm + self.beta
                self.bn_cache = (norm, inv, training)
            act = 'tanh' if i == len(self.W)-1 and w.shape[1] == 2 else self.activation
            if i == len(self.W)-1 and w.shape[1] == 1:
                act = 'linear'
            h = np.tanh(u) if act == 'tanh' else np.maximum(0, u) if act == 'relu' else u
            slope = 1-h*h if act == 'tanh' else (u > 0).astype(float) if act == 'relu' else np.ones_like(u)
            self.cache.append(dict(x=x, z=z, u=u, h=h, slope=slope, norm=norm))
            x = h
        return x

    def backward(self, grad):
        self.gW, self.gb = [None]*len(self.W), [None]*len(self.W)
        self.ggamma, self.gbeta = np.zeros_like(self.gamma), np.zeros_like(self.beta)
        for i in reversed(range(len(self.W))):
            c = self.cache[i]
            c['dh'] = grad.copy()
            du = grad*c['slope']
            dz = du
            if i == 0 and self.bn:
                norm, inv, training = self.bn_cache
                self.ggamma = (du*norm).sum(0)
                self.gbeta = du.sum(0)
                dn = du*self.gamma
                dz = inv*(dn-dn.mean(0)-norm*(dn*norm).mean(0)) if training else dn*inv
            c['du'], c['dz'] = du, dz
            self.gW[i], self.gb[i] = c['x'].T @ dz, dz.sum(0)
            grad = dz @ self.W[i].T
            c['dx'] = grad.copy()
        return grad

    def update(self, lr):
        for w, b, gw, gb in zip(self.W, self.b, self.gW, self.gb):
            w -= lr*gw
            b -= lr*gb
        if self.bn:
            self.gamma -= lr*self.ggamma
            self.beta -= lr*self.gbeta


def supervised(phase=.35, activation='tanh', bn=False, training=False, lr=.05):
    net = TraceNet(activation=activation, bn=bn)
    phases = np.mod(phase + np.arange(8)/8, 1) if training else np.array([phase])
    x = gait(phases)
    pred = net.forward(x, training)
    target = reference(x)
    loss = .5*np.mean(np.sum((pred-target)**2, axis=1))
    net.backward((pred-target)/len(x))
    after = deepcopy(net)
    after.update(lr)
    out = after.forward(x, training)
    return dict(net=net, after=after, x=x, pred=pred, target=target, out=out,
                loss=loss, loss_after=.5*np.mean(np.sum((out-target)**2, axis=1)))


def ddpg_snapshot(phase=.35, lr=.03, terminal=False):
    """One actual replay minibatch update, with frozen targets and critic."""
    x = gait(np.mod(phase+np.arange(8)/8, 1))
    x2 = gait(np.mod(phase+np.arange(8)/8+.03, 1))
    actor = TraceNet(seed=4)
    critic = TraceNet((8, 4, 3, 1), seed=9)
    target_actor, target_critic = deepcopy(actor), deepcopy(critic)
    # A stored behavior action need not equal the current actor's action.
    replay_a = np.clip(reference(x)+.12, -1, 1)
    reward = -np.sum((replay_a-reference(x))**2, axis=1, keepdims=True)
    next_a = target_actor.forward(x2)
    next_q = target_critic.forward(np.c_[x2, next_a])
    y = reward + .95*(1-int(terminal))*next_q
    q = critic.forward(np.c_[x, replay_a])
    critic.backward(2*(q-y)/len(x))
    fitted = deepcopy(critic)
    fitted.update(lr)
    fitted_q = fitted.forward(np.c_[x, replay_a])
    policy_a = actor.forward(x)
    policy_q = fitted.forward(np.c_[x, policy_a])
    da = fitted.backward(-np.ones_like(policy_q)/len(x))[:, -2:]
    actor.backward(da)
    updated = deepcopy(actor)
    updated.update(lr)
    new_a = updated.forward(x)
    new_q = fitted.forward(np.c_[x, new_a])
    soft = deepcopy(target_actor)
    soft_c = deepcopy(target_critic)
    for dst, src in ((soft, updated), (soft_c, fitted)):
        for i in range(len(dst.W)):
            dst.W[i] = .95*dst.W[i]+.05*src.W[i]
            dst.b[i] = .95*dst.b[i]+.05*src.b[i]
    return dict(actor=actor, critic=critic, fitted=fitted, updated=updated,
                target_actor=target_actor, target_critic=target_critic,
                soft=soft, soft_c=soft_c, x=x, x2=x2, replay_a=replay_a,
                reward=reward, next_q=next_q, y=y, q=q, fitted_q=fitted_q,
                policy_a=policy_a, new_a=new_a, da=da, policy_q=policy_q, new_q=new_q)
