#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <Eigen/Dense>

using namespace Eigen;

class GaussianRegressionProcess {
private:
    MatrixXd train_X; // active set (support vectors)
    VectorXd alpha; // Pre-computed weights
    double length_scale; // hyperparameter theta
    double sigma_f;  // signal variance

    double matern32_kernel_ARD(const VectorXd& x1, const VectorXd& x2, const VectorXd& length_scales, double sigma_f) {
        // 1. Calculate ARD distance: sum of ((x1_i - x2_i)^2 / l_i^2)
        double weighted_dist_sq = 0.0;
        for (int i = 0; i < x1.size(); ++i) {
            double diff = x1(i) - x2(i);
            weighted_dist_sq += (diff * diff) / (length_scales(i) * length_scales(i));
        }
        double r = std::sqrt(weighted_dist_sq);

        // 2. Matern 3/2 math
        double sqrt3 = std::sqrt(3.0);
        double val = (1.0 + sqrt3 * r) * std::exp(-sqrt3 * r);

        // 3. Scale by signal variance (sigma_f^2)
        return sigma_f * sigma_f * val;
    }
public:
    GaussianRegressionProcess(const MatrixXd X, const VectorXd y, double l, double s) : train_X(X), length_scale(l), sigma_f(s) {
        // Pre-compute alpha = (K + sigma_n^2 I)^-1 y
        int n = X.rows();
        MatrixXd K(n, n);
        VectorXd length_scales = VectorXd::Constant(X.cols(), length_scale);
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                K(i, j) = matern32_kernel_ARD(X  .row(i), X.row(j), length_scales, sigma_f);
            }
        }
        // Add small noise term for numerical stability
        K += 1e-6 * MatrixXd::Identity(n, n);
        alpha = K.ldlt().solve(y);
    }

    void setAlpha(VectorXd a) { alpha = a; }

    double predict(VectorXd current_input){
        int n_train = train_X.rows();
        VectorXd k_star(n_train);

        for (int i = 0; i < n_train; ++i) {
            k_star(i) = matern32_kernel_ARD(current_input, train_X.row(i), VectorXd::Constant(train_X.cols(), length_scale), sigma_f);
        }
        return k_star.dot(alpha);
    }
};

int main() {
    MatrixXd training_samples(3, 2);
    training_samples << 100.0, 5.0,
                        150.0, 10.0,
                        200.0, 15.0;
    VectorXd weight(3);
    weight << 0.6,0.2,-0.1;

    GaussianRegressionProcess grp(training_samples, VectorXd::Zero(3), 10.0, 1.0);
    grp.setAlpha(weight);

    VectorXd sensor_reading(2);
    sensor_reading << 180.0, 12.0;

    double prediction = grp.predict(sensor_reading);
    std::cout << "Predicted value: " << prediction << std::endl;

    return 0;
}