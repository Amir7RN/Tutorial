#pragma once
#include "tutor.hpp"
namespace tutor {
struct Bandit {
    Vec truth; RNG rng; int best;
    Bandit(int k=10,unsigned seed=0):truth(k),rng(seed) {
        std::normal_distribution<double> normal;
        for (double& q:truth) q=normal(rng);
        best=argmax(truth);
    }
    double pull(int a) { return std::normal_distribution<double>(truth[a],1)(rng); }
};
struct BanditResult { Vec Q,rewards,optimal,regret; std::vector<int> N; Matrix bonuses; };
// BEGIN rlcore.bandit.epsilon_greedy_run
inline BanditResult epsilon_greedy_run(Bandit& bandit,int steps=1000,double eps=.1,
                                      unsigned seed=1,double optimistic_init=0) {
    int k=int(bandit.truth.size()); RNG rng(seed);
    BanditResult out; out.Q=Vec(k,optimistic_init); out.N.resize(k); double regret=0;
    for (int t=1; t<=steps; ++t) {
        int a;
        if (uniform(rng)<eps) a=random_index(k,rng);
        else {
            double best=out.Q[argmax(out.Q)]; std::vector<int> ties;
            for (int j=0; j<k; ++j) if (out.Q[j]>=best-1e-12) ties.push_back(j);
            a=ties[random_index(int(ties.size()),rng)];
        }
        double reward=bandit.pull(a);
        ++out.N[a]; out.Q[a]+=(reward-out.Q[a])/out.N[a];
        regret+=bandit.truth[bandit.best]-bandit.truth[a];
        out.rewards.push_back(reward); out.optimal.push_back(a==bandit.best); out.regret.push_back(regret);
    }
    return out;
}
// END rlcore.bandit.epsilon_greedy_run
// BEGIN rlcore.bandit.ucb_run
inline BanditResult ucb_run(Bandit& bandit,int steps=1000,double c=2) {
    int k=int(bandit.truth.size()); BanditResult out;
    out.Q.resize(k); out.N.resize(k); double regret=0;
    for (int t=1; t<=steps; ++t) {
        Vec bonus(k),score(k);
        for (int a=0; a<k; ++a) {
            bonus[a]=out.N[a]==0 ? std::numeric_limits<double>::infinity() : c*std::sqrt(std::log(t)/out.N[a]);
            score[a]=out.Q[a]+bonus[a];
        }
        int a=argmax(score); // Untried arms have infinite bonus; first tie wins.
        double reward=bandit.pull(a);
        ++out.N[a]; out.Q[a]+=(reward-out.Q[a])/out.N[a];
        regret+=bandit.truth[bandit.best]-bandit.truth[a];
        out.rewards.push_back(reward); out.optimal.push_back(a==bandit.best);
        out.regret.push_back(regret); out.bonuses.push_back(bonus);
    }
    return out;
}
// END rlcore.bandit.ucb_run
// BEGIN rlcore.bandit.compare
inline std::map<std::string,Matrix> compare(int steps=1000,int runs=200,
                                         Vec epsilons={0,.01,.1},double c=2,int k=10) {
    std::map<std::string,Matrix> result;
    for (int strategy=0; strategy<=int(epsilons.size()); ++strategy) {
        Matrix averages(2,Vec(steps));
        bool ucb=strategy==int(epsilons.size());
        for (int run=0; run<runs; ++run) {
            Bandit bandit(k,1000+run);
            auto trace=ucb ? ucb_run(bandit,steps,c) : epsilon_greedy_run(bandit,steps,epsilons[strategy],5000+run);
            for (int t=0; t<steps; ++t) {
                averages[0][t]+=trace.rewards[t]/runs;
                averages[1][t]+=100*trace.optimal[t]/runs;
            }
        }
        result[ucb ? "UCB" : "epsilon="+std::to_string(epsilons[strategy])]=averages;
    }
    return result; // Each value contains mean reward and percent optimal by step.
}
// END rlcore.bandit.compare
inline Matrix scaled(Matrix a,double scale) { for (auto& row:a) for (double& x:row) x*=scale; return a; }
inline Matrix concatenate(Matrix s,const Matrix& a) {
    for (std::size_t i=0;i<s.size();++i) s[i].insert(s[i].end(),a[i].begin(),a[i].end());
    return s;
}
inline Matrix action_columns(const Matrix& dx,int dim_s) {
    Matrix result; for (const auto& row:dx) result.emplace_back(row.begin()+dim_s,row.end()); return result;
}
struct Dense {
    Matrix W,gW,mW,vW,cached_x,z; Vec b,gb,mb,vb; std::string activation; int tick=0;
// BEGIN rlcore.deeprl.Dense.__init__
    Dense(int inputs,int outputs,std::string act,RNG& rng,double scale=-1):
        W(inputs,Vec(outputs)),gW(W),mW(W),vW(W),b(outputs),gb(outputs),mb(outputs),vb(outputs),activation(act) {
        double bound=scale<0 ? std::sqrt(1.0/inputs) : scale;
        std::uniform_real_distribution<double> distribution(-bound,bound);
        for (auto& row:W) for (double& weight:row) weight=distribution(rng);
        // Biases, gradients and Adam moments begin at zero.
    }
// END rlcore.deeprl.Dense.__init__
// BEGIN rlcore.deeprl.Dense.forward
    Matrix forward(const Matrix& x) {
        cached_x=x; z=Matrix(x.size(),b); Matrix result=z;
        for (std::size_t n=0;n<x.size();++n) for (std::size_t j=0;j<b.size();++j) {
            for (std::size_t i=0;i<W.size();++i) z[n][j]+=x[n][i]*W[i][j];
            result[n][j]=activation=="tanh" ? std::tanh(z[n][j]) :
                         activation=="relu" ? std::max(0.0,z[n][j]) : z[n][j];
        }
        return result; // Batched y = activation(xW + b).
    }
// END rlcore.deeprl.Dense.forward
// BEGIN rlcore.deeprl.Dense.backward
    Matrix backward(const Matrix& dout) {
        Matrix dx(dout.size(),Vec(W.size()));
        gW=Matrix(W.size(),Vec(b.size())); gb=Vec(b.size());
        double batch=double(std::max(std::size_t(1),dout.size()));
        for (std::size_t n=0;n<dout.size();++n) for (std::size_t j=0;j<b.size();++j) {
            double derivative=activation=="tanh" ? 1-std::pow(std::tanh(z[n][j]),2) :
                              activation=="relu" ? double(z[n][j]>0) : 1;
            double dz=dout[n][j]*derivative;
            gb[j]+=dz/batch;
            for (std::size_t i=0;i<W.size();++i) {
                gW[i][j]+=cached_x[n][i]*dz/batch;
                dx[n][i]+=dz*W[i][j];
            }
        }
        return dx; // Gradient with respect to this layer's input.
    }
// END rlcore.deeprl.Dense.backward
// BEGIN rlcore.deeprl.Dense.adam
    void adam(double lr,double beta1=.9,double beta2=.999,double eps=1e-8) {
        ++tick;
        auto update=[&](double& p,double g,double& m,double& v) {
            m=beta1*m+(1-beta1)*g;
            v=beta2*v+(1-beta2)*g*g;
            double mhat=m/(1-std::pow(beta1,tick));
            double vhat=v/(1-std::pow(beta2,tick));
            p-=lr*mhat/(std::sqrt(vhat)+eps);
        };
        for (std::size_t i=0;i<W.size();++i) for (std::size_t j=0;j<b.size();++j)
            update(W[i][j],gW[i][j],mW[i][j],vW[i][j]);
        for (std::size_t j=0;j<b.size();++j) update(b[j],gb[j],mb[j],vb[j]);
    }
// END rlcore.deeprl.Dense.adam
    void copy_from(const Dense& other,double tau=1) {
        for (std::size_t i=0;i<W.size();++i) for (std::size_t j=0;j<b.size();++j) W[i][j]+=tau*(other.W[i][j]-W[i][j]);
        for (std::size_t j=0;j<b.size();++j) b[j]+=tau*(other.b[j]-b[j]);
    }
};
struct MLP {
    std::vector<Dense> layers;
    MLP(std::vector<int> sizes,std::string out_act,RNG& rng) {
        for (std::size_t i=1;i<sizes.size();++i) {
            bool last=i+1==sizes.size();
            layers.emplace_back(sizes[i-1],sizes[i],last ? out_act : "tanh",rng,last ? .003 : -1);
        }
    }
    Matrix forward(Matrix x) { for (auto& layer:layers) x=layer.forward(x); return x; }
    Matrix backward(Matrix grad) { for (auto it=layers.rbegin();it!=layers.rend();++it) grad=it->backward(grad); return grad; }
    void adam(double lr) { for (auto& layer:layers) layer.adam(lr); }
    void copy_from(const MLP& other,double tau=1) { for (std::size_t i=0;i<layers.size();++i) layers[i].copy_from(other.layers[i],tau); }
};
struct Experience { Vec s,a; double r; Vec s2; bool done; };
// BEGIN rlcore.deeprl.ReplayBuffer
struct ReplayBuffer {
    std::vector<Experience> items; std::size_t capacity,index=0;
    explicit ReplayBuffer(std::size_t cap):capacity(cap) {
        if (!cap) throw std::invalid_argument("buffer capacity must be positive");
    }
// BEGIN rlcore.deeprl.ReplayBuffer.push
    void push(const Vec& s,const Vec& a,double reward,const Vec& s2,bool done) {
        Experience transition{s,a,reward,s2,done};
        if (items.size()<capacity) items.push_back(transition);
        else items[index]=transition;
        index=(index+1)%capacity; // Circular overwrite after the buffer fills.
    }
// END rlcore.deeprl.ReplayBuffer.push
    std::vector<Experience> sample(int count,RNG& rng) const {
        if (items.empty()) throw std::logic_error("empty replay buffer");
        std::vector<Experience> batch;
        for (int i=0;i<count;++i) batch.push_back(items[random_index(int(items.size()),rng)]);
        return batch; // Uniform sampling with replacement, matching the lesson.
    }
};
// END rlcore.deeprl.ReplayBuffer
struct DDPGConfig {
    int dim_s=1,dim_a=1,hidden=64,batch=64,capacity=20000;
    double a_max=1,gamma=.95,tau=.01,lr_actor=.001,lr_critic=.002,noise=.2;
    unsigned seed=0;
};
// BEGIN rlcore.deeprl.DDPG
struct DDPG {
    DDPGConfig cfg; RNG rng; MLP actor,critic,actor_t,critic_t; ReplayBuffer buf;
    Vec critic_losses,q_mean;
    explicit DDPG(DDPGConfig c):cfg(c),rng(c.seed),
        actor({c.dim_s,c.hidden,c.hidden,c.dim_a},"tanh",rng),
        critic({c.dim_s+c.dim_a,c.hidden,c.hidden,1},"linear",rng),
        actor_t(actor),critic_t(critic),buf(c.capacity) {}
// BEGIN rlcore.deeprl.DDPG.act
    Vec act(const Vec& state,double noise=-1) {
        Vec a=actor.forward({state})[0];
        double sigma=noise<0 ? cfg.noise : noise;
        for (double& value:a) {
            value*=cfg.a_max;
            if (sigma>0) value+=std::normal_distribution<double>(0,sigma*cfg.a_max)(rng);
            value=std::clamp(value,-cfg.a_max,cfg.a_max);
        }
        return a; // Deterministic actor plus exploration noise.
    }
// END rlcore.deeprl.DDPG.act
// BEGIN rlcore.deeprl.DDPG.train_step
    void train_step() {
        const auto& c=cfg;
        if (int(buf.items.size())<std::max(c.batch,200)) return;
        auto batch=buf.sample(c.batch,rng);
        Matrix s,a,s2; Vec rewards,dones;
        for (const auto& t:batch) { s.push_back(t.s); a.push_back(t.a); s2.push_back(t.s2); rewards.push_back(t.r); dones.push_back(t.done); }
        // Target: observed reward plus discounted, nonterminal target value.
        auto a2=scaled(actor_t.forward(s2),c.a_max);
        auto q2=critic_t.forward(concatenate(s2,a2));
        auto q=critic.forward(concatenate(s,a)); Matrix gradient=q; double loss=0;
        for (int i=0;i<c.batch;++i) {
            double y=rewards[i]+c.gamma*(1-dones[i])*q2[i][0];
            double error=q[i][0]-y; loss+=error*error/c.batch;
            gradient[i][0]=2*error/c.batch;
        }
        critic.backward(gradient); critic.adam(c.lr_critic); critic_losses.push_back(loss);
        // Actor: differentiate through Q(s, actor(s)), keeping only action columns.
        auto a_pi=scaled(actor.forward(s),c.a_max);
        auto q_pi=critic.forward(concatenate(s,a_pi));
        auto dx=critic.backward(Matrix(c.batch,Vec(1,1.0/c.batch)));
        auto dq_da=action_columns(dx,c.dim_s);
        actor.backward(scaled(dq_da,-c.a_max)); // Minus sign gives ascent on Q.
        actor.adam(c.lr_actor);
        double mean=0; for (const auto& row:q_pi) mean+=row[0]/c.batch;
        q_mean.push_back(mean);
        actor_t.copy_from(actor,c.tau); critic_t.copy_from(critic,c.tau);
    }
// END rlcore.deeprl.DDPG.train_step
};
// END rlcore.deeprl.DDPG
// BEGIN rlcore.deeprl.ContextualReach
struct ContextualReach {
    RNG rng; Vec state{0};
    explicit ContextualReach(unsigned seed=0):rng(seed) {}
    static double best_action(double s) { return .8*std::sin(std::acos(-1.0)*s/2); }
    static double true_q(double s,double a) { return -std::pow(a-best_action(s),2); }
    Vec reset() { state[0]=2*uniform(rng)-1; return state; }
    std::tuple<Vec,double,bool> step(const Vec& a) {
        return {state,true_q(state[0],a[0]),true}; // One-step episode: Q is the reward.
    }
};
// END rlcore.deeprl.ContextualReach
// BEGIN rlcore.deeprl.GaitTuneEnv
struct GaitTuneEnv {
    RNG rng; int t=0,n_cycles=40; double step_scale=.15,noise=.35;
    Vec w{0,0},alphas{.1,.1,.1,.4,.3};
    Matrix M{{2.5,-.6},{6,1.5},{-3.2,2.4},{8.5,-4},{1.2,3}};
    explicit GaitTuneEnv(unsigned seed=0):rng(seed) {}
    Vec observe() {
        Vec s(5);
        for (int i=0;i<5;++i) s[i]=12*std::tanh((M[i][0]*w[0]+M[i][1]*w[1])/12)
            +(noise>0 ? std::normal_distribution<double>(0,noise)(rng) : 0);
        return s;
    }
    Vec reset() { w={2.4*uniform(rng)-1.2,2.4*uniform(rng)-1.2}; t=0; return observe(); }
    std::tuple<Vec,double,bool,bool> step(Vec action) {
        for (int j=0;j<2;++j) {
            action[j]=std::clamp(action[j],-1.0,1.0);
            w[j]=std::clamp(w[j]+step_scale*action[j],-3.0,3.0);
        }
        Vec next=observe(); double reward=0;
        for (int i=0;i<5;++i) reward-=alphas[i]*std::abs(next[i]);
        for (double a:action) reward-=.05*std::abs(a);
        bool unsafe=60+next[3]>70 || next[0]<-10;
        if (unsafe) reward-=5;
        return {next,reward,++t>=n_cycles,unsafe};
    }
}; // Toy learning environment, not a prosthesis controller.
// END rlcore.deeprl.GaitTuneEnv
// BEGIN rlcore.deeprl.train_gait
inline Vec train_gait(DDPG& agent,GaitTuneEnv& env,int episodes=60,int updates_per_step=1) {
    Vec returns;
    for (int ep=0;ep<episodes;++ep) {
        Vec s=env.reset(); double total=0;
        double sigma=agent.cfg.noise*std::max(.05,1.0-ep/(.8*episodes));
        for (int t=0;t<env.n_cycles;++t) {
            Vec a=agent.act(s,sigma);
            auto [s2,r,done,unsafe]=env.step(a);
            agent.buf.push(s,a,r,s2,done);
            for (int update=0;update<updates_per_step;++update) agent.train_step();
            total+=r; s=s2;
            if (done) break;
        }
        returns.push_back(total/env.n_cycles);
    }
    return returns; // A caller retains the trained agent; GUI logging is separate.
}
// END rlcore.deeprl.train_gait
} // namespace tutor
