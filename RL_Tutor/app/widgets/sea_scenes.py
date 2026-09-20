"""Mechanism movies with exact relative amplitudes and explicit experiment ports."""
import math

from ctrlcore.sea_teaching import SeaModel
from .. import theme


class SeaScenes:
    def draw_sea_motion(self):
        model = SeaModel(k=self.d.get('k', 300.))
        mode = self.d.get('mode', 'load_slow')
        drive = 'motor' if mode.startswith('motor') else 'load'
        if mode == 'resonance':
            omega = model.wr
            xm, xl = 1+0j, -model.jm/model.jl+0j
            experiment = 'Free relative mode · no continuing input torque'
        elif mode.startswith('imposed'):
            omega = model.wn * {'imposed_slow': .2, 'imposed_near': .95, 'imposed_fast': 3}[mode]
            xm, xl = model.imposed_motor(omega, self.d.get('damping', 0.))
            experiment = 'Impose θ_m(t) · external load torque = 0 · measure θ_L'
        else:
            omega = {'load_slow': .2*min(model.wn,model.wa), 'load_fast': 4*model.wr,
                     'load_anti': model.wa, 'motor_anti': model.wn,
                     'motor_slow': .2*min(model.wn,model.wa), 'motor_fast': 3*model.wr,
                     'load_damped': model.wa}.get(mode, .5*model.wr)
            xm, xl = model.harmonic(omega, drive, self.d.get('damping', .6 if mode == 'load_damped' else 0.))
            experiment = f'Apply sinusoidal τ_{"m" if drive == "motor" else "L"} · other applied torque = 0'
        phase = 2*math.pi*self.progress
        wave = complex(math.cos(phase), math.sin(phase))
        scale = 42/max(abs(xm),abs(xl),1e-12)
        motor, load = (xm*wave).real*scale, (xl*wave).real*scale
        mx, lx = 245+motor, 650+load
        self.text(15, 2, 870, 30, experiment, theme.TEXT, 12)
        self.text(20, 32, 860, 27, f'ω = {omega:.2f} rad/s   |   f = {omega/(2*math.pi):.2f} Hz   |   playback slowed', theme.CYAN, 10)
        self.line(245, 65, 245, 168, theme.BORDER)
        self.line(650, 65, 650, 168, theme.BORDER)
        self.box(mx-67, 83, 134, 69, 'Motor\nJ_m = 0.04', True)
        self.box(lx-67, 83, 134, 69, 'Load\nJ_L = 0.06', True, theme.WARN)
        self.spring(mx+67,117,lx-67)
        self.text(366,68,170,24,f'k = {model.k:g} N·m/rad',theme.TEXT_DIM,10)
        if mode != 'resonance':
            x = mx if drive=='motor' or mode.startswith('imposed') else lx
            self.arrow(x,180,x+45*math.cos(phase),180,theme.VIOLET)
        ratio = abs(xm)/max(abs(xl),1e-15)
        stationary = ('Motor angle = 0; load still moves' if abs(xm)<1e-10 else
                      'Load angle = 0; motor still moves' if abs(xl)<1e-10 else
                      f'Angle amplitude ratio |θ_m| / |θ_L| = {ratio:.3g}')
        self.text(110, 182, 680, 25, stationary, theme.TEXT, 11)
        self.note(self.d.get('note', 'Horizontal offsets represent angles; motion magnified with model-based relative amplitude and phase.'))

    def draw_sea_frequency(self):
        model = SeaModel(k=self.d.get('k',300.))
        definitions = [('ω_n', model.wn, 'motor anti-resonance /\nimposed-motion resonance'),
                       ('ω_a', model.wa, 'load anti-resonance'),
                       ('ω_r', model.wr, 'free two-inertia mode')]
        for i,(symbol,w,label) in enumerate(definitions):
            x=25+i*295
            self.box(x,60,265,118,f'{symbol} = {w:.2f} rad/s\nf = {w/(2*math.pi):.2f} Hz\n{label}',i==self.d.get('active',0))
            self.dot(x+132+28*math.cos(2*math.pi*self.progress),40,5,theme.WARN)
        self.text(20,3,860,28,'One example: J_m = 0.04, J_L = 0.06 kg·m²; k = '+str(model.k)+' N·m/rad',theme.TEXT_DIM,11)
        self.note(self.d.get('note','Same frequency: ω in rad/s = 2π × f in Hz. Different transfer functions can give it different roles.'))

    def draw_sea_balance(self):
        # At a driving-point antiresonance the driven body is stationary:
        # spring torque balances its applied torque, while the other body moves.
        motor = self.d.get('drive','load')=='motor'
        a=65*math.cos(2*math.pi*self.progress)
        self.box(345,68,210,86,('Motor' if motor else 'Load')+' stays still',True)
        self.arrow(450-a,46,450,46,theme.WARN)
        self.arrow(450+a,179,450,179,theme.CYAN)
        self.text(30,59,260,90,'Applied torque\nτ = cos(ωt)',theme.WARN)
        self.text(610,59,270,100,'Spring reaction\n−τ = −cos(ωt)',theme.CYAN)
        self.note('Equal and opposite torques → zero acceleration at this measured port; the other inertia oscillates.')
