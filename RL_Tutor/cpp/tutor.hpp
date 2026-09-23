#pragma once
// C++17 teaching counterparts. GUI simulation remains in Python.
#include <algorithm>
#include <array>
#include <cmath>
#include <functional>
#include <limits>
#include <map>
#include <numeric>
#include <random>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace tutor {
using Vec = std::vector<double>;
using Matrix = std::vector<Vec>;
using Policy = std::array<int,16>;
using Values = std::array<double,16>;
using QTable = std::array<std::array<double,4>,16>;
using ProbPolicy = QTable;
using RNG = std::mt19937;
inline double uniform(RNG& rng) { return std::generate_canonical<double,53>(rng); }
inline int random_index(int n, RNG& rng) { return std::uniform_int_distribution<int>(0,n-1)(rng); }
template<class Row> int argmax(const Row& row) {
    return int(std::max_element(row.begin(),row.end())-row.begin());
}
struct Transition { double prob; int next_state; double reward; bool done; };
using Model = std::array<std::array<std::vector<Transition>,4>,16>;
inline bool terminal(int s) { return s==5 || s==7 || s==11 || s==12 || s==15; }
struct SlipModel {
    double intended=1.0/3, perp_cw=1.0/3, perp_ccw=1.0/3;
// BEGIN rlcore.frozen_lake.SlipModel.as_pairs
    std::vector<std::pair<double,int>> as_pairs(int a) const {
        std::vector<std::pair<double,int>> result;
        for (auto branch : {std::pair<double,int>{intended,a},
                            {perp_cw,(a+1)%4}, {perp_ccw,(a+3)%4}}) {
            if (branch.first > 0) result.push_back(branch);
        }
        return result;
    }
// END rlcore.frozen_lake.SlipModel.as_pairs
};
struct RewardScheme { double goal=1, hole=0, step=0; };
// BEGIN rlcore.frozen_lake.move
inline int move(int s, int action) {
    constexpr int dr[] = {0,1,0,-1}, dc[] = {-1,0,1,0};
    int row = std::clamp(s/4+dr[action],0,3);
    int col = std::clamp(s%4+dc[action],0,3);
    return row*4+col; // A wall leaves the agent in the same cell.
}
// END rlcore.frozen_lake.move
// BEGIN rlcore.frozen_lake.build_model
inline Model build_model(SlipModel slip={}, RewardScheme reward={}) {
    Model P;
    for (int s=0; s<16; ++s) {
        for (int a=0; a<4; ++a) {
            if (terminal(s)) {
                P[s][a].push_back({1.0,s,0.0,true});
                continue; // Absorbing terminal states have no future reward.
            }
            for (auto [prob,actual] : slip.as_pairs(a)) {
                int next = move(s,actual);
                double r = next==15 ? reward.goal : terminal(next) ? reward.hole : reward.step;
                P[s][a].push_back({prob,next,r,terminal(next)});
            }
        }
    }
    return P;
}
// END rlcore.frozen_lake.build_model
struct FrozenLake {
    SlipModel slip; RewardScheme rewards; RNG rng;
    int state=0, last_actual=0; bool done=true, last_bumped=false;
    FrozenLake(SlipModel sm={}, RewardScheme rs={}, unsigned seed=0): slip(sm),rewards(rs),rng(seed) {}
    int reset() { state=0; done=false; return state; }
// BEGIN rlcore.frozen_lake.FrozenLake.sample_actual_action
    int sample_actual_action(int a) {
        double roll=uniform(rng), cumulative=0;
        for (auto [prob,actual] : slip.as_pairs(a)) {
            cumulative += prob;
            if (roll < cumulative) return actual;
        }
        return a; // Floating-point roundoff guard.
    }
// END rlcore.frozen_lake.FrozenLake.sample_actual_action
// BEGIN rlcore.frozen_lake.FrozenLake.step
    std::tuple<int,double,bool> step(int a) {
        if (done) throw std::logic_error("call reset before stepping");
        last_actual = sample_actual_action(a);
        int next = move(state,last_actual);
        last_bumped = next==state;
        double r = next==15 ? rewards.goal : terminal(next) ? rewards.hole : rewards.step;
        state=next; done=terminal(next);
        return {state,r,done};
    }
// END rlcore.frozen_lake.FrozenLake.step
};
using Episode = std::vector<std::tuple<int,int,double>>;
// BEGIN rlcore.frozen_lake.run_episode
inline Episode run_episode(FrozenLake& env, const std::function<int(int)>& policy, int max_steps=200) {
    Episode trajectory;
    int s=env.reset();
    for (int t=0; t<max_steps; ++t) {
        int a=policy(s);
        auto [next,reward,done]=env.step(a);
        trajectory.emplace_back(s,a,reward);
        s=next;
        if (done) break;
    }
    return trajectory;
}
// END rlcore.frozen_lake.run_episode
// BEGIN rlcore.frozen_lake.q_from_V
inline double q_from_V(const Model& P, const Values& V, int s, int a, double gamma=.99) {
    double total=0;
    for (const auto& branch : P[s][a]) {
        double bootstrap = branch.done ? 0.0 : V[branch.next_state];
        total += branch.prob*(branch.reward+gamma*bootstrap);
    }
    return total;
}
// END rlcore.frozen_lake.q_from_V
// BEGIN rlcore.frozen_lake.V_from_Q
inline Values V_from_Q(const QTable& Q, const ProbPolicy& policy_probs) {
    Values V{};
    for (int s=0; s<16; ++s)
        for (int a=0; a<4; ++a) V[s]+=policy_probs[s][a]*Q[s][a];
    return V;
}
// END rlcore.frozen_lake.V_from_Q
// BEGIN rlcore.dp.policy_evaluation
inline Values policy_evaluation(const Model& P, const Policy& pi, double gamma=.99,
                                double tolerance=1e-10, int max_sweeps=10000) {
    Values V{};
    for (int sweep=0; sweep<max_sweeps; ++sweep) {
        Values previous=V; double delta=0;
        for (int s=0; s<16; ++s) {
            V[s]=q_from_V(P,previous,s,pi[s],gamma);
            delta=std::max(delta,std::abs(V[s]-previous[s]));
        }
        if (delta<tolerance) break;
    }
    return V;
}
// END rlcore.dp.policy_evaluation
// BEGIN rlcore.dp.policy_evaluation_stochastic
inline Values policy_evaluation_stochastic(const Model& P, const ProbPolicy& pi,
                                           double gamma=.99, double tolerance=1e-12,
                                           int max_sweeps=10000) {
    Values V{};
    for (int sweep=0; sweep<max_sweeps; ++sweep) {
        Values previous=V; double delta=0;
        for (int s=0; s<16; ++s) {
            V[s]=0;
            for (int a=0; a<4; ++a) V[s]+=pi[s][a]*q_from_V(P,previous,s,a,gamma);
            delta=std::max(delta,std::abs(V[s]-previous[s]));
        }
        if (delta<tolerance) break;
    }
    return V;
}
// END rlcore.dp.policy_evaluation_stochastic
// BEGIN rlcore.dp.policy_evaluation_exact
inline Values policy_evaluation_exact(const Model& P, const ProbPolicy& pi, double gamma=.99) {
    // Solve (I - gamma * P_pi) V = r_pi by pivoted elimination.
    std::array<std::array<double,17>,16> augmented{};
    for (int s=0; s<16; ++s) {
        augmented[s][s]=1;
        for (int a=0; a<4; ++a) for (const auto& t : P[s][a]) {
            double weight=pi[s][a]*t.prob;
            augmented[s][16]+=weight*t.reward;
            if (!t.done) augmented[s][t.next_state]-=gamma*weight;
        }
    }
    for (int col=0; col<16; ++col) {
        int pivot=col;
        for (int r=col+1; r<16; ++r)
            if (std::abs(augmented[r][col])>std::abs(augmented[pivot][col])) pivot=r;
        std::swap(augmented[col],augmented[pivot]);
        double divisor=augmented[col][col];
        if (std::abs(divisor)<1e-14) throw std::runtime_error("singular policy system");
        for (double& v : augmented[col]) v/=divisor;
        for (int r=0; r<16; ++r) if (r!=col) {
            double factor=augmented[r][col];
            for (int j=col; j<=16; ++j) augmented[r][j]-=factor*augmented[col][j];
        }
    }
    Values V{};
    for (int s=0; s<16; ++s) V[s]=augmented[s][16];
    return V;
}
// END rlcore.dp.policy_evaluation_exact
struct Improvement { Policy policy; bool stable; QTable Q; };
// BEGIN rlcore.dp.policy_improvement
inline Improvement policy_improvement(const Model& P, const Values& V, const Policy& old, double gamma=.99) {
    Improvement result{{},true,{}};
    for (int s=0; s<16; ++s) {
        for (int a=0; a<4; ++a) result.Q[s][a]=q_from_V(P,V,s,a,gamma);
        int best=argmax(result.Q[s]);
        result.policy[s]=best;
        // Tied actions are not a genuine improvement.
        if (result.Q[s][best]-result.Q[s][old[s]]>1e-12) result.stable=false;
    }
    return result;
}
// END rlcore.dp.policy_improvement
struct DPResult { Policy policy; Values V; int sweeps; };
// BEGIN rlcore.dp.policy_iteration
inline DPResult policy_iteration(const Model& P, double gamma=.99, double tolerance=1e-10, int max_rounds=200) {
    Policy pi{}; Values V{};
    for (int round=1; round<=max_rounds; ++round) {
        V=policy_evaluation(P,pi,gamma,tolerance);
        auto improved=policy_improvement(P,V,pi,gamma);
        pi=improved.policy;
        if (improved.stable) return {pi,V,round};
    }
    return {pi,V,max_rounds};
}
// END rlcore.dp.policy_iteration
// BEGIN rlcore.dp.value_iteration
inline DPResult value_iteration(const Model& P, double gamma=.99, double tolerance=1e-10, int max_sweeps=10000) {
    Values V{}; int sweep=0;
    for (; sweep<max_sweeps; ++sweep) {
        Values previous=V; double delta=0;
        for (int s=0; s<16; ++s) {
            std::array<double,4> q{};
            for (int a=0; a<4; ++a) q[a]=q_from_V(P,previous,s,a,gamma);
            V[s]=q[argmax(q)];
            delta=std::max(delta,std::abs(V[s]-previous[s]));
        }
        if (delta<tolerance) { ++sweep; break; }
    }
    return {policy_improvement(P,V,Policy{},gamma).policy,V,sweep};
}
// END rlcore.dp.value_iteration
// BEGIN rlcore.dp.value_iteration_operator
inline std::pair<Values,std::vector<Values>> value_iteration_operator(
        const Model& P, double gamma=.99, std::string op="max", double tolerance=1e-12, int max_sweeps=400) {
    Values V{}; std::vector<Values> history{V};
    for (int sweep=0; sweep<max_sweeps; ++sweep) {
        Values previous=V; double delta=0;
        for (int s=0; s<16; ++s) {
            std::array<double,4> q{};
            for (int a=0; a<4; ++a) q[a]=q_from_V(P,previous,s,a,gamma);
            if (op=="mean") V[s]=std::accumulate(q.begin(),q.end(),0.0)/4;
            else if (op=="min") V[s]=*std::min_element(q.begin(),q.end());
            else V[s]=q[argmax(q)];
            delta=std::max(delta,std::abs(V[s]-previous[s]));
        }
        history.push_back(V);
        if (delta<tolerance) break;
    }
    return {V,history};
}
// END rlcore.dp.value_iteration_operator
// BEGIN rlcore.dp.q_value_iteration_history
inline std::pair<QTable,std::vector<QTable>> q_value_iteration_history(
        const Model& P, double gamma=.99, double tolerance=1e-12, int max_sweeps=400) {
    QTable Q{}; std::vector<QTable> history{Q};
    for (int sweep=0; sweep<max_sweeps; ++sweep) {
        QTable previous=Q; double delta=0;
        for (int s=0; s<16; ++s) for (int a=0; a<4; ++a) {
            double total=0;
            for (const auto& t : P[s][a]) {
                double boot=t.done ? 0 : previous[t.next_state][argmax(previous[t.next_state])];
                total+=t.prob*(t.reward+gamma*boot);
            }
            delta=std::max(delta,std::abs(total-Q[s][a]));
            Q[s][a]=total;
        }
        history.push_back(Q);
        if (delta<tolerance) break;
    }
    return {Q,history};
}
// END rlcore.dp.q_value_iteration_history
// BEGIN rlcore.dp.q_value_iteration
inline std::tuple<Policy,QTable,int> q_value_iteration(const Model& P, double gamma=.99,
                                                       double tolerance=1e-10, int max_sweeps=10000) {
    auto [Q,history]=q_value_iteration_history(P,gamma,tolerance,max_sweeps);
    Policy pi{};
    for (int s=0; s<16; ++s) pi[s]=argmax(Q[s]);
    return {pi,Q,int(history.size())-1};
}
// END rlcore.dp.q_value_iteration
// BEGIN rlcore.dp.evaluate_policy_empirically
inline std::map<std::string,double> evaluate_policy_empirically(
        FrozenLake& env, const Policy& pi, int episodes=2000, int max_steps=200) {
    double wins=0, total_return=0, steps=0;
    for (int ep=0; ep<episodes; ++ep) {
        auto trajectory=run_episode(env,[&](int s){return pi[s];},max_steps);
        wins+=env.state==15; steps+=trajectory.size();
        for (const auto& transition:trajectory) total_return+=std::get<2>(transition);
    }
    return {{"success_rate",wins/episodes},{"mean_return",total_return/episodes},{"mean_length",steps/episodes}};
}
// END rlcore.dp.evaluate_policy_empirically
// BEGIN rlcore.mc.epsilon_greedy
inline int epsilon_greedy(const QTable& Q, int s, double eps, RNG& rng) {
    if (uniform(rng)<eps) return random_index(4,rng);
    double best=Q[s][argmax(Q[s])]; std::vector<int> ties;
    for (int a=0; a<4; ++a) if (Q[s][a]>=best-1e-12) ties.push_back(a);
    return ties[random_index(int(ties.size()),rng)];
}
// END rlcore.mc.epsilon_greedy
// BEGIN rlcore.mc.mc_prediction
inline std::pair<Values,std::array<int,16>> mc_prediction(
        FrozenLake& env, const std::function<int(int)>& policy, double gamma=.99,
        int episodes=5000, bool first_visit=true, int max_steps=200) {
    Values V{}; std::array<int,16> counts{};
    for (int ep=0; ep<episodes; ++ep) {
        auto trajectory=run_episode(env,policy,max_steps);
        std::map<int,int> first;
        for (int t=0; t<int(trajectory.size()); ++t) first.emplace(std::get<0>(trajectory[t]),t);
        double G=0;
        for (int t=int(trajectory.size())-1; t>=0; --t) {
            auto [s,a,r]=trajectory[t];
            G=gamma*G+r;
            if (first_visit && first[s]!=t) continue;
            ++counts[s];
            V[s]+=(G-V[s])/counts[s];
        }
    }
    return {V,counts};
}
// END rlcore.mc.mc_prediction
struct MCResult { QTable Q{}; Policy policy{}; double success_rate=0; };
// BEGIN rlcore.mc.mc_control
inline MCResult mc_control(FrozenLake& env, double gamma=.99, int episodes=20000,
        double eps=1, double eps_min=.05, double eps_decay=.9995,
        double alpha=.5, double alpha_min=.01, double alpha_decay=.9995,
        bool first_visit=true, int max_steps=200, unsigned seed=0) {
    RNG rng(seed); MCResult result; int wins=0;
    for (int ep=0; ep<episodes; ++ep) {
        auto trajectory=run_episode(env,[&](int s){return epsilon_greedy(result.Q,s,eps,rng);},max_steps);
        wins+=env.state==15;
        std::map<std::pair<int,int>,int> first;
        for (int t=0; t<int(trajectory.size()); ++t) {
            auto [s,a,r]=trajectory[t]; first.emplace(std::make_pair(s,a),t);
        }
        double G=0;
        for (int t=int(trajectory.size())-1; t>=0; --t) {
            auto [s,a,r]=trajectory[t]; G=gamma*G+r;
            if (first_visit && first[{s,a}]!=t) continue;
            result.Q[s][a]+=alpha*(G-result.Q[s][a]);
        }
        eps=std::max(eps_min,eps*eps_decay);
        alpha=std::max(alpha_min,alpha*alpha_decay);
    }
    for (int s=0; s<16; ++s) result.policy[s]=argmax(result.Q[s]);
    result.success_rate=double(wins)/episodes;
    return result; // GUI-only per-episode logging omitted from this teaching API.
}
// END rlcore.mc.mc_control
// BEGIN rlcore.mc.estimate_pi
inline Vec estimate_pi(int n=5000, unsigned seed=0) {
    RNG rng(seed); Vec estimates; int inside=0;
    for (int i=1; i<=n; ++i) {
        double x=uniform(rng), y=uniform(rng);
        inside+=x*x+y*y<=1;
        estimates.push_back(4.0*inside/i);
    }
    return estimates;
}
// END rlcore.mc.estimate_pi
// BEGIN rlcore.mc.dice_convergence
inline Vec dice_convergence(int n=5000, unsigned seed=0) {
    RNG rng(seed); Vec means; double total=0;
    for (int i=1; i<=n; ++i) {
        total+=1+random_index(6,rng);
        means.push_back(total/i);
    }
    return means;
}
// END rlcore.mc.dice_convergence
// BEGIN ctrlcore.impedance.impedance_torque
inline double impedance_torque(double theta, double omega,
        double theta_d, double omega_d, double k, double b, double tau_ff=0.0) {
    // Virtual spring and damper: command a torque-displacement relationship.
    // With tau_ff = 0 this has the same algebra as PD position feedback.
    return -k*(theta-theta_d) - b*(omega-omega_d) + tau_ff;
}
// END ctrlcore.impedance.impedance_torque
struct VirtualModel {
    double m_v=2, b_v=6, k_v=0, x=0, v=0;
// BEGIN ctrlcore.impedance.VirtualModel.step
    std::pair<double,double> step(double f_ext, double dt) {
        // Force -> virtual acceleration -> velocity -> position reference.
        double acceleration=(f_ext-b_v*v-k_v*x)/m_v;
        v+=acceleration*dt;
        x+=v*dt;
        return {x,v}; // Passed to the inner motion controller.
    }
// END ctrlcore.impedance.VirtualModel.step
};
struct PID {
    double kp=40,ki=0,kd=3,tau_d=0,out_min=-12,out_max=12,kt=1;
    double integral=0,prev_e=0,prev_y=0,d_state=0;
    bool first=true,d_on_measurement=true;
    std::string anti_windup="clamp";
// BEGIN ctrlcore.realtime.PID.step
    std::pair<double,std::array<double,3>> step(double setpoint, double measurement, double dt) {
        dt=std::max(dt,1e-9); // Use measured elapsed time.
        double e=setpoint-measurement, p=kp*e, raw_d=0;
        if (!first) raw_d=d_on_measurement ? -(measurement-prev_y)/dt : (e-prev_e)/dt;
        first=false;
        double d=kd*raw_d;
        if (tau_d>0) { d_state+=dt/(tau_d+dt)*(raw_d-d_state); d=kd*d_state; }
        double candidate=integral+ki*e*dt;
        double unsaturated=p+candidate+d;
        double output=std::clamp(unsaturated,out_min,out_max);
        if (anti_windup=="none") integral=candidate;
        else if (anti_windup=="clamp") {
            if (!(unsaturated!=output && (e>0)==(unsaturated>0))) integral=candidate;
        } else if (anti_windup=="back_calc") integral=candidate+kt*(output-unsaturated)*dt;
        else throw std::invalid_argument("unknown anti-windup mode");
        prev_e=e; prev_y=measurement;
        return {std::clamp(p+integral+d,out_min,out_max),{p,integral,d}};
    }
// END ctrlcore.realtime.PID.step
};
struct PffLoop {
    double k_f=.0002,delay=.04,f_max=3000,gate_start=.1,gate_end=.6,a_max=1;
    Vec history;
// BEGIN ctrlcore.neuro.PffLoop.step
    std::pair<double,double> step(double emg, double length, double velocity,
                                 double phase, double dt, bool gated=true) {
        int n=int(std::nearbyint(delay/dt));
        double delayed=history.empty() ? 0 : n<=0 ? history.back() :
            int(history.size())>n ? history[history.size()-1-n] : 0;
        bool enabled=!gated || (gate_start<=phase && phase<=gate_end);
        double activation=std::clamp(emg+(enabled ? k_f*delayed : 0),0.0,a_max);
        double v=std::max(-1.0,velocity);
        double fl=std::exp(-std::pow((length-1)/.45,2));
        double fv=v<=0 ? (1+v)/(1-v/.25) : std::min(1.8,1.8-.8*(1-v)/(1+7.56*v));
        double force=activation*f_max*fl*fv;
        history.push_back(force);
        return {force,activation};
    }
// END ctrlcore.neuro.PffLoop.step
};
} // namespace tutor
