#include "check.hpp"
#include "model_share.hpp"

int main() {
    std::shared_ptr<const Model> m = std::make_shared<Model>(Model{"arm", 3.5});
    CHECK_EQ("one owner to start", m.use_count(), 1L);
    auto planner = std::make_unique<Planner>(m);
    CHECK_EQ("the planner is a second owner", m.use_count(), 2L);
    CHECK_NEAR("planner reads the model", planner->mass(), 3.5, 0.0);
    Logger log(m);
    CHECK_EQ("the logger does NOT own it (weak_ptr)", m.use_count(), 2L);
    CHECK("logger sees it alive", log.modelAlive());
    CHECK_EQ("logger describes it", log.describe(), std::string("arm"));
    m.reset();
    CHECK("we let go, but the planner keeps it alive", log.modelAlive());
    CHECK_NEAR("planner still works", planner->mass(), 3.5, 0.0);
    planner.reset();
    CHECK("last owner gone -> the model is destroyed", !log.modelAlive());
    CHECK_EQ("logger says gone instead of crashing", log.describe(), std::string("gone"));
    DONE();
}
