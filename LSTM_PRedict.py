import numpy as np
import scipy.io as sio
from scipy.signal import butter, filtfilt
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
import itertools
import time

# ==========================================
# 1. DATA LOADING & PREPROCESSING
# ==========================================
# ==========================================
# 1. DATA LOADING & FILTERING
# ==========================================
mat_contents = sio.loadmat('C:/Users/Amirreza Naseri/OneDrive - University of North Carolina at Chapel Hill/1.1Fault Tolerance Study/Science Robotic/PilotTest/TF02/PoweredKnee/Training.mat')
data_test = mat_contents['DataTest'] 

# MATLAB indices 56372:301903
data = data_test[56371:301903, :]

# Extract Raw Signals
force_z      = data[:, 0]
knee_vel     = data[:, 2]
force_deriv  = data[:, 6]
force_z_flex = data[:, 10]
# Note: Ensure these column indices match your MATLAB exactly

# 3. Low-Pass Filter (Butterworth 4th order, 20Hz cutoff)
# This removes high-frequency noise from the load cell before the LSTM sees it
b, a = butter(4, 20/(1000/2), btype='low')
force_z_filt = filtfilt(b, a, force_z)
# We use the filtered force for training
force_deriv_filt = np.gradient(force_z_filt) 

# ==========================================
# 2. STANCE SEGMENTATION (Gait Cycle Extraction)
# ==========================================
# Identify indices where the prosthesis is in stance (Flexion Force > 20)
st_f = np.where(force_z_flex > 20)[0]
sft = np.diff(st_f)
check_f = np.where(sft > 400)[0]

start_f = st_f[check_f + 1] - 5
end_f = st_f[check_f]

# Create X_Stance and Y_Stance by concatenating only the stance segments
X_list = []
Y_list = []

for i in range(len(start_f) - 1):
    # Extract one specific stance phase
    segment_x = np.column_stack((force_z_filt[start_f[i]:end_f[i+1]], 
                                 force_deriv_filt[start_f[i]:end_f[i+1]]))
    segment_y = knee_vel[start_f[i]:end_f[i+1]]
    
    X_list.append(segment_x)
    Y_list.append(segment_y)

# Combine all stance segments into one large training array
X_continuous = np.vstack(X_list)
Y_velocity = np.concatenate(Y_list)

print(f"Total Stance Data Points: {X_continuous.shape[0]}")

# Split 80/20 for Train/Test (Keep order for time-series)
X_train_raw, X_test_raw, y_train_raw, y_test_raw = train_test_split(
    X_continuous, Y_velocity, test_size=0.2, shuffle=False
)

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def create_sliding_windows(x_data, y_data, window_size):
    x_out, y_out = [], []
    for i in range(len(x_data) - window_size):
        x_out.append(x_data[i : i + window_size, :])
        y_out.append(y_data[i + window_size])
    return np.array(x_out), np.array(y_out)

def train_model(model, train_loader, criterion, optimizer, epochs=25):
    model.train()
    for epoch in range(epochs):
        for inputs, targets in train_loader:
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs.squeeze(), targets)
            loss.backward()
            optimizer.step()

def evaluate_model(model, test_loader):
    model.eval()
    errors = []
    with torch.no_grad():
        for inputs, targets in test_loader:
            outputs = model(inputs)
            mse = torch.mean((outputs.squeeze() - targets)**2)
            errors.append(mse.item())
    return np.sqrt(np.mean(errors)) # Returns RMSE

# ==========================================
# 3. MODEL DEFINITION
# ==========================================
class ProsthesisLSTM(nn.Module):
    def __init__(self, input_size, hidden_size, fc_size):
        super(ProsthesisLSTM, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, fc_size)
        self.out = nn.Linear(fc_size, 1)
        
    def forward(self, x):
        # x shape: (batch, seq_len, features)
        _, (h_n, _) = self.lstm(x) 
        # h_n[-1] is the last hidden state of the last layer
        x = torch.relu(self.fc(h_n[-1]))
        return self.out(x)

