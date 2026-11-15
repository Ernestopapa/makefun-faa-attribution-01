import json
import os
import math
import sys

# Constants - to be tuned
SHRINK = 0
SIGMA_FLOOR = 0.0015
SIGMA_CAP = 0.02
K = 2.0
W = 0.03
SIGMA_JUMP = 0.05

def clamp(v, lo, hi):
    return max(lo, min(v, hi))

def normal_cdf(x, mu, sigma):
    if sigma <= 0:
        return 1.0 if x >= mu else 0.0
    return 0.5 * (1 + math.erf((x - mu) / (sigma * math.sqrt(2))))

def get_quantile(tau, mu, sigma, sigma_jump, w):
    # Mixture CDF(v) = (1-w) * N_cdf(v, mu, sigma) + w * N_cdf(v, mu, sigma_jump)
    
    # Bracket
    # Use a large enough bracket
    s = max(sigma, sigma_jump)
    lo = mu - 6 * s * math.sqrt(240)
    hi = mu + 6 * s * math.sqrt(240)
    
    for _ in range(40):
        mid = (lo + hi) / 2
        cdf = (1 - w) * normal_cdf(mid, mu, sigma) + w * normal_cdf(mid, mu, sigma_jump)
        if cdf < tau:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2

def solve_case(case_data):
    forecasts = []
    
    for market in case_data['markets']:
        prices = market['prices']
        x = prices[-1]
        
        # Drift
        # 1-min returns
        returns = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
        winsorized_returns = [clamp(r, -0.05, 0.05) for r in returns]
        
        # slope60/240
        def get_slope(series):
            if len(series) < 2: return 0.0
            n = len(series)
            t = list(range(n))
            # LS slope
            mean_t = sum(t) / n
            mean_p = sum(series) / n
            num = sum((t[i] - mean_t) * (series[i] - mean_p) for i in range(n))
            den = sum((t[i] - mean_t)**2 for i in range(n))
            if den == 0: return 0.0
            return num / den
            
        slope60 = get_slope(prices[-60:])
        slope240 = get_slope(prices[-240:])
        
        # EWMA
        ewma = 0.0
        if winsorized_returns:
            weight = 0.1
            current_ewma = 0.0
            # EWMA(0.1) over last 240
            recent_returns = winsorized_returns[-240:]
            # Recent weight highest? "decay 0.1 over the last 240 returns (most recent weight highest)"
            # Usually EWMA is recursive: y_t = (1-a) * y_{t-1} + a * x_t.
            # "Most recent weight highest" suggests a different direction, or just standard EWMA
            # Let's assume standard EWMA for now.
            for r in recent_returns:
                current_ewma = (1 - weight) * current_ewma + weight * r
            ewma = current_ewma
            
        drift_per_min = SHRINK * (0.4 * slope60 + 0.4 * slope240 + 0.2 * ewma)
        
        # Sigma
        # mean(|d[i]|) over last 720
        recent_d = [abs(r) for r in returns[-720:]]
        sigma = 1.25 * (sum(recent_d) / len(recent_d) if recent_d else 0.0)
        
        # Jump regime
        jump_detected = any(abs(r) >= 0.04 for r in returns[-120:])
        if jump_detected:
            sigma *= K
        
        sigma = clamp(sigma, SIGMA_FLOOR, SIGMA_CAP)
        if jump_detected:
            sigma = min(sigma, 0.03)
            
        # Forecast
        market_forecasts = []
        for h in range(1, 241):
            median_h = clamp(x + drift_per_min * h, 0, 1)
            
            # Mixture Quantiles
            sigma_h = sigma * math.sqrt(h)
            sigma_jump_h = SIGMA_JUMP * math.sqrt(h)
            
            row = []
            for tau in [0.05, 0.25, 0.5, 0.75, 0.95]:
                # Fallback to normal if bisection is potentially risky, 
                # but design says use bisection first.
                try:
                    q = get_quantile(tau, median_h, sigma_h, sigma_jump_h, W)
                except:
                    # Baseline fallback: median(h) + z_tau * sigma * sqrt(h)
                    # z: (-1.644854, -0.674490, 0, 0.674490, 1.644854)
                    z_map = {0.05: -1.644854, 0.25: -0.674490, 0.5: 0.0, 0.75: 0.674490, 0.95: 1.644854}
                    q = median_h + z_map[tau] * sigma_h
                
                row.append(clamp(round(q, 6), 0, 1))
            
            # Non-decreasing
            row.sort()
            market_forecasts.append(row)
        
        forecasts.append({"id": market['id'], "q": market_forecasts})
        
    return {"forecasts": forecasts}

def main():
    input_dir = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
    output_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    files = [f for f in os.listdir(input_dir) if f.endswith(".in")]
    files.sort()
    
    for filename in files:
        with open(os.path.join(input_dir, filename), "r") as f:
            case_data = json.load(f)
            
        forecasts = solve_case(case_data)
        
        output_filename = filename.replace(".in", ".out")
        with open(os.path.join(output_dir, output_filename), "w") as f:
            json.dump(forecasts, f)

if __name__ == "__main__":
    main()
