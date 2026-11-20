"""GTA VI trophy rarity forecast: per-trophy logit trend with random-walk spread.

Each trophy's earn rate is tracked in logit space, where a straight line
against log-time captures steady growth while a flat history collapses back
to simply repeating the last observed rate. The spread around the median
combines a random-walk term that grows with the horizon, the scatter left
over by the fitted line, and the uncertainty of the fitted slope carried
forward to the target. Nothing here touches the network, the clock, or any
source of randomness: the same case file always yields the same bytes.
"""

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
IN_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

# Log-time is measured from the start of launch day, 2026-11-19 UTC.
EPOCH = datetime(2026, 11, 19, 0, 0, 0, tzinfo=timezone.utc)

# Normal quantiles for the five scored levels, in level order.
NORMAL_Q = [-1.645, -0.674, 0.0, 0.674, 1.645]

# Bounds applied to every rate before a logit is taken, and to every
# forecast rate before it is written out.
LOW_RATE = 0.01
HIGH_RATE = 99.99

# Random-walk spread per square-root day, in logit units.
WALK = 0.5
# Smallest spread allowed, so the five quantiles never collapse onto one value.
MIN_SPREAD = 0.05
# Widest logit move the fitted line may claim away from the last read.
MAX_MOVE = 3.0


def _clamp_rate(pct):
    if pct < LOW_RATE:
        return LOW_RATE
    if pct > HIGH_RATE:
        return HIGH_RATE
    return pct


def _logit(pct):
    p = _clamp_rate(pct) / 100.0
    return math.log(p / (1.0 - p))


def _inv_logit(logit_value):
    return 100.0 / (1.0 + math.exp(-logit_value))


def _round4(value):
    """Round to 4 decimals, halves away from zero, JavaScript-style.

    Every value here is positive, so adding half a unit in the last place
    and flooring gives the same result as Math.round(x * 10000) / 10000.
    Whole numbers are returned as ints so the JSON stays compact.
    """
    stepped = math.floor(value * 10000.0 + 0.5) / 10000.0
    return int(stepped) if stepped == int(stepped) else stepped


def _read_time(text):
    """Parse an ISO 8601 timestamp, accepting a trailing Z for UTC."""
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _log_hours(moment):
    """Log-time feature: ln(1 + hours from launch-day midnight to `moment`)."""
    hours = (moment - EPOCH).total_seconds() / 3600.0
    return math.log(max(1.0 + hours, 1e-6))


def _least_squares(xs, ys):
    """Fit y ~ a + b*x by least squares; return (a, b, resid_var, slope_se).

    resid_var is the mean squared residual; slope_se is the standard error
    of the slope implied by that residual variance. Callers only use these
    when the x values actually vary.
    """
    n = len(xs)
    x_bar = sum(xs) / n
    y_bar = sum(ys) / n
    sxx = sum((x - x_bar) ** 2 for x in xs)
    sxy = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = y_bar - slope * x_bar
    resid_var = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys)) / n
    slope_se = math.sqrt(resid_var / sxx) if sxx > 0.0 else 0.0
    return intercept, slope, resid_var, slope_se


def _forecast_trophy(points, last_logit, target_x, horizon_days):
    """Forecast one trophy from its (log-time, logit-rate) history points.

    `points` is the trophy's full history, oldest first; `last_logit` is the
    logit of its most recent rate. With too little history, or a history
    that never moves, the median is the last rate and the spread is the
    plain random-walk term.
    """
    points = sorted(points)
    walk_var = (WALK * math.sqrt(horizon_days)) ** 2
    if len(points) < 3:
        return last_logit, math.sqrt(walk_var)

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    if max(xs) == min(xs) or max(ys) == min(ys):
        return last_logit, math.sqrt(walk_var)

    intercept, slope, resid_var, slope_se = _least_squares(xs, ys)
    median_logit = intercept + slope * target_x
    move = median_logit - last_logit
    if move > MAX_MOVE:
        median_logit = last_logit + MAX_MOVE
    elif move < -MAX_MOVE:
        median_logit = last_logit - MAX_MOVE
    x_bar = sum(xs) / len(xs)
    spread_sq = walk_var + resid_var + (slope_se * (target_x - x_bar)) ** 2
    spread = max(math.sqrt(spread_sq), MIN_SPREAD)
    return median_logit, spread


def _forecast_case(case):
    trophies = case["trophies"]
    history = case["history"]
    if not history:
        raise ValueError("case has no history reads")
    target_x = _log_hours(_read_time(case["target"]))
    horizon_days = case["horizon_minutes"] / 1440.0

    rows = []
    for pos, trophy in enumerate(trophies):
        points = []
        last_rate = None
        for read in history:
            rate = read["rates"][pos]
            if rate is None:
                continue
            points.append((_log_hours(_read_time(read["at"])), _logit(rate)))
            last_rate = rate
        if last_rate is None:
            last_rate = LOW_RATE
        last_logit = _logit(last_rate)
        median_logit, spread = _forecast_trophy(points, last_logit, target_x, horizon_days)
        quantiles = []
        previous = None
        for z in NORMAL_Q:
            value = _round4(_clamp_rate(_inv_logit(median_logit + z * spread)))
            if previous is not None and value < previous:
                value = previous
            quantiles.append(value)
            previous = value
        rows.append({"id": trophy["id"], "q": quantiles})
    return {"trophies": rows}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(IN_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = _forecast_case(case)
        text = json.dumps(forecast, separators=(",", ":")) + "\n"
        (OUT_DIR / (path.stem + ".out")).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