# ==========================================
# 4. EXPERIMENT 1: HYPERPARAMETER SWEEP
# ==========================================
# (For the sweep, we'll use a fixed W=100 to find best capacity)
W_fixed = 100
X_tr, y_tr = create_sliding_windows(X_train_raw, y_train_raw, W_fixed)
X_te, y_te = create_sliding_windows(X_test_raw, y_test_raw, W_fixed)

train_loader = DataLoader(TensorDataset(torch.Tensor(X_tr), torch.Tensor(y_tr)), batch_size=512, shuffle=True)
test_loader = DataLoader(TensorDataset(torch.Tensor(X_te), torch.Tensor(y_te)), batch_size=512)

results_sweep = []
for h_dim, fc_dim, lr, l2 in itertools.product([8, 16, 32], [8, 16, 32], [1e-3, 5e-3], [1e-3]):
    model = ProsthesisLSTM(2, h_dim, fc_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=l2)
    criterion = nn.MSELoss()
    
    train_model(model, train_loader, criterion, optimizer, epochs=5) # Short sweep
    rmse = evaluate_model(model, test_loader)
    results_sweep.append(((h_dim, fc_dim, lr, l2), rmse))
    print(f"Sweep - H:{h_dim} FC:{fc_dim} LR:{lr} -> RMSE: {rmse:.4f}")

# Find best architecture
best_params = min(results_sweep, key=lambda x: x[1])[0]
print(f"Best Architecture: {best_params}")

# ==========================================
# 5. EXPERIMENT 2: WINDOW SENSITIVITY
# ==========================================
window_sizes = [20, 50, 100, 150] # Subset for speed
results_window = {}

for W in window_sizes:
    X_tr, y_tr = create_sliding_windows(X_train_raw, y_train_raw, W)
    X_te, y_te = create_sliding_windows(X_test_raw, y_test_raw, W)
    
    t_loader = DataLoader(TensorDataset(torch.Tensor(X_tr), torch.Tensor(y_tr)), batch_size=512, shuffle=True)
    v_loader = DataLoader(TensorDataset(torch.Tensor(X_te), torch.Tensor(y_te)), batch_size=512)
    
    model = ProsthesisLSTM(2, best_params[0], best_params[1])
    optimizer = torch.optim.Adam(model.parameters(), lr=best_params[2], weight_decay=best_params[3])
    
    train_model(model, t_loader, nn.MSELoss(), optimizer, epochs=25)
    rmse = evaluate_model(model, v_loader)
    results_window[W] = rmse
    print(f"Window Analysis - W:{W}ms -> RMSE: {rmse:.4f}")

# ==========================================
# 6. EXPERIMENT 3: STABILITY (5 Runs)
# ==========================================
best_W = 100 
seeds = [42, 123, 999, 7, 21]
stability_errors = []

for seed in seeds:
    torch.manual_seed(seed)
    # Re-prepare best window data
    X_tr, y_tr = create_sliding_windows(X_train_raw, y_train_raw, best_W)
    X_te, y_te = create_sliding_windows(X_test_raw, y_test_raw, best_W)
    t_loader = DataLoader(TensorDataset(torch.Tensor(X_tr), torch.Tensor(y_tr)), batch_size=512, shuffle=True)
    v_loader = DataLoader(TensorDataset(torch.Tensor(X_te), torch.Tensor(y_te)), batch_size=512)

    model = ProsthesisLSTM(2, best_params[0], best_params[1])
    optimizer = torch.optim.Adam(model.parameters(), lr=best_params[2], weight_decay=best_params[3])
    
    train_model(model, t_loader, nn.MSELoss(), optimizer, epochs=25)
    stability_errors.append(evaluate_model(model, v_loader))

print(f"Final Stability - Mean RMSE: {np.mean(stability_errors):.4f}, Var: {np.var(stability_errors):.6f}")