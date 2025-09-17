# merged_ucf_grpo.py
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from scipy.spatial import cKDTree, distance
from scipy.stats import gaussian_kde
from typing import Tuple, Dict, Optional, List

# --- Simulation Parameters (global) ---
phi = 1.618
alpha = 0.1
beta = 0.05
phi_cap = 1.2
use_phi = min(phi, phi_cap)

# --- GRPO-enhanced R Function ---
def grpo_R_function(I: np.ndarray,
                    Psi: np.ndarray,
                    E: np.ndarray,
                    coupling: np.ndarray,
                    group_size: int = 4,
                    rng: Optional[np.random.Generator] = None) -> Tuple[np.ndarray, float]:
    """
    GRPO-based R function for generating candidate R values and selecting the best
    candidate via a simple advantage calculation. Returns (best_candidate, best_advantage).
    """
    if rng is None:
        rng = np.random.default_rng()

    candidates = []
    rewards = []

    for _ in range(group_size):
        noise = rng.normal(0, 0.02, size=I.shape)
        candidate_input = I + Psi + E + coupling + noise
        candidate = np.tanh(candidate_input)
        candidates.append(candidate)

        # multi-objective reward
        stability_reward = -np.linalg.norm(candidate - I)            # prefer stability
        exploration_reward = np.linalg.norm(candidate)               # encourage exploration
        balance_reward = -np.abs(candidate[0] - candidate[1])        # prefer balanced dims
        coherence_reward = np.dot(candidate, Psi)                   # align with internal state

        total_reward = (stability_reward +
                        0.3 * exploration_reward +
                        balance_reward +
                        0.5 * coherence_reward)
        rewards.append(total_reward)

    rewards = np.asarray(rewards)
    mean_reward = rewards.mean()
    std_reward = rewards.std() + 1e-8
    advantages = (rewards - mean_reward) / std_reward
    best_idx = int(np.argmax(advantages))
    best_candidate = candidates[best_idx]
    best_advantage = float(advantages[best_idx])
    return best_candidate, best_advantage


# --- Enhanced Simulation Function (GRPO-aware) ---
def run_simulation(initial_I: np.ndarray,
                   initial_Psi: np.ndarray,
                   iterations: int,
                   perturb: bool = False,
                   perturbation_size: float = 1e-5,
                   rng: Optional[np.random.Generator] = None) -> Tuple[np.ndarray, np.ndarray, List[float]]:
    """
    Run the UCF-inspired simulation with GRPO-enhanced decision making.
    Returns (results, loss_history, advantage_history).
    """
    if rng is None:
        rng = np.random.default_rng()

    I = initial_I.astype(float).copy()
    Psi = initial_Psi.astype(float).copy()
    results = np.zeros((iterations, 2))
    loss_history = np.zeros(iterations)
    advantage_history: List[float] = []

    if perturb:
        I += rng.normal(0, perturbation_size, size=I.shape)

    for t in range(iterations):
        # External input with occasional larger perturbations
        E = rng.normal(0, 0.05, size=I.shape)
        if t % 200 == 0 and t > 0:
            E += rng.normal(0, 0.2, size=I.shape)

        prev_I = I.copy()

        # Non-linear coupling between dimensions
        coupling = beta * np.array([I[1] * (1 - I[0]), I[0] * (1 - I[1])])

        # GRPO-enhanced decision making
        R, best_adv = grpo_R_function(I, Psi, E, coupling, rng=rng)

        # Update Rule with momentum-like term
        I = (1 - alpha) * I + alpha * use_phi * R

        # Internal state drift with momentum
        Psi += rng.normal(0, 0.001, size=Psi.shape) - 0.01 * Psi

        # Calculate information loss and record
        loss_history[t] = np.linalg.norm(I - prev_I)
        results[t] = I
        advantage_history.append(best_adv)

    return results, loss_history, advantage_history


