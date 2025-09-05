merged_ucf_grpo.py

import numpy as np import matplotlib.pyplot as plt from scipy import stats from scipy.spatial import cKDTree,distance from scipy.stats import gaussian_kde from typing import Tuple,Dict, Optional, List

--- Simulation Parameters (global) ---

phi = 1.618 alpha= 0.1 beta= 0.05 phi_cap= 1.2 use_phi= min(phi, phi_cap)

--- GRPO-enhanced R Function ---

def grpo_R_function(I: np.ndarray, Psi: np.ndarray, E: np.ndarray, coupling: np.ndarray, group_size: int = 4, rng: Optional[np.random.Generator] = None) -> Tuple[np.ndarray, float]: """ GRPO-based R function for generating candidate R values and selecting the best candidate via a simple advantage calculation. Returns (best_candidate, best_advantage). """ if rng is None: rng = np.random.default_rng()

--- Enhanced Simulation Function (GRPO-aware) ---

def run_simulation(initial_I: np.ndarray, initial_Psi: np.ndarray, iterations: int, perturb: bool = False, perturbation_size: float = 1e-5, rng: Optional[np.random.Generator] = None) -> Tuple[np.ndarray, np.ndarray, List[float]]: """ Run the UCF-inspired simulation with GRPO-enhanced decision making. Returns (results, loss_history, advantage_history). """ if rng is None: rng = np.random.default_rng()

--- Fractal Dimension Calculation (box-counting) ---

def fractal_dimension(points: np.ndarray, box_sizes: np.ndarray, n_samples: int = 5, rng: Optional[np.random.Generator] = None) -> Tuple[float, float, np.ndarray, np.ndarray]: if rng is None: rng = np.random.default_rng()

--- Autocorrelation using FFT ---

def autocorr_fft(x: np.ndarray, max_lag: int) -> np.ndarray: x = np.asarray(x, dtype=float) n = x.size x = x - x.mean() nfft = 1 << (int(np.ceil(np.log2(2 * n)))) fx = np.fft.rfft(x, n=nfft) acf_full = np.fft.irfft(fx * np.conj(fx), n=nfft)[:n] if acf_full[0] != 0: acf_full = acf_full / acf_full[0] max_lag = min(max_lag, n - 1) return acf_full[1:max_lag + 1]

--- Lyapunov Exponent Calculation ---

def calculate_lyapunov(run_fn_params: Dict, iterations: int, d0: float = 1e-9, renorm_every: int = 10, rng: Optional[np.random.Generator] = None) -> Tuple[float, np.ndarray]: if rng is None: rng = np.random.default_rng()

--- Recurrence Rate via KDTree ---

def recurrence_rate_kdtree(Z: np.ndarray, eps: float) -> float: tree = cKDTree(Z) counts = tree.query_ball_point(Z, r=eps) total_pairs = sum(len(c) - 1 for c in counts) n = len(Z) return total_pairs / (n * (n - 1))

--- Surrogate Data Test (phase randomization) ---

def surrogate_test(x: np.ndarray, n_surrogates: int = 20, rng: Optional[np.random.Generator] = None) -> Dict: if rng is None: rng = np.random.default_rng()

--- Main Analysis Function ---

def analyze_system(initial_I: np.ndarray, initial_Psi: np.ndarray, iterations: int, rng: Optional[np.random.Generator] = None) -> Dict: if rng is None: rng = np.random.default_rng(42)

--- Plotting Function (keeps your original layout, minor adjustments) ---

def plot_results(analysis_results: Dict): results = analysis_results["results"] loss_history = analysis_results["loss_history"] fractal_d = analysis_results["fractal_d"] fractal_d_std = analysis_results["fractal_d_std"] log_sizes = analysis_results["log_sizes"] log_counts = analysis_results["log_counts"] autocorr_I1 = analysis_results["autocorr_I1"] loss_autocorr = analysis_results["loss_autocorr"] avg_lyapunov = analysis_results["avg_lyapunov"] lyap_logs = analysis_results["lyap_logs"] recurrence_rate = analysis_results["recurrence_rate"] surrogate_result = analysis_results["surrogate_result"] kde1 = analysis_results["kde1"] kde2 = analysis_results["kde2"] xgrid1 = analysis_results["xgrid1"] xgrid2 = analysis_results["xgrid2"] Z = analysis_results["Z"] eps = analysis_results["eps"]

--- Example usage ---

if name == "main": initial_I = np.array([0.5, 0.3]) initial_Psi = np.array([0.1, -0.1]) iterations = 3000 rng = np.random.default_rng(42)

