#include "cpp/examples.hpp"
#include <cassert>
#include <iomanip>
using namespace tutor;
int main() {
    assert(std::abs(impedance_torque(.3,.2,.1,0,100,5,2)+19)<1e-12);
    VirtualModel vm; auto [x,v]=vm.step(10,.01);
    assert(std::abs(v-.05)<1e-12 && std::abs(x-.0005)<1e-12);
    PID pid; for(int i=0;i<100;++i) assert(pid.step(100,0,.001).first==12);
    assert(pid.integral==0);
    auto P=build_model({.8,.1,.1},{1,-1,-.04});
    auto result=value_iteration(P,.99);
    ProbPolicy probabilities{};
    for(int s=0;s<16;++s) probabilities[s][result.policy[s]]=1;
    auto exact=policy_evaluation_exact(P,probabilities,.99);
    for(int s=0;s<16;++s) assert(std::abs(result.V[s]-exact[s])<1e-7);
    QTable Q{}; Q[0]={1,2,3,4}; probabilities[0]={.25,.25,.25,.25};
    assert(V_from_Q(Q,probabilities)[0]==2.5);
    auto returns=discounted_returns({{0,0,1},{1,0,2}},.5);
    assert(returns[0]==2 && returns[1]==2);
    RNG rng(3); Dense layer(2,1,"linear",rng);
    layer.W={{2},{3}}; layer.b={1};
    assert(layer.forward({{4,5}})[0][0]==24);
    auto dx=layer.backward({{2}});
    assert(dx[0][0]==4 && dx[0][1]==6 && layer.gW[0][0]==8 && layer.gb[0]==2);
    layer.adam(.01); assert(layer.W[0][0]<2);
    ReplayBuffer buffer(2);
    for(int i=0;i<3;++i) buffer.push({double(i)},{0},0,{0},true);
    assert(buffer.items.size()==2 && buffer.items[0].s[0]==2);
    DDPGConfig config; config.dim_s=1; config.dim_a=1; config.hidden=4; config.batch=8;
    DDPG agent(config);
    for(int i=0;i<210;++i) agent.buf.push({.2},{.1},-.3,{.4},false);
    agent.train_step(); assert(std::isfinite(agent.critic_losses.back()));
    actor_gradient_step(agent,{{.2},{.4}});
    auto gaussian=[](const Vec&){return std::pair<double,double>{0,1};};
    auto value=[](const Vec&){return 0.;};
    assert(std::isfinite(std::get<1>(ppo_action(gaussian,value,{0},rng))));
    FrozenLake env({1,0,0},{1,-1,-.04});
    auto deterministic=value_iteration(build_model({1,0,0},{1,-1,-.04}),.99);
    auto metrics=evaluate_policy_empirically(env,deterministic.policy,10);
    assert(metrics.at("success_rate")==1 && metrics.at("mean_length")==6);
    assert(std::abs(metrics.at("mean_return")-.8)<1e-12);
    std::cout<<std::setprecision(17);
    for(double val:result.V) std::cout<<val<<' ';
}
