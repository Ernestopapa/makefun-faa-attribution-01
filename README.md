# Polymarket Yes Price Forecaster

This program forecasts Polymarket Yes prices for the FAA attribution family.

## Method
The forecaster uses a jump mixture model:
1.  **Drift:** Persistence model (SHRINK=0).
2.  **Sigma:** Robust recent mean absolute move (1.25 * mean(|d[i]|)), with a jump regime detection (any |d| >= 0.04 in the last 120 minutes multiplies sigma by 2.0).
3.  **Quantiles:** Jump mixture model combining two normal distributions based on the estimated sigma and a jump sigma (0.05).
4.  **Tuning:** Walk-forward validation on practice cases p00-p05.

## Winning Constants
- SHRINK: 0
- SIGMA_FLOOR: 0.0015
- SIGMA_CAP: 0.02
- K: 2.0
- W: 0.03
- SIGMA_JUMP: 0.05

## Walk-Forward Loss
- Model loss: 2.1905
- Baseline loss: 2.2428

## Usage
`mkdir -p /output && MAKEFUN_INPUT_DIR=/input MAKEFUN_OUTPUT_DIR=/output python3 main.py`

## Contract
- **I/O:** Reads from `$MAKEFUN_INPUT_DIR` (default `/input`) and writes to `$MAKEFUN_OUTPUT_DIR` (default `/output`).
- **Limits:** Runs in < 8s per case.
- **Determinism:** BYTE-IDENTICAL output for the same case.
