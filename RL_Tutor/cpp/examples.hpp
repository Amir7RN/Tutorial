#pragma once
#include "learning.hpp"
#include <iostream>
namespace tutor {
// BEGIN example.actor_gradient
inline void actor_gradient_step(DDPG& agent,const Matrix& s) {
    const auto& c=agent.cfg;
    auto a_pi=scaled(agent.actor.forward(s),c.a_max);
    auto q_pi=agent.critic.forward(concatenate(s,a_pi));
    auto dx=agent.critic.backward(Matrix(s.size(),Vec(1,1.0/s.size())));
    auto dq_da=action_columns(dx,c.dim_s); // Keep the action gradient only.
    agent.actor.backward(scaled(dq_da,-c.a_max)); // Minus = ascent on Q.
    agent.actor.adam(c.lr_actor); // Only now do the actor weights change.
}
// END example.actor_gradient
// BEGIN example.four_networks
inline void four_networks(int dim_s,int dim_a,int h,RNG& rng) {
    MLP actor({dim_s,h,h,dim_a},"tanh",rng);
    MLP critic({dim_s+dim_a,h,h,1},"linear",rng);
    MLP actor_t({dim_s,h,h,dim_a},"tanh",rng);
    MLP critic_t({dim_s+dim_a,h,h,1},"linear",rng);
    actor_t.copy_from(actor,1.0); // Start identical.
    critic_t.copy_from(critic,1.0);
}
// END example.four_networks
// BEGIN example.action_comparison
inline int tabular_action(const QTable& Q,int s,double eps,RNG& rng) {
    if (uniform(rng)<eps) return random_index(4,rng);
    return argmax(Q[s]); // Compare entries in a stored row.
}
inline int dqn_action(MLP& net,const Vec& s,int actions,double eps,RNG& rng) {
    if (uniform(rng)<eps) return random_index(actions,rng);
    return argmax(net.forward({s})[0]); // Compare network outputs.
}
inline Vec ddpg_action(DDPG& agent,const Vec& s,double noise) {
    return agent.act(s,noise); // Trained actor plus clipped exploration noise.
}
// Scalar Gaussian PPO example; policy(s) returns {mean, standard deviation}.
template<class GaussianPolicy,class ValueFunction>
std::tuple<double,double,double> ppo_action(
        GaussianPolicy& policy,ValueFunction& value,const Vec& s,RNG& rng) {
    auto [mu,sigma]=policy(s);
    double a=std::normal_distribution<double>(mu,sigma)(rng);
    double log_prob=-.5*std::pow((a-mu)/sigma,2)-std::log(sigma)
                    -.5*std::log(2*std::acos(-1.0));
    return {a,log_prob,value(s)}; // Keep the action's probability for PPO's ratio.
}
// END example.action_comparison
// BEGIN example.training_loop
template<class Agent,class Environment>
void training_loop(Agent& agent,Environment& env,int total_steps) {
    auto s=env.reset();
    for (int t=0;t<total_steps;++t) {
        auto a=agent.act(s);
        auto [s2,reward,done,info]=env.step(a);
        agent.store(s,a,reward,s2,done);
        agent.train_step();
        s=done ? env.reset() : s2;
    }
}
// END example.training_loop
// BEGIN example.evaluation_sweep
inline double evaluation_sweep(const Model& P,Values& V,const Policy& pi,double gamma) {
    Values previous=V; double delta=0;
    for (int s=0;s<16;++s) {
        double next=q_from_V(P,previous,s,pi[s],gamma); // FOLLOW the policy.
        delta=std::max(delta,std::abs(next-V[s]));
        V[s]=next;
    }
    return delta;
}
// END example.evaluation_sweep
// BEGIN example.optimality_sweep
inline double optimality_sweep(const Model& P,Values& V,double gamma) {
    Values previous=V; double delta=0;
    for (int s=0;s<16;++s) {
        std::array<double,4> q{};
        for (int a=0;a<4;++a) q[a]=q_from_V(P,previous,s,a,gamma);
        double next=q[argmax(q)]; // Choose the BEST action.
        delta=std::max(delta,std::abs(next-V[s])); V[s]=next;
    }
    return delta;
}
// END example.optimality_sweep
// BEGIN example.model_based_interface
inline DPResult model_based_solution(const Model& P,double gamma,double tolerance) {
    // P[s][a] contains all possible outcomes and their probabilities.
    return value_iteration(P,gamma,tolerance);
}
// END example.model_based_interface
// BEGIN example.model_free_interface
inline MCResult model_free_solution(FrozenLake& env,double gamma,int episodes) {
    // Only reset() and step(action) are used to obtain experience.
    return mc_control(env,gamma,episodes);
}
// END example.model_free_interface
// BEGIN example.returns
inline Vec discounted_returns(const Episode& trajectory,double gamma) {
    Vec returns(trajectory.size()); double G=0;
    for (int t=int(trajectory.size())-1;t>=0;--t) {
        auto [state,action,reward]=trajectory[t];
        G=gamma*G+reward;
        returns[t]=G; // G is now the return from time t.
    }
    return returns;
}
// END example.returns
// BEGIN example.console_demo
inline void console_demo() {
    SlipModel slip{.8,.1,.1}; RewardScheme reward{1,-1,-.04};
    auto P=build_model(slip,reward);
    auto dp=value_iteration(P,.99);
    std::cout << "DP sweeps: " << dp.sweeps << ", V(start): " << dp.V[0] << '\n';
    FrozenLake env(slip,reward,0);
    auto mc=mc_control(env,.99,30000);
    std::cout << "MC success rate: " << mc.success_rate << '\n';
    auto V_mc=policy_evaluation(P,mc.policy,.99);
    std::cout << "Model-evaluated MC policy: " << V_mc[0] << '\n';
}
// END example.console_demo
} // namespace tutor