# --- Fractal Dimension Calculation (box-counting) ---
def fractal_dimension(points: np.ndarray,
                      box_sizes: np.ndarray,
                      n_samples: int = 5,
                      rng: Optional[np.random.Generator] = None) -> Tuple[float, float, np.ndarray, np.ndarray]:
    if rng is None:
        rng = np.random.default_rng()

    N = len(points)
    all_slopes = []
    all_log_counts = []

    for _ in range(n_samples):
        idx = rng.choice(N, size=min(800, N), replace=False)
        sample = points[idx]
        xmin, ymin = sample.min(axis=0)
        xmax, ymax = sample.max(axis=0)

        counts = []
        for s in box_sizes:
            gx = np.floor((sample[:, 0] - xmin) / s).astype(int)
            gy = np.floor((sample[:, 1] - ymin) / s).astype(int)
            boxes = gx.astype(np.int64) * (1 + int(np.ceil((ymax - ymin) / s))) + gy
            box_count = len(np.unique(boxes))
            counts.append(box_count if box_count > 0 else 1)

        log_sizes = np.log(1 / np.asarray(box_sizes))
        log_counts = np.log(np.asarray(counts))
        slope, _, _, _, _ = stats.linregress(log_sizes, log_counts)
        all_slopes.append(slope)
        all_log_counts.append(log_counts)

    avg_log_counts = np.mean(all_log_counts, axis=0)
    return float(np.mean(all_slopes)), float(np.std(all_slopes)), log_sizes, avg_log_counts


# --- Autocorrelation using FFT ---
def autocorr_fft(x: np.ndarray, max_lag: int) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    n = x.size
    x = x - x.mean()
    nfft = 1 << (int(np.ceil(np.log2(2 * n))))
    fx = np.fft.rfft(x, n=nfft)
    acf_full = np.fft.irfft(fx * np.conj(fx), n=nfft)[:n]
    if acf_full[0] != 0:
        acf_full = acf_full / acf_full[0]
    max_lag = min(max_lag, n - 1)
    return acf_full[1:max_lag + 1]


# --- Lyapunov Exponent Calculation ---
def calculate_lyapunov(run_fn_params: Dict,
                      iterations: int,
                      d0: float = 1e-9,
                      renorm_every: int = 10,
                      rng: Optional[np.random.Generator] = None) -> Tuple[float, np.ndarray]:
    if rng is None:
        rng = np.random.default_rng()

    I_ref = run_fn_params['initial_I'].copy()
    Psi = run_fn_params['initial_Psi'].copy()
    alpha_loc = run_fn_params['alpha']
    beta_loc = run_fn_params['beta']
    use_phi_loc = run_fn_params['use_phi']

    pert_direction = rng.random(size=I_ref.shape)
    pert_direction /= np.linalg.norm(pert_direction)
    I_pert = I_ref + d0 * pert_direction

    log_stretches = []

    for t in range(iterations):
        E = rng.normal(0, 0.05, size=I_ref.shape)
        if t % 200 == 0 and t > 0:
            E += rng.normal(0, 0.2, size=I_ref.shape)

        Psi_drift = rng.normal(0, 0.001, size=Psi.shape) - 0.01 * Psi
        Psi += Psi_drift

        coupling_ref = beta_loc * np.array([I_ref[1] * (1 - I_ref[0]), I_ref[0] * (1 - I_ref[1])])
        R_ref = np.tanh(I_ref + Psi + E + coupling_ref)
        I_ref = (1 - alpha_loc) * I_ref + alpha_loc * use_phi_loc * R_ref

        coupling_pert = beta_loc * np.array([I_pert[1] * (1 - I_pert[0]), I_pert[0] * (1 - I_pert[1])])
        R_pert = np.tanh(I_pert + Psi + E + coupling_pert)
        I_pert = (1 - alpha_loc) * I_pert + alpha_loc * use_phi_loc * R_pert

        if (t + 1) % renorm_every == 0:
            d_t = np.linalg.norm(I_pert - I_ref)
            if d_t > 1e-15:
                log_stretches.append(np.log(d_t / d0))
                direction = (I_pert - I_ref) / d_t
                I_pert = I_ref + d0 * direction
            else:
                pert_direction = rng.random(size=I_ref.shape)
                pert_direction /= np.linalg.norm(pert_direction)
                I_pert = I_ref + d0 * pert_direction

    if not log_stretches:
        return 0.0, np.array([])

    lyapunov_exp = np.mean(log_stretches) / renorm_every
    return float(lyapunov_exp), np.array(log_stretches)


