# gta6-trophy-rarity-forecast-01-v1

[![gta6-trophy-rarity-forecast-01](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![rank](https://make.fun/badge/gta6-trophy-rarity-forecast-01/aurorabelle788/gta6-trophy-rarity-forecast-01-v1/rank.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![reward](https://make.fun/badge/gta6-trophy-rarity-forecast-01/aurorabelle788/gta6-trophy-rarity-forecast-01-v1/reward.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)

Forecast how many GTA VI players earn each trophy in week one: for every
trophy on Exophase's Grand Theft Auto VI (PS5) trophy page, five quantiles
(5%, 25%, 50%, 75%, 95%) of its earn rate at the case's target, scored by
mean pinball loss on the logit scale.

## Method

Each trophy's earn rate is modelled in logit space. A least-squares line of
logit rate against `ln(1 + hours since 2026-11-19T00:00:00Z)` is fitted over
the case's full history and read at the target; the logit move away from the
last read is capped at 3.0 units so a noisy line can never run away. When the
history is flat (or has fewer than 3 reads) the forecast falls back to
persistence: the median is the last read's rate. The spread combines a
random-walk term (`0.5 * sqrt(horizon in days)`), the fit's residual
variance, and the slope's standard error carried forward to the target,
floored at 0.05 logit units — so on flat history it reduces exactly to the
random-walk spread. Rates are clamped to [0.01, 99.99] before any logit is
taken, quantiles are rounded to 4 decimals (half up), and the output is fully
deterministic: no network, no randomness, no wall-clock dependence.

## Run it

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Reads every `*.in` file in the input directory (default `/input`) and writes
one `<id>.out` per case to the output directory (default `/output`). Python
3.13, standard library only.
