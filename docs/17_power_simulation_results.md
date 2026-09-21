# Power simulation — development benchmark

Статус: synthetic development benchmark. Эти результаты не являются real-world performance.

## Protocol

- baseline: 60 synthetic Gaussian residuals, seed 20260920;
- bootstrap null-path calibration: 5000 runs;
- CUSUM drift: 0.5;
- warmup: 12;
- target path-level FPR: 0.10;
- calibrated threshold: 12.0;
- measured null path-level FPR: 0.0992;
- power runs per cell: 5000;
- detection window: shock start through duration + 2 periods;
- target power: 0.80.

Path-level FPR здесь не равен operational metric false alarms per municipality-year. После появления реального Predictive Layer потребуется отдельная calibration на реальном development period.

## Results

| Shock, sigma | 1 period | 2 periods | 3 periods | 6 periods | Min duration for power >= 0.80 |
|---:|---:|---:|---:|---:|---:|
| 0.5 | 0.010 | 0.012 | 0.019 | 0.037 | >6 |
| 1.0 | 0.013 | 0.020 | 0.033 | 0.090 | >6 |
| 1.5 | 0.012 | 0.025 | 0.051 | 0.216 | >6 |
| 2.0 | 0.014 | 0.046 | 0.097 | 0.424 | >6 |
| 2.5 | 0.021 | 0.068 | 0.161 | 0.628 | >6 |
| 3.0 | 0.029 | 0.095 | 0.258 | 0.821 | 6 |
| 4.0 | 0.045 | 0.201 | 0.516 | 0.955 | 6 |

## Interpretation

При жесткой calibration до FPR≈0.10 текущий CUSUM development setup надежно обнаруживает только крупные и устойчивые injected shifts: в этом benchmark power >=0.80 достигается при 3–4 sigma и длительности 6 периодов.

Это полезный отрицательный результат: threshold нельзя выбирать только по sensitivity. Нужно одновременно контролировать false alarms и detection power.

Следующий этап — повторить тот же protocol на реальных residuals Predictive Layer и отдельно для combined detector CUSUM + PELT.