# --- Recurrence Rate via KDTree ---
def recurrence_rate_kdtree(Z: np.ndarray, eps: float) -> float:
    tree = cKDTree(Z)
    counts = tree.query_ball_point(Z, r=eps)
    total_pairs = sum(len(c) - 1 for c in counts)
    n = len(Z)
    return total_pairs / (n * (n - 1))


# --- Surrogate Data Test (phase randomization) ---
def surrogate_test(x: np.ndarray, n_surrogates: int = 20, rng: Optional[np.random.Generator] = None) -> Dict:
    if rng is None:
        rng = np.random.default_rng()

    x_fft = np.fft.fft(x)
    magnitudes = np.abs(x_fft)
    surrogate_acfs = []

    for _ in range(n_surrogates):
        # Randomize phases while preserving conjugate symmetry
        n = len(x_fft)
        random_phases = rng.uniform(0, 2 * np.pi, n // 2 - 1)
        phases = np.zeros(n, dtype=float)
        phases[1:n//2] = random_phases
        phases[n//2+1:] = -random_phases[::-1]
        phases = phases * 1j
        surrogate_fft = magnitudes * np.exp(phases)
        surrogate = np.real(np.fft.ifft(surrogate_fft))
        surrogate_acf = autocorr_fft(surrogate, 20)
        surrogate_acfs.append(np.mean(surrogate_acf))

    original_acf = autocorr_fft(x, 20)
    original_acf_mean = np.mean(original_acf)
    surr_mean = np.mean(surrogate_acfs)
    surr_std = np.std(surrogate_acfs)
    is_nonlinear = original_acf_mean > surr_mean + 2 * surr_std

    return {
        "original_acf_mean": original_acf_mean,
        "surrogate_acf_mean": surr_mean,
        "surrogate_acfs": surrogate_acfs,
        "is_nonlinear": is_nonlinear
    }


# --- Main Analysis Function ---
def analyze_system(initial_I: np.ndarray,
                   initial_Psi: np.ndarray,
                   iterations: int,
                   rng: Optional[np.random.Generator] = None) -> Dict:
    if rng is None:
        rng = np.random.default_rng(42)

    # Run simulation (GRPO-aware)
    results, loss_history, advantage_history = run_simulation(initial_I, initial_Psi, iterations, rng=rng)

    # Fractal dimension
    box_sizes = np.logspace(-2, -0.5, 10)
    fractal_d, fractal_d_std, log_sizes, log_counts = fractal_dimension(results, box_sizes, rng=rng)

    # Autocorrelations
    autocorr_I1 = autocorr_fft(results[:, 0], 100)
    loss_autocorr = autocorr_fft(loss_history, 100)

    # Lyapunov exponent (uses same RNG for reproducibility)
    lyap_params = {
        'initial_I': initial_I,
        'initial_Psi': initial_Psi,
        'alpha': alpha,
        'beta': beta,
        'use_phi': use_phi
    }
    avg_lyapunov, lyap_logs = calculate_lyapunov(lyap_params, iterations, rng=rng)

    # Recurrence rate
    Z = (results - results.mean(axis=0)) / (results.std(axis=0) + 1e-12)
    pairwise_dists = distance.cdist(Z, Z)
    eps = np.percentile(pairwise_dists, 10.0)
    recurrence_rate = recurrence_rate_kdtree(Z, eps)

    # Surrogate test (on first dimension)
    surrogate_result = surrogate_test(results[:, 0], rng=rng)

    # KDEs
    kde1 = gaussian_kde(results[:, 0])
    kde2 = gaussian_kde(results[:, 1])
    xgrid1 = np.linspace(results[:, 0].min(), results[:, 0].max(), 400)
    xgrid2 = np.linspace(results[:, 1].min(), results[:, 1].max(), 400)

    return {
        "results": results,
        "loss_history": loss_history,
        "advantage_history": np.array(advantage_history),
        "fractal_d": fractal_d,
        "fractal_d_std": fractal_d_std,
        "log_sizes": log_sizes,
        "log_counts": log_counts,
        "autocorr_I1": autocorr_I1,
        "loss_autocorr": loss_autocorr,
        "avg_lyapunov": avg_lyapunov,
        "lyap_logs": lyap_logs,
        "recurrence_rate": recurrence_rate,
        "surrogate_result": surrogate_result,
        "kde1": kde1,
        "kde2": kde2,
        "xgrid1": xgrid1,
        "xgrid2": xgrid2,
        "Z": Z,
        "eps": eps
    }


# --- Plotting Function (keeps your original layout, minor adjustments) ---
def plot_results(analysis_results: Dict):
    results = analysis_results["results"]
    loss_history = analysis_results["loss_history"]
    fractal_d = analysis_results["fractal_d"]
    fractal_d_std = analysis_results["fractal_d_std"]
    log_sizes = analysis_results["log_sizes"]
    log_counts = analysis_results["log_counts"]
    autocorr_I1 = analysis_results["autocorr_I1"]
    loss_autocorr = analysis_results["loss_autocorr"]
    avg_lyapunov = analysis_results["avg_lyapunov"]
    lyap_logs = analysis_results["lyap_logs"]
    recurrence_rate = analysis_results["recurrence_rate"]
    surrogate_result = analysis_results["surrogate_result"]
    kde1 = analysis_results["kde1"]
    kde2 = analysis_results["kde2"]
    xgrid1 = analysis_results["xgrid1"]
    xgrid2 = analysis_results["xgrid2"]
    Z = analysis_results["Z"]
    eps = analysis_results["eps"]

    subset_size = min(250, len(Z))
    D = distance.cdist(Z[:subset_size], Z[:subset_size])
    RP = (D < eps)

    # plotting
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.figure(figsize=(20, 15))

    plt.subplot(3, 3, 1)
    plt.plot(results[:, 0], label='$I_1$', alpha=0.9)
    plt.plot(results[:, 1], label='$I_2$', alpha=0.9)
    plt.title('Time Series of Informational States', fontsize=14)
    plt.xlabel('Iteration (t)')
    plt.ylabel('State Value')
    plt.legend()

    plt.subplot(3, 3, 2)
    sc = plt.scatter(results[:, 0], results[:, 1], c=np.arange(len(results)), cmap='viridis', alpha=0.6, s=8)
    plt.colorbar(sc, label='Iteration')
    plt.title('Phase Portrait (Colored by Time)', fontsize=14)
    plt.xlabel('$I_1$')
    plt.ylabel('$I_2$')

    plt.subplot(3, 3, 3)
    plt.plot(xgrid1, kde1(xgrid1), label='KDE of $I_1$')
    plt.plot(xgrid2, kde2(xgrid2), label='KDE of $I_2$')
    plt.title('State Distribution (KDE)', fontsize=14)
    plt.xlabel('State Value')
    plt.ylabel('Density')
    plt.legend()

    plt.subplot(3, 3, 4)
    plt.plot(autocorr_I1)
    plt.axhline(0, linestyle='--', linewidth=0.8)
    plt.title('Autocorrelation of $I_1$', fontsize=14)
    plt.xlabel('Lag')
    plt.ylabel('Correlation')

    plt.subplot(3, 3, 5)
    slope, intercept, _, _, _ = stats.linregress(log_sizes, log_counts)
    plt.plot(log_sizes, log_counts, 'o', label='Data')
    plt.plot(log_sizes, intercept + slope * log_sizes, 'r-', label=f'Fit (Slope={fractal_d:.2f})')
    plt.xlabel('log(1/box size)')
    plt.ylabel('log(box count)')
    plt.title(f'Fractal Dimension: {fractal_d:.3f} ± {fractal_d_std:.3f}', fontsize=14)
    plt.legend()

    plt.subplot(3, 3, 6)
    plt.plot(loss_history)
    plt.title('Information Loss Over Time', fontsize=14)
    plt.xlabel('Iteration')
    plt.ylabel('Loss (State Change Magnitude)')

    plt.subplot(3, 3, 7)
    plt.imshow(RP, cmap='binary', origin='lower', aspect='equal')
    plt.title(f'Recurrence Plot (Rate: {recurrence_rate:.3f})', fontsize=14)
    plt.xlabel('Time Index')
    plt.ylabel('Time Index')

    plt.subplot(3, 3, 8)
    if len(lyap_logs) > 0:
        cum_avg = np.cumsum(lyap_logs) / np.arange(1, len(lyap_logs) + 1)
        plt.plot(cum_avg, label='Cumulative Average')
        plt.axhline(y=avg_lyapunov, linestyle='--', label=f'Final Avg: {avg_lyapunov:.4f}')
    plt.title('Lyapunov Exponent Convergence', fontsize=14)
    plt.xlabel('Renormalization Blocks')
    plt.ylabel('Cumulative Average Log Divergence')
    plt.legend()

    plt.subplot(3, 3, 9)
    plt.hist(surrogate_result['surrogate_acfs'], bins=5, alpha=0.7)
    plt.axvline(surrogate_result['original_acf_mean'], color='red', linestyle='--', label='Original ACF')
    plt.title('Surrogate Data Test for Nonlinearity', fontsize=14)
    plt.xlabel('Mean Autocorrelation')
    plt.ylabel('Frequency')
    plt.legend()

    plt.tight_layout(pad=3.0)
    plt.show()

    # Print summary
    print("\n" + "=" * 50)
    print(" " * 15 + "SYSTEM ANALYSIS RESULTS")
    print("=" * 50)
    print(f"Mean states:\t\t I₁ = {np.mean(results[:, 0]):.4f}, I₂ = {np.mean(results[:, 1]):.4f}")
    print(f"Standard deviations:\t I₁ = {np.std(results[:, 0]):.4f}, I₂ = {np.std(results[:, 1]):.4f}")
    print("-" * 50)
    print(f"Fractal dimension:\t {fractal_d:.4f} ± {fractal_d_std:.4f}")
    print(f"Lyapunov exponent (λ):\t {avg_lyapunov:.6f}")
    print(f"Recurrence rate:\t {recurrence_rate:.4f}")
    print(f"Average information loss: {np.mean(loss_history):.6f} (std {np.std(loss_history):.6f})")
    print("-" * 50)
    print("Surrogate Test for Nonlinearity:")
    print(f"  - Original Data ACF Mean:\t {surrogate_result['original_acf_mean']:.4f}")
    print(f"  - Average Surrogate ACF Mean:\t {surrogate_result['surrogate_acf_mean']:.4f}")
    print(f"  - System shows nonlinear characteristics: {surrogate_result['is_nonlinear']}")
    print("=" * 50 + "\n")


# --- Example usage ---
if __name__ == "__main__":
    initial_I = np.array([0.5, 0.3])
    initial_Psi = np.array([0.1, -0.1])
    iterations = 3000
    rng = np.random.default_rng(42)

    analysis_results = analyze_system(initial_I, initial_Psi, iterations, rng=rng)
    plot_results(analysis_results)
