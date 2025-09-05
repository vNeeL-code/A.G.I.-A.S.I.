import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from scipy.spatial import cKDTree, distance
from scipy.stats import gaussian_kde
from typing import Tuple, Dict, Optional

# --- Simulation Parameters ---
# These are defined globally so they can be accessed by multiple functions
phi = 1.618
alpha = 0.1
beta = 0.05
phi_cap = 1.2
use_phi = min(phi, phi_cap)

# --- Simulation Function ---
def run_simulation(initial_I: np.ndarray, 
                  initial_Psi: np.ndarray, 
                  iterations: int, 
                  perturb: bool = False, 
                  perturbation_size: float = 1e-5,
                  rng: Optional[np.random.Generator] = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Run the UCF-inspired simulation.
    
    Parameters:
    -----------
    initial_I : np.ndarray
        Initial informational state
    initial_Psi : np.ndarray
        Initial internal state
    iterations : int
        Number of iterations to simulate
    perturb : bool
        Whether to apply a small perturbation to initial state
    perturbation_size : float
        Size of initial perturbation
    rng : np.random.Generator
        Random number generator for reproducibility
        
    Returns:
    --------
    results : np.ndarray
        Array of informational states over time
    loss_history : np.ndarray
        Array of information loss values over time
    """
    if rng is None:
        rng = np.random.default_rng()

    I = initial_I.astype(float).copy()
    Psi = initial_Psi.astype(float).copy()
    results = np.zeros((iterations, 2))
    loss_history = np.zeros(iterations)

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

        # The Recursive Function with coupling
        R = np.tanh(I + Psi + E + coupling)

        # Update Rule with momentum-like term
        I = (1 - alpha) * I + alpha * use_phi * R

        # Internal state drift with momentum
        Psi += rng.normal(0, 0.001, size=2) - 0.01 * Psi

        # Calculate information loss
        loss_history[t] = np.linalg.norm(I - prev_I)
        results[t] = I

    return results, loss_history


# --- Fractal Dimension Calculation ---
def fractal_dimension(points: np.ndarray, 
                     box_sizes: np.ndarray, 
                     n_samples: int = 5,
                     rng: Optional[np.random.Generator] = None) -> Tuple[float, float, np.ndarray, np.ndarray]:
    """
    Calculate fractal dimension using box-counting method.
    
    Parameters:
    -----------
    points : np.ndarray
        Array of points in phase space
    box_sizes : np.ndarray
        Array of box sizes to use
    n_samples : int
        Number of random samples to average over
    rng : np.random.Generator
        Random number generator
        
    Returns:
    --------
    mean_dim : float
        Mean fractal dimension
    std_dim : float
        Standard deviation of fractal dimension estimates
    log_sizes : np.ndarray
        Log of box sizes
    log_counts : np.ndarray
        Log of box counts (averaged across samples)
    """
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
            # Grid indices for each point
            gx = np.floor((sample[:, 0] - xmin) / s).astype(int)
            gy = np.floor((sample[:, 1] - ymin) / s).astype(int)

            # Unique boxes
            boxes = gx.astype(np.int64) * (1 + int(np.ceil((ymax - ymin) / s))) + gy
            box_count = len(np.unique(boxes))
            counts.append(box_count if box_count > 0 else 1)

        log_sizes = np.log(1 / np.asarray(box_sizes))
        log_counts = np.log(np.asarray(counts))

        slope, _, _, _, _ = stats.linregress(log_sizes, log_counts)
        all_slopes.append(slope)
        all_log_counts.append(log_counts)

    # Average log counts across samples
    avg_log_counts = np.mean(all_log_counts, axis=0)

    return float(np.mean(all_slopes)), float(np.std(all_slopes)), log_sizes, avg_log_counts


# --- Autocorrelation Function ---
def autocorr_fft(x: np.ndarray, max_lag: int) -> np.ndarray:
    """
    Calculate autocorrelation using FFT.
    
    Parameters:
    -----------
    x : np.ndarray
        Input time series
    max_lag : int
        Maximum lag to calculate
        
    Returns:
    --------
    acf : np.ndarray
        Autocorrelation function values
    """
    x = np.asarray(x, dtype=float)
    n = x.size
    x = x - x.mean()

    # Choose nfft = next power of two >= 2*n for circular conv safety and speed
    nfft = 1 << (int(np.ceil(np.log2(2 * n))))
    fx = np.fft.rfft(x, n=nfft)
    acf_full = np.fft.irfft(fx * np.conj(fx), n=nfft)[:n]

    # Normalize
    if acf_full[0] != 0:
        acf_full = acf_full / acf_full[0]

    max_lag = min(max_lag, n - 1)
    return acf_full[1:max_lag + 1]


# --- Lyapunov Exponent Calculation (Improved) ---
def calculate_lyapunov(run_fn_params: Dict, 
                      iterations: int,
                      d0: float = 1e-9, 
                      renorm_every: int = 10,
                      rng: Optional[np.random.Generator] = None) -> Tuple[float, np.ndarray]:
    """
    Calculate the largest Lyapunov exponent using the standard algorithm.
    
    This method evolves a reference trajectory and a perturbed trajectory
    simultaneously, ensuring both are subject to the exact same noise.
    
    Parameters:
    -----------
    run_fn_params : Dict
        Dictionary of parameters for the simulation function.
    iterations : int
        Total number of iterations.
    d0 : float
        Initial separation between trajectories.
    renorm_every : int
        Number of steps between renormalizations.
    rng : np.random.Generator
        Random number generator.
        
    Returns:
    --------
    lyapunov_exp : float
        The estimated largest Lyapunov exponent.
    log_stretches : np.ndarray
        The history of log-scaled divergences.
    """
    if rng is None:
        rng = np.random.default_rng()

    # Unpack parameters
    I_ref = run_fn_params['initial_I'].copy()
    Psi = run_fn_params['initial_Psi'].copy()
    alpha = run_fn_params['alpha']
    beta = run_fn_params['beta']
    use_phi = run_fn_params['use_phi']

    # Create a perturbed trajectory
    pert_direction = rng.random(size=I_ref.shape)
    pert_direction /= np.linalg.norm(pert_direction)
    I_pert = I_ref + d0 * pert_direction

    log_stretches = []

    for t in range(iterations):
        # --- Apply the same dynamics and noise to both trajectories ---
        # External input
        E = rng.normal(0, 0.05, size=2)
        if t % 200 == 0 and t > 0:
            E += rng.normal(0, 0.2, size=2)

        # Internal state drift
        Psi_drift = rng.normal(0, 0.001, size=2) - 0.01 * Psi
        Psi += Psi_drift

        # --- Update Reference Trajectory ---
        coupling_ref = beta * np.array([I_ref[1] * (1 - I_ref[0]), I_ref[0] * (1 - I_ref[1])])
        R_ref = np.tanh(I_ref + Psi + E + coupling_ref)
        I_ref = (1 - alpha) * I_ref + alpha * use_phi * R_ref

        # --- Update Perturbed Trajectory ---
        coupling_pert = beta * np.array([I_pert[1] * (1 - I_pert[0]), I_pert[0] * (1 - I_pert[1])])
        R_pert = np.tanh(I_pert + Psi + E + coupling_pert)
        I_pert = (1 - alpha) * I_pert + alpha * use_phi * R_pert

        # --- Renormalization Step ---
        if (t + 1) % renorm_every == 0:
            d_t = np.linalg.norm(I_pert - I_ref)

            # Avoid log(0)
            if d_t > 1e-15:
                log_stretches.append(np.log(d_t / d0))

                # Renormalize: reset the perturbed point
                direction = (I_pert - I_ref) / d_t
                I_pert = I_ref + d0 * direction
            else:
                # If they collapse, re-perturb in a random direction
                pert_direction = rng.random(size=I_ref.shape)
                pert_direction /= np.linalg.norm(pert_direction)
                I_pert = I_ref + d0 * pert_direction

    if not log_stretches:
        return 0.0, np.array([])

    # The Lyapunov exponent is the average rate of separation
    lyapunov_exp = np.mean(log_stretches) / renorm_every
    return float(lyapunov_exp), np.array(log_stretches)


# --- Recurrence Rate Calculation ---
def recurrence_rate_kdtree(Z: np.ndarray, eps: float) -> float:
    """
    Calculate recurrence rate using KDTree for efficiency.
    
    Parameters:
    -----------
    Z : np.ndarray
        Normalized state vectors
    eps : float
        Recurrence threshold
        
    Returns:
    --------
    recurrence_rate : float
        Recurrence rate
    """
    tree = cKDTree(Z)
    counts = tree.query_ball_point(Z, r=eps)
    # Each counts[i] includes i itself, so subtract 1
    total_pairs = sum(len(c) - 1 for c in counts)
    n = len(Z)
    # Recurrence rate normalized to n*n
    return total_pairs / (n * (n - 1))


# --- Surrogate Data Test ---
def surrogate_test(x: np.ndarray, n_surrogates: int = 20, rng: Optional[np.random.Generator] = None) -> Dict:
    """
    Perform surrogate data test for nonlinearity using phase randomization.
    
    Parameters:
    -----------
    x : np.ndarray
        Input time series
    n_surrogates : int
        Number of surrogate datasets to generate
    rng : np.random.Generator
        Random number generator
        
    Returns:
    --------
    result : dict
        Dictionary with test results
    """
    if rng is None:
        rng = np.random.default_rng()

    # Phase randomization
    x_fft = np.fft.fft(x)
    magnitudes = np.abs(x_fft)

    surrogate_acfs = []
    for _ in range(n_surrogates):
        # Randomize phases, maintaining conjugate symmetry for real output
        random_phases = rng.uniform(0, 2 * np.pi, len(x_fft) // 2 + 1)
        phases = np.concatenate([random_phases, -random_phases[-2:0:-1]])
        surrogate_fft = magnitudes * np.exp(1j * phases)
        surrogate = np.real(np.fft.ifft(surrogate_fft))

        # Calculate ACF for surrogate
        surrogate_acf = autocorr_fft(surrogate, 20)
        surrogate_acfs.append(np.mean(surrogate_acf))

    # Calculate ACF for original data
    original_acf = autocorr_fft(x, 20)
    original_acf_mean = np.mean(original_acf)

    # A more robust check: is the original value an outlier compared to the surrogates?
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
    """
    Perform complete analysis of the UCF system.
    
    Parameters:
    -----------
    initial_I : np.ndarray
        Initial informational state
    initial_Psi : np.ndarray
        Initial internal state
    iterations : int
        Number of iterations to simulate
    rng : np.random.Generator
        Random number generator
        
    Returns:
    --------
    results : dict
        Dictionary with all analysis results
    """
    if rng is None:
        rng = np.random.default_rng(42)

    # Run simulation
    results, loss_history = run_simulation(initial_I, initial_Psi, iterations, rng=rng)

    # Calculate fractal dimension
    box_sizes = np.logspace(-2, -0.5, 10)
    fractal_d, fractal_d_std, log_sizes, log_counts = fractal_dimension(results, box_sizes, rng=rng)

    # Calculate autocorrelations
    autocorr_I1 = autocorr_fft(results[:, 0], 100)
    loss_autocorr = autocorr_fft(loss_history, 100)

    # Calculate Lyapunov exponent
    lyap_params = {
        'initial_I': initial_I,
        'initial_Psi': initial_Psi,
        'alpha': alpha,
        'beta': beta,
        'use_phi': use_phi
    }
    avg_lyapunov, lyap_logs = calculate_lyapunov(lyap_params, iterations, rng=rng)

    # Calculate recurrence rate
    Z = (results - results.mean(axis=0)) / (results.std(axis=0) + 1e-12)
    # Using scipy.spatial.distance.cdist
    pairwise_dists = distance.cdist(Z, Z)
    eps = np.percentile(pairwise_dists, 10.0)
    recurrence_rate = recurrence_rate_kdtree(Z, eps)

    # Perform surrogate test
    surrogate_result = surrogate_test(results[:, 0], rng=rng)

    # Prepare KDEs
    kde1 = gaussian_kde(results[:, 0])
    kde2 = gaussian_kde(results[:, 1])
    xgrid1 = np.linspace(results[:, 0].min(), results[:, 0].max(), 400)
    xgrid2 = np.linspace(results[:, 1].min(), results[:, 1].max(), 400)

    # Return all results
    return {
        "results": results,
        "loss_history": loss_history,
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


# --- Plotting Function ---
def plot_results(analysis_results: Dict):
    """
    Create comprehensive visualization of analysis results.
    
    Parameters:
    -----------
    analysis_results : dict
        Dictionary with analysis results from analyze_system
    """
    # Extract results
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

    # Create recurrence matrix for plotting (using a smaller subset for speed)
    subset_size = 250
    D = distance.cdist(Z[:subset_size], Z[:subset_size])
    RP = (D < eps)

    # Create figure
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.figure(figsize=(20, 15))

    # Time series
    plt.subplot(3, 3, 1)
    plt.plot(results[:, 0], label='$I_1$', alpha=0.9)
    plt.plot(results[:, 1], label='$I_2$', alpha=0.9)
    plt.title('Time Series of Informational States', fontsize=14)
    plt.xlabel('Iteration (t)')
    plt.ylabel('State Value')
    plt.legend()

    # Phase portrait
    plt.subplot(3, 3, 2)
    sc = plt.scatter(results[:, 0], results[:, 1], c=np.arange(len(results)), cmap='viridis', alpha=0.6, s=8)
    plt.colorbar(sc, label='Iteration')
    plt.title('Phase Portrait (Colored by Time)', fontsize=14)
    plt.xlabel('$I_1$')
    plt.ylabel('$I_2$')

    # Distribution with KDE
    plt.subplot(3, 3, 3)
    plt.plot(xgrid1, kde1(xgrid1), label='KDE of $I_1$')
    plt.plot(xgrid2, kde2(xgrid2), label='KDE of $I_2$')
    plt.title('State Distribution (KDE)', fontsize=14)
    plt.xlabel('State Value')
    plt.ylabel('Density')
    plt.legend()

    # Autocorrelation of I1
    plt.subplot(3, 3, 4)
    plt.plot(autocorr_I1)
    plt.axhline(0, color='gray', linestyle='--', linewidth=0.8)
    plt.title('Autocorrelation of $I_1$', fontsize=14)
    plt.xlabel('Lag')
    plt.ylabel('Correlation')

    # Fractal dimension analysis
    plt.subplot(3, 3, 5)
    slope, intercept, _, _, _ = stats.linregress(log_sizes, log_counts)
    plt.plot(log_sizes, log_counts, 'o', label='Data')
    plt.plot(log_sizes, intercept + slope * log_sizes, 'r-', label=f'Fit (Slope={fractal_d:.2f})')
    plt.xlabel('log(1/box size)')
    plt.ylabel('log(box count)')
    plt.title(f'Fractal Dimension: {fractal_d:.3f} ± {fractal_d_std:.3f}', fontsize=14)
    plt.legend()

    # Loss history
    plt.subplot(3, 3, 6)
    plt.plot(loss_history, color='teal')
    plt.title('Information Loss Over Time', fontsize=14)
    plt.xlabel('Iteration')
    plt.ylabel('Loss (State Change Magnitude)')

    # Recurrence plot
    plt.subplot(3, 3, 7)
    plt.imshow(RP, cmap='binary', origin='lower', aspect='equal')
    plt.title(f'Recurrence Plot (Rate: {recurrence_rate:.3f})', fontsize=14)
    plt.xlabel('Time Index')
    plt.ylabel('Time Index')

    # Lyapunov exponent
    plt.subplot(3, 3, 8)
    if len(lyap_logs) > 0:
        cum_avg = np.cumsum(lyap_logs) / np.arange(1, len(lyap_logs) + 1)
        plt.plot(cum_avg, label='Cumulative Average')
        plt.axhline(y=avg_lyapunov, color='r', linestyle='--', label=f'Final Avg: {avg_lyapunov:.4f}')
    plt.title('Lyapunov Exponent Convergence', fontsize=14)
    plt.xlabel('Renormalization Blocks')
    plt.ylabel('Cumulative Average Log Divergence')
    plt.legend()

    # Surrogate Test Visualization
    plt.subplot(3, 3, 9)
    plt.hist(surrogate_result['surrogate_acfs'], bins=5, label='Surrogate ACFs', alpha=0.7)
    plt.axvline(surrogate_result['original_acf_mean'], color='red', linestyle='--', label='Original ACF')
    plt.title('Surrogate Data Test for Nonlinearity', fontsize=14)
    plt.xlabel('Mean Autocorrelation')
    plt.ylabel('Frequency')
    plt.legend()

    plt.tight_layout(pad=3.0)
    plt.show()

    # --- Print Summary ---
    print("\n" + "="*50)
    print(" " * 15 + "SYSTEM ANALYSIS RESULTS")
    print("="*50)
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
    print("="*50 + "\n")


# --- Main Execution ---
if __name__ == "__main__":
    # Set initial conditions and simulation length
    initial_I = np.array([0.5, 0.3])
    initial_Psi = np.array([0.1, -0.1])
    iterations = 3000

    # Set random seed for reproducibility
    rng = np.random.default_rng(42)

    # Run analysis
    analysis_results = analyze_system(initial_I, initial_Psi, iterations, rng=rng)

    # Plot results
    plot_results(analysis_results)
