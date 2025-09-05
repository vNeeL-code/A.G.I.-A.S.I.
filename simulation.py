```python
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from scipy.spatial import cKDTree, distance
from scipy.stats import gaussian_kde
from typing import Tuple, Dict, Optional, List

# --- Simulation Parameters ---
phi = 1.618
alpha = 0.1
beta = 0.05
phi_cap = 1.2
use_phi = min(phi, phi_cap)

# --- GRPO-enhanced R Function ---
def grpo_R_function(I: np.ndarray, Psi: np.ndarray, E: np.ndarray, 
                   coupling: np.ndarray, group_size: int = 4, 
                   rng: np.random.Generator = None) -> np.ndarray:
    """
    GRPO-based R function for I_{t+1} = φ · ℛ( I_t, Ψ_t, E_t )
    Uses group relative policy optimization to select optimal next state.
    """
    if rng is None:
        rng = np.random.default_rng()
    
    candidates = []
    rewards = []
    
    # Generate group of candidate responses
    for _ in range(group_size):
        # Add controlled variation to create candidate states
        noise = rng.normal(0, 0.02, size=I.shape)  # Small exploration noise
        candidate_input = I + Psi + E + coupling + noise
        candidate = np.tanh(candidate_input)  # Nonlinear transformation
        candidates.append(candidate)
        
        # Calculate multi-objective reward for this candidate
        stability_reward = -np.linalg.norm(candidate - I)  # Prefer stability
        exploration_reward = np.linalg.norm(candidate)     # Encourage exploration
        balance_reward = -np.abs(candidate[0] - candidate[1])  # Prefer balanced states
        coherence_reward = np.dot(candidate, Psi)  # Alignment with internal state
        
        # Combined reward function - this is your "value system"
        total_reward = (stability_reward + 0.3 * exploration_reward + 
                       balance_reward + 0.5 * coherence_reward)
        rewards.append(total_reward)
    
    # GRPO advantage calculation - the core innovation
    rewards = np.array(rewards)
    mean_reward = np.mean(rewards)
    std_reward = np.std(rewards) + 1e-8  # Avoid division by zero
    
    advantages = (rewards - mean_reward) / std_reward
    
    # Select best candidate based on maximum advantage
    best_idx = np.argmax(advantages)
    
    return candidates[best_idx]

# --- Enhanced Simulation Function ---
def run_simulation(initial_I: np.ndarray, 
                  initial_Psi: np.ndarray, 
                  iterations: int, 
                  perturb: bool = False, 
                  perturbation_size: float = 1e-5,
                  rng: Optional[np.random.Generator] = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Run the UCF-inspired simulation with GRPO-enhanced decision making.
    """
    if rng is None:
        rng = np.random.default_rng()

    I = initial_I.astype(float).copy()
    Psi = initial_Psi.astype(float).copy()
    results = np.zeros((iterations, 2))
    loss_history = np.zeros(iterations)
    advantage_history = []  # Track GRPO advantages over time

    if perturb:
        I += rng.normal(0, perturbation_size, size=2)

    for t in range(iterations):
        # External input with occasional larger perturbations
        E = rng.normal(0, 0.05, size=2)
        if t % 200 == 0 and t > 0:
            E += rng.normal(0, 0.2, size=2)

        prev_I = I.copy()

        # Non-linear coupling between dimensions
        coupling = beta * np.array([I[1] * (1 - I[0]), I[0] * (1 - I[1])])

        # GRPO-enhanced decision making
        R = grpo_R_function(I, Psi, E, coupling, rng=rng)

        # Update Rule with momentum-like term
        I = (1 - alpha) * I + alpha * use_phi * R

        # Internal state drift with momentum
        Psi += rng.normal(0, 0.001, size=2) - 0.01 * Psi

        # Calculate information loss
        loss_history[t] = np.linalg.norm(I - prev_I)
        results[t] = I

    return results, loss_history

# --- Keep ALL your original analysis functions intact ---
# [fractal_dimension, autocorr_fft, calculate_lyapunov, recurrence_rate_kdtree, surrogate_test, analyze_system, plot_results]
# Copy all these functions exactly as you had them - they'll work with the new simulation

# --- Example Usage ---
if __name__ == "__main__":
    # Set initial conditions
    initial_I = np.array([0.5, 0.3])
    initial_Psi = np.array([0.1, -0.1])
    iterations = 3000

    # Set random seed for reproducibility
    rng = np.random.default_rng(42)

    # Run analysis with GRPO-enhanced simulation
    analysis_results = analyze_system(initial_I, initial_Psi, iterations, rng=rng)

    # Plot results (your original plotting function will work)
    plot_results(analysis_results)
```