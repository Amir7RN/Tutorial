"""Step-through gait, differentiation and actor/critic visual microscopes."""
from copy import deepcopy

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QComboBox, QCheckBox, QHBoxLayout, QPushButton, QSlider

from rlcore.visual_nn import FEATURES, LIMITS, gait, supervised, ddpg_snapshot
from .. import theme
from .common import Card, body
from .plot import MplCanvas


class NetworkLab(Card):
    NN_STEPS = ['Read sensors', 'Scale the state', 'Dense layer 1', 'Normalize',
                'Activate layer 1', 'Hidden layer 2', 'Bound the torques',
                'Compare with target', 'Back through output',
                'Back through hidden layers', 'Update weights → run again']
    RL_STEPS = ['Read a replay batch', 'Target actor → next action',
                'Target critic → TD target', 'Online critic → prediction',
                'Critic backward', 'Update critic only', 'Online actor → action',
                'Frozen critic → action gradient', 'Actor backward',
                'Update actor only', 'Slowly move both target networks']

    def __init__(self, mode='forward', parent=None):
        super().__init__('Gait to torque · visual microscope', parent)
        self.mode = mode
        self.rl = mode == 'ddpg'
        self.steps = self.RL_STEPS if self.rl else self.NN_STEPS
        self.add(body('Synthetic exoskeleton / prosthesis example • ankle + knee • '
                      'small, untrained networks so every neuron is visible. '
                      'Torque scales are illustrative, not device settings.'))
        row = QHBoxLayout()
        self.prev = QPushButton('← Back')
        self.play = QPushButton('Play steps')
        self.next = QPushButton('Next →')
        self.reset = QPushButton('Reset')
        self.stage = QComboBox()
        self.stage.addItems([f'{i+1:02d}  {s}' for i, s in enumerate(self.steps)])
        for w in (self.prev, self.play, self.next, self.reset, self.stage):
            row.addWidget(w)
        row.setStretch(4, 1)
        self.add_layout(row)
        controls = QHBoxLayout()
        self.phase = QSlider(Qt.Horizontal)
        self.phase.setRange(0, 99)
        self.phase.setValue(35)
        self.phase.setAccessibleName('Selected instant within stride')
        self.phase_label = body('')
        controls.addWidget(self.phase_label)
        controls.addWidget(self.phase, 1)
        self.activation = QComboBox()
        self.activation.addItems(['tanh', 'relu', 'linear'])
        self.activation.setAccessibleName('Hidden activation function')
        self.bn = QCheckBox('Batch norm in layer 1')
        self.training = QCheckBox('Training batch (8 samples)')
        self.terminal = QCheckBox('Episode truly terminated')
        if self.rl:
            controls.addWidget(self.terminal)
        else:
            controls.addWidget(self.activation)
            controls.addWidget(self.bn)
            controls.addWidget(self.training)
        self.add_layout(controls)
        detail = QHBoxLayout()
        detail.addWidget(body('Inspect hidden neuron'))
        self.neuron = QComboBox()
        self.neuron.addItems(['H1.1', 'H1.2', 'H1.3', 'H1.4'])
        detail.addWidget(self.neuron)
        detail.addWidget(body('SGD step size'))
        self.lr = QSlider(Qt.Horizontal)
        self.lr.setRange(1, 30)
        self.lr.setValue(5)
        self.lr.setAccessibleName('SGD learning rate')
        detail.addWidget(self.lr, 1)
        self.lr_label = body('')
        detail.addWidget(self.lr_label)
        if self.rl:
            self.neuron.hide()
            detail.itemAt(0).widget().hide()
        self.add_layout(detail)
        self.caption = body('')
        self.caption.setMinimumHeight(66)
        self.add(self.caption)
        self.overview = MplCanvas(height=3.2)
        self.overview.fig.set_layout_engine('constrained')
        self.overview.setMinimumHeight(300)
        self.overview.setAccessibleName('Network flow with live values and direction arrows')
        self.add(self.overview)
        self.detail = MplCanvas(height=3.1, ncols=2)
        self.detail.fig.set_layout_engine('constrained')
        self.detail.setMinimumHeight(300)
        self.detail.setAccessibleName('Numerical detail for the selected computation step')
        self.add(self.detail)
        self.readout = body('')
        self.readout.setMinimumHeight(55)
        self.add(self.readout)
        self.add(body('Timing: each phase selection is one current sensor sample. '
                      'A direct torque policy runs repeatedly within a stride. '
                      'A stride-level policy instead reads a completed stride summary and selects '
                      'parameters or a profile for the next stride; it cannot read future samples. '
                      'Replay minibatches contain recorded transitions, not a live future stride.', dim=True))
        self.timer = QTimer(self)
        self.timer.setInterval(1800)
        self.timer.timeout.connect(self.advance)
        self.prev.clicked.connect(lambda: self.move(-1))
        self.next.clicked.connect(lambda: self.move(1))
        self.reset.clicked.connect(self.restart)
        self.play.clicked.connect(self.toggle)
        for obj in (self.stage, self.activation, self.neuron):
            obj.currentIndexChanged.connect(self.redraw)
        for obj in (self.phase, self.lr):
            obj.valueChanged.connect(self.redraw)
        for obj in (self.bn, self.training, self.terminal):
            obj.toggled.connect(self.redraw)
        if mode == 'backward':
            self.stage.setCurrentIndex(7)
        elif mode == 'normalization':
            self.bn.setChecked(True)
            self.training.setChecked(True)
            self.stage.setCurrentIndex(3)
        elif mode == 'activation':
            self.stage.setCurrentIndex(4)
        self.redraw()

    def hideEvent(self, event):
        self.stop()
        super().hideEvent(event)

    def stop(self):
        self.timer.stop()
        self.play.setText('Play steps')

    def toggle(self):
        if self.timer.isActive():
            self.stop()
        else:
            if self.stage.currentIndex() == 10:
                self.stage.setCurrentIndex(0)
            self.timer.start()
            self.play.setText('Pause')

    def move(self, amount):
        self.stop()
        self.stage.setCurrentIndex(max(0, min(10, self.stage.currentIndex()+amount)))

    def advance(self):
        if self.stage.currentIndex() == 10:
            self.stop()
        else:
            self.stage.setCurrentIndex(self.stage.currentIndex()+1)

    def restart(self):
        self.stop()
        self.stage.setCurrentIndex(0)
        self.phase.setValue(35)
        self.lr.setValue(5)

    def redraw(self, *_):
        self.phase_label.setText(f'Stride {self.phase.value()}%')
        self.lr_label.setText(f'{self.lr.value()/100:.2f}')
        self.prev.setEnabled(self.stage.currentIndex() > 0)
        self.next.setEnabled(self.stage.currentIndex() < 10)
        if self.rl:
            self.draw_rl()
        else:
            self.draw_nn()

    @staticmethod
    def bars(ax, values, labels, heading, ylabel='value'):
        v = np.asarray(values)
        ax.bar(np.arange(len(v)), v, color=[theme.CYAN if a >= 0 else theme.ORANGE for a in v])
        ax.axhline(0, color=theme.TEXT_DIM, lw=.7)
        ax.set_xticks(np.arange(len(v)), labels, fontsize=8)
        ax.set_title(heading, fontsize=10)
        ax.set_ylabel(ylabel)
        ax.margins(y=.25)
        for i, a in enumerate(v):
            ax.annotate(f'{a:+.3f}', (i, a), xytext=(0, 4 if a >= 0 else -12),
                        textcoords='offset points', ha='center', fontsize=8, color=theme.TEXT)

    def network(self, net, stage):
        ax = self.overview.ax
        ax.clear()
        ax.set_axis_off()
        ax.set_xlim(-.5, 3.6)
        ax.set_ylim(-1, 6.5)
        backward = stage in (8, 9)
        values = ([net.cache[0]['dx'][0]]+[c['dh'][0] for c in net.cache]) if backward else ([net.cache[0]['x'][0]]+[c['h'][0] for c in net.cache])
        if stage == 2:
            values[1] = net.cache[0]['z'][0]
        elif stage == 3:
            values[1] = net.cache[0]['u'][0]
        ys = [np.linspace(5.2, .5, len(v)) for v in values]
        active = 1 if stage in (2, 3, 4, 9) else 2 if stage == 5 else 3 if stage >= 6 else 0
        for k, w in enumerate(net.W):
            for i in range(w.shape[0]):
                for j in range(w.shape[1]):
                    focus = k == active-1
                    ax.plot([k, k+1], [ys[k][i], ys[k+1][j]],
                            color=theme.CYAN if w[i, j] >= 0 else theme.ORANGE,
                            lw=.5+min(abs(w[i, j]), 2)*1.8, alpha=.65 if focus else .12)
        names = ['State · 6', 'Hidden 1 · 4', 'Hidden 2 · 3', 'Action · 2']
        for k, v in enumerate(values):
            ax.text(k, 6.1, names[k], ha='center', color=theme.TEXT, fontsize=10)
            visible = k <= active or backward or stage == 10
            for i, val in enumerate(v):
                label = (f'{val:+.3f}' if backward else f'{val:+.2f}') if visible else '?'
                ax.text(k, ys[k][i], label, ha='center', va='center', fontsize=9,
                        color=theme.TEXT, bbox=dict(boxstyle='circle,pad=.3',
                        fc=theme.BG_RAISED, ec=theme.WARN if k == active else theme.BORDER))
                if k == 0:
                    ax.text(k-.18, ys[k][i]+.35, FEATURES[i], fontsize=7, color=theme.TEXT_DIM, ha='center')
                if k == 3 and visible:
                    out_label = f'{["ankle", "knee"][i]}\ndL/da' if backward else f'{["ankle", "knee"][i]}\n{val*LIMITS[i]:+.2f} Nm'
                    ax.text(k+.25, ys[k][i], out_label,
                            color=theme.TEXT, fontsize=9, va='center')
        start, end = (3, 0) if backward else (0, 3)
        ax.annotate('', xy=(end, -.2), xytext=(start, -.2),
                    arrowprops=dict(arrowstyle='->', color=theme.PINK if backward else theme.CYAN, lw=2))
        legend = 'Nodes = dL/d activation' if backward else 'H1 nodes = weighted sums z' if stage == 2 else 'H1 nodes = normalized values u' if stage == 3 else 'Nodes = activations'
        ax.text(1.5, -.6, legend+' · edges = weights · cyan + / orange − · thickness = |weight|', ha='center', color=theme.TEXT, fontsize=8)
        self.overview.refresh(layout=False)

    def draw_nn(self):
        s, j = self.stage.currentIndex(), self.neuron.currentIndex()
        d = supervised(self.phase.value()/100, self.activation.currentText(),
                       self.bn.isChecked(), self.training.isChecked(), self.lr.value()/100)
        n, c = d['net'], d['net'].cache[0]
        self.snapshot = d
        self.network(d['after'] if s == 10 else n, s)
        self.detail.clear()
        a, b = self.detail.axes
        explanations = [
            'Read the highlighted instant in the gait cycle. The six inputs describe the current joint motion and phase; a feedforward network has no memory unless you supply a history window.',
            'Convert sensor units into comparable scales. Here angle / 60° and velocity / (120π °/s) define four inputs for a synthetic one-second stride; sin and cos encode phase without a jump at the stride boundary.',
            'Follow one hidden neuron: each input contributes x × weight. Add all six contributions and the bias. A neuron mixes sensor information; it is not assigned a physical meaning in advance.',
            'Batch normalization acts on each feature across samples. Training uses the current batch; inference uses stored statistics. Its learned scale γ and shift β come after centering and rescaling.',
            'The activation bends the weighted sum. The dot shows this neuron’s value; its local slope decides how much gradient survives on the backward pass. Output neurons still use tanh.',
            'Layer 2 mixes the activated features from layer 1 and applies another activation. Adding layers creates useful nonlinear combinations only when the activations bend the mapping.',
            'The final dense layer produces two logits. tanh bounds each to −1…1; multiply by 40 Nm for ankle and 25 Nm for knee. A saturated output has a small slope and learns slowly.',
            'For this supervised warm-up only, compare predicted torque with a synthetic teaching target. The loss seeds the backward pass. DDPG replaces this target torque with the critic’s action gradient.',
            'Backward starts at the error, then multiplies by the output tanh slope. Each output sends sensitivity through its incoming weights; contributions from BOTH joints add at a shared hidden neuron.',
            'At each hidden layer, sum sensitivities from all downstream paths, then multiply by the activation slope. With batch norm, the gradient also crosses centering, variance, γ and β.',
            'Only the optimizer changes parameters. Apply one SGD step, then run the SAME input again. The old and new torque predictions show the effect; step size controls the size of the change.'
        ]
        self.caption.setText(f'<b>{s+1}/11 · {self.steps[s]}</b><br>{explanations[s]}')
        if s in (0, 1):
            phase = np.linspace(0, 1, 101)
            signals = gait(phase)
            for k, name in enumerate(['ankle', 'knee']):
                a.plot(phase*100, signals[:, k]*60, label=name, color=[theme.CYAN, theme.ORANGE][k])
            a.axvline(self.phase.value(), color=theme.WARN, ls='--')
            a.set(xlabel='Stride (%)', ylabel='Synthetic angle (degrees)', title='A moving cursor selects one sensor sample')
            self.detail.legend(a)
            self.bars(b, d['x'][0], ['ank θ', 'knee θ', 'ank ω', 'knee ω', 'sin φ', 'cos φ'], 'The actual state vector', 'normalized input')
        elif s == 2:
            contrib = c['x'][0]*n.W[0][:, j]
            self.bars(a, np.r_[contrib, n.b[0][j]], ['ank θ', 'knee θ', 'ank ω', 'knee ω', 'sin φ', 'cos φ', 'bias'], f'H1.{j+1}: six weighted inputs + bias')
            cumulative = np.cumsum(np.r_[contrib, n.b[0][j]])
            a.set_xticklabels(['ank θ', 'knee θ', 'ank ω', 'knee ω', 'sin φ', 'cos φ', 'bias'], rotation=25)
            b.plot(range(7), cumulative, 'o-', color=theme.CYAN)
            b.axhline(c['z'][0, j], color=theme.WARN, ls='--')
            b.set(xlabel='Add contribution 1 → 6 → bias', ylabel='Running sum z', title=f'Final weighted sum z = {c["z"][0,j]:+.4f}')
        elif s == 3:
            batch = gait(np.mod(self.phase.value()/100+np.arange(8)/8, 1))
            z = batch@n.W[0]+n.b[0]
            mean, var = (z.mean(0), z.var(0)) if self.training.isChecked() else (n.mean, n.var)
            u = (z-mean)/np.sqrt(var+1e-5)*n.gamma+n.beta if n.bn else z
            for k in range(8):
                a.plot([0, 1], [z[k, j], u[k, j]], 'o-', alpha=1 if k == 0 else .4,
                       color=theme.WARN if k == 0 else theme.CYAN)
            a.set_xticks([0, 1], ['Before BN: z', 'After BN: u' if n.bn else 'BN bypassed'])
            a.set(ylabel=f'H1.{j+1} value', title='One feature across eight samples; gold = selected')
            self.bars(b, [mean[j], np.sqrt(var[j]+1e-5), n.gamma[j], n.beta[j]], ['mean', 'std + ε', 'γ', 'β'], 'Batch statistics' if self.training.isChecked() else 'Stored calibration statistics')
        elif s == 4:
            t = np.linspace(-4, 4, 200)
            act = n.activation
            h = np.tanh(t) if act == 'tanh' else np.maximum(t, 0) if act == 'relu' else t
            slope = 1-h*h if act == 'tanh' else (t > 0).astype(float) if act == 'relu' else np.ones_like(t)
            for ax, curve, val, heading in ((a, h, c['h'][0,j], 'Forward: bend the signal'), (b, slope, c['slope'][0,j], 'Backward: multiply by this slope')):
                ax.plot(t, curve, color=theme.CYAN)
                ax.scatter([c['u'][0,j]], [val], color=theme.WARN, s=70, zorder=4)
                ax.set(xlabel='Activation input u', ylabel='activation' if ax is a else 'local derivative', title=f'{heading} · {val:.3f}')
        elif s == 5:
            self.bars(a, n.cache[1]['z'][0], ['H2.1', 'H2.2', 'H2.3'], 'Layer 2: weighted sums')
            self.bars(b, n.cache[1]['h'][0], ['H2.1', 'H2.2', 'H2.3'], f'Layer 2: after {n.activation}')
        elif s in (6, 7, 10):
            idx = np.arange(2)
            for offset, vals, label, color in [(-.25, d['pred'][0], 'before', theme.CYAN), (0, d['target'][0], 'teaching target', theme.WARN), (.25, d['out'][0] if s == 10 else d['pred'][0], 'after SGD' if s == 10 else 'prediction again', theme.PINK)]:
                if offset == .25 and s != 10:
                    continue
                a.bar(idx+offset, vals*LIMITS, width=.24, label=label, color=color)
            a.set_xticks(idx, ['Ankle', 'Knee'])
            a.set(ylabel='Torque (Nm)', title='Same sensor input; compare torque output')
            self.detail.legend(a)
            if s == 10:
                delta = d['after'].W[0]-n.W[0]
                b.imshow(delta, cmap='coolwarm', aspect='auto', vmin=-max(abs(delta).max(), 1e-8), vmax=max(abs(delta).max(), 1e-8))
                b.set(xticks=range(4), xticklabels=['H1.1', 'H1.2', 'H1.3', 'H1.4'], yticks=range(6), yticklabels=FEATURES, title='Actual ΔW in layer 1 (numbers on cells)')
                b.grid(False)
                for row in range(6):
                    for col in range(4):
                        color = 'white' if abs(delta[row,col]) > .65*max(abs(delta).max(), 1e-8) else 'black'
                        b.text(col, row, f'{delta[row,col]:+.3f}', ha='center', va='center', color=color, fontsize=8)
            else:
                self.bars(b, n.cache[-1]['slope'][0] if s == 6 else (d['pred']-d['target'])[0], ['Ankle', 'Knee'], 'Output tanh derivative' if s == 6 else 'Loss seed: prediction − target', 'dimensionless')
        elif s == 8:
            oc = n.cache[-1]
            self.bars(a, np.r_[oc['dh'][0], oc['dz'][0]], ['ank in', 'knee in', 'ank out', 'knee out'], 'Output backward: incoming gradient × tanh slope')
            contributions = n.W[-1]*oc['dz'][0]
            for k in range(2):
                b.bar(np.arange(3)+(k-.5)*.3, contributions[:, k], width=.3, label=['ankle path', 'knee path'][k], color=[theme.CYAN, theme.ORANGE][k])
            b.plot(range(3), contributions.sum(1), 'o', color=theme.WARN, label='sum of both paths')
            b.set(xticks=range(3), xticklabels=['H2.1', 'H2.2', 'H2.3'], ylabel='dL / dh₂ (selected sample)', title='Branch gradients ADD at shared neurons')
            self.detail.legend(b)
        else:
            self.bars(a, [c['dh'][0,j], c['slope'][0,j], c['du'][0,j], c['dz'][0,j]], ['incoming', 'slope', 'after act', 'after BN'], f'H1.{j+1}: chain rule through every operation')
            self.bars(b, n.gW[0][:, j], ['ank θ', 'knee θ', 'ank ω', 'knee ω', 'sin φ', 'cos φ'], 'Weight gradients = sum over samples of x × dL/dz', 'dL/dW')
        w, grad = n.W[0][0, j], n.gW[0][0, j]
        self.readout.setText(f'<b>Follow weight ankle angle → H1.{j+1}:</b> {w:+.5f} − {self.lr.value()/100:.2f} × ({grad:+.5f}) = '
                             f'<b>{d["after"].W[0][0,j]:+.5f}</b> after one SGD step.<br>'
                             f'Loss ½ mean Σ(normalized torque error²): {d["loss"]:.6f} → {d["loss_after"]:.6f}. '
                             f'{len(d["x"])} sample(s); charts show sample 1 unless labeled as a batch. '
                             f'Bias gradient for H1.{j+1}: {n.gb[0][j]:+.5f}. '
                             + (f'BN gradients γ: {n.ggamma[j]:+.5f}, β: {n.gbeta[j]:+.5f}. ' if n.bn else '')
                             + 'All controls replay one update from the same initial weights.')
        self.detail.refresh(layout=False)

    def draw_rl(self):
        s = self.stage.currentIndex()
        d = ddpg_snapshot(self.phase.value()/100, self.lr.value()/100, self.terminal.isChecked())
        self.snapshot = d
        notes = [
            'Sample eight recorded (state, action, reward, next state, termination) transitions. Stored behavior actions train the critic; they are not the actions the current actor must imitate.',
            'Feed next state s′ into the target actor. This slow copy predicts the next action a′; it receives no gradient from the TD target.',
            'Feed s′ and a′ into the target critic, then combine its estimate with observed reward. Termination removes the future term. Detach this target from differentiation.',
            'Feed recorded state s and RECORDED action a into the online critic. It outputs one predicted return Q, not joint torques.',
            'Seed the critic backward pass with 2(Q − y)/batch size. Gradients cross its output and hidden layers. The replay inputs and target y stay fixed.',
            'Apply the critic optimizer. Only online critic weights and biases change. Compare its prediction before and after against the same detached target.',
            'Now reuse replay states, but recompute actions with the online actor. These are current policy actions, different from the stored behavior actions.',
            'Pass the actor’s actions through the updated critic. Freeze critic PARAMETERS while differentiating Q with respect to its ACTION INPUT. Freezing parameters does not cut this path.',
            'The critic supplies two sensitivities: one for ankle action and one for knee action. Backpropagate −dQ/da through output tanh and every actor layer to minimize −mean Q.',
            'Apply the actor optimizer only. The action moves on the fixed critic landscape. This increases a learned estimate locally; it does not guarantee improved real walking.',
            'Soft-update both targets: target ← 0.95 target + 0.05 online. This is a parameter blend, not backpropagation. At deployment only the actor’s forward pass is needed.'
        ]
        self.caption.setText(f'<b>{s+1}/11 · {self.steps[s]}</b><br>{notes[s]}')
        ax = self.overview.ax
        ax.clear()
        ax.set_axis_off()
        ax.set(xlim=(-.6, 3.7), ylim=(-.65, 2.6))
        positions = [(0, 2), (1.5, 2), (3, 2), (0, .5), (1.5, .5), (3, .5)]
        statuses = ['read only', 'NO gradient', 'NO gradient',
                    'UPDATE' if s == 9 else 'gradient' if s == 8 else 'fixed',
                    'UPDATE' if s == 5 else 'gradient' if s == 4 else 'FROZEN' if s in (7, 8, 9) else 'fixed', 'detached y']
        labels = ['Replay batch\ns, a, r, s′', 'Target actor\ns′ → a′', 'Target critic\n(s′, a′) → Q′',
                  'Online actor\n6 → 4 → 3 → 2', 'Online critic\n(6 + 2) → 4 → 3 → 1', f'TD target\ny = {d["y"][0,0]:+.4f}']
        active = [0, 1, 2, 4, 4, 4, 3, 4, 3, 3, 1][s]
        for k, ((x, y), label) in enumerate(zip(positions, labels)):
            ax.text(x, y, label+'\n'+statuses[k], ha='center', va='center', color=theme.TEXT, fontsize=10,
                    bbox=dict(boxstyle='round,pad=.8', fc=theme.BG_RAISED, ec=theme.WARN if active == k else theme.BORDER, lw=2 if active == k else 1))
        def arrow(p, q, text, color=theme.CYAN):
            ax.annotate('', xy=q, xytext=p, arrowprops=dict(arrowstyle='->', color=color, lw=2))
            ax.text((p[0]+q[0])/2, (p[1]+q[1])/2+.12, text, ha='center', fontsize=8, color=theme.TEXT)
        arrow((.45, 2), (1.02, 2), 's′')
        arrow((2.02, 2), (2.58, 2), 'a′')
        arrow((3, 1.55), (3, .98), 'r + γQ′')
        if s in (7, 8, 9):
            arrow((1.02, .2), (.45, .2), '−dQ/da', theme.PINK)
        elif s >= 6:
            arrow((.45, .5), (1.0, .5), 'μ(s)')
        else:
            arrow((.35, 1.6), (1.25, .95), 's, replay a')
        if s <= 5:
            arrow((2.55, .5), (2.02, .5), 'compare')
        ax.text(1.5, -.48, 'CRITIC learns return estimates  •  ACTOR learns torque choices  •  TARGETS move slowly', ha='center', fontsize=9, color=theme.TEXT)
        self.overview.refresh(layout=False)
        self.detail.clear()
        a, b = self.detail.axes
        if s <= 2:
            vals = np.c_[d['x'][:, :2], d['replay_a'], d['reward']]
            a.imshow(vals, cmap='coolwarm', aspect='auto', vmin=-1, vmax=1)
            a.grid(False)
            a.set(xticks=range(5), xticklabels=['ank θ', 'knee θ', 'stored a₁', 'stored a₂', 'reward'], ylabel='Replay sample', title='Batch rows = recorded transitions (state excerpt)')
            self.bars(b, [d['reward'][0,0], .95*(not self.terminal.isChecked())*d['next_q'][0,0], d['y'][0,0]], ['reward', 'future', 'target y'], 'One TD target: reward + discounted future')
        elif s <= 5:
            idx = np.arange(8)
            a.plot(idx, d['y'][:, 0], 's--', color=theme.WARN, label='detached target')
            a.plot(idx, d['q'][:, 0], 'o-', color=theme.CYAN, label='before critic update')
            if s == 5:
                a.plot(idx, d['fitted_q'][:, 0], 'o-', color=theme.PINK, label='after critic update')
            a.set(xlabel='Replay sample', ylabel='Estimated return', title='Fit Q(s, recorded a) to y')
            self.detail.legend(a)
            self.bars(b, [np.linalg.norm(g) for g in d['critic'].gW], ['input → H1', 'H1 → H2', 'H2 → Q'], 'Critic: gradient size in EACH layer', '‖dL/dW‖')
        elif s <= 9:
            grid = np.linspace(-1, 1, 41)
            xx, yy = np.meshgrid(grid, grid)
            probe = deepcopy(d['fitted'])
            surface = probe.forward(np.c_[np.repeat(d['x'][:1], xx.size, axis=0), xx.ravel(), yy.ravel()]).reshape(xx.shape)
            a.contourf(xx*LIMITS[0], yy*LIMITS[1], surface, levels=14, cmap='viridis')
            a.contour(xx*LIMITS[0], yy*LIMITS[1], surface, levels=7, colors=theme.TEXT, linewidths=.4, alpha=.5)
            old, new = d['policy_a'][0]*LIMITS, d['new_a'][0]*LIMITS
            a.plot(*old, 'wo', label='current actor')
            a.plot(*(d['replay_a'][0]*LIMITS), 'x', color=theme.ORANGE, label='recorded action')
            if s == 9:
                a.plot(*new, '*', color=theme.PINK, markersize=12, label='after update')
                a.annotate('', xy=new, xytext=old, arrowprops=dict(arrowstyle='->', color=theme.PINK, lw=2))
            a.set(xlabel='Ankle torque (Nm)', ylabel='Knee torque (Nm)', title='Fixed learned Q landscape · brighter = larger Q')
            self.detail.legend(a, loc='upper left')
            if s == 7:
                self.bars(b, -d['da'][0]*8/LIMITS, ['ankle', 'knee'], 'Critic handoff: dQ / d torque', 'return / Nm')
            else:
                self.bars(b, [np.linalg.norm(g) for g in d['actor'].gW], ['state → H1', 'H1 → H2', 'H2 → action'], 'Actor: gradient crosses EVERY layer', '‖d(−mean Q)/dW‖')
        else:
            for ax, old, new, soft, name in ((a, d['target_actor'], d['updated'], d['soft'], 'actor'), (b, d['target_critic'], d['fitted'], d['soft_c'], 'critic')):
                deltas = [np.linalg.norm(n-o) for n, o in zip(new.W, old.W)]
                moved = [np.linalg.norm(n-o) for n, o in zip(soft.W, old.W)]
                idx = np.arange(3)
                ax.bar(idx-.15, deltas, width=.3, color=theme.CYAN, label='online − old target')
                ax.bar(idx+.15, moved, width=.3, color=theme.PINK, label='target moves 5%')
                ax.set(xticks=idx, xticklabels=['layer 1', 'layer 2', 'output'], ylabel='Weight distance', title=f'Target {name}: every layer follows slowly')
                self.detail.legend(ax)
        loss0, loss1 = np.mean((d['q']-d['y'])**2), np.mean((d['fitted_q']-d['y'])**2)
        self.readout.setText(f'<b>One reproducible SGD update:</b> critic MSE {loss0:.6f} → {loss1:.6f}; '
                             f'actor mean Q under the fixed updated critic {d["policy_q"].mean():+.6f} → {d["new_q"].mean():+.6f}.<br>'
                             'Critic actions are normalized torque coordinates; dQ/d torque divides by the joint torque scale. '
                             'SGD exposes the update arithmetic; the existing full DDPG trainer below uses Adam.')
        self.detail.refresh(layout=False)
