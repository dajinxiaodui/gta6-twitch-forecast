#!/usr/bin/env python3
"""Launch-day Twitch viewership forecaster (make.fun gta6-twitch-ccu-forecast-01).

Reads every case file (*.in) in the input directory and writes one forecast
file (<id>.out) per case: for each of hours 2..24 of the release day, five
quantiles of that hour's concurrent-viewer count in the game's Twitch
category, at levels 0.05 / 0.25 / 0.5 / 0.75 / 0.95.

Method
------
A launch day has a characteristic shape: a first hour carried by the
earliest time zones, a build as Europe and then the Americas unlock, an
evening peak, and a long decay. Rather than guessing that shape, the
forecaster measures it from the case's own comparables — dozens of past
big launches with full hourly curves. Each comparable's release day is
expressed as log-ratios to its own first hour; the ratios are pooled hour
by hour, weighted toward launches whose first hour was of a similar scale
to this case's, and smoothed across neighbouring hours. The five
quantiles of the pooled distribution, rescaled by this case's first-hour
print, are the forecast. Where the pool is too thin the program falls
back to the house baseline's shape (flat median, widening spread).

Standard library only, no network, no randomness: the same input always
produces byte-identical output, well inside the 8-second limit.
"""

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

LEVELS = (0.05, 0.25, 0.5, 0.75, 0.95)
# Standard-normal quantiles at LEVELS, for the baseline fallback.
Z = (-1.6448536269514722, -0.6744897501960817, 0.0, 0.6744897501960817, 1.6448536269514722)
HOURS = range(2, 25)


def parse_ts(text):
    """ISO-8601 UTC timestamp -> epoch seconds (float)."""
    return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def hour_of(day_start_epoch, ts_epoch):
    """1-based hour of the release day containing ts_epoch."""
    return int((ts_epoch - day_start_epoch) // 3600) + 1


def first_hour_print(case):
    """The case's hour-1 viewer count, with graceful fallbacks."""
    known = case.get("known") or []
    for row in known:
        if row.get("hour") == 1 and row.get("viewers"):
            return float(row["viewers"])
    hourly = case.get("history_hourly") or []
    if hourly:
        return max(1.0, float(hourly[-1].get("viewers") or 1))
    history = case.get("history") or []
    if history:
        return max(1.0, float(history[-1].get("viewers") or 1))
    return 1.0


def unlock_factor(comp):
    """How comparable a launch's day shape is to a rolling midnight unlock.

    This case's game unlocks at midnight local time, country by country,
    so its first UTC hour already holds the earliest time zones' players
    and the Americas arrive hours later. A comparable that unlocked the
    same way traces the same kind of day. One that unlocked everywhere at
    a single UTC instant spent its first hours pre-unlock and traces a
    different day entirely, so it counts for much less.
    """
    text = (comp.get("unlock") or "").lower()
    if "midnight local" in text or "rolling" in text:
        return 1.0
    if "simultaneous" in text or "global unlock" in text:
        return 0.12
    return 0.5


def comparable_curves(case):
    """Each comparable launch's release day as {hour: log(viewers / hour-1)}.

    Returns a list of (hour1_viewers, unlock_factor, {hour: log_ratio})
    for comparables whose release day is recorded well enough to teach
    the shape: a real first hour and at least half of hours 2..24
    present. The case game's own category history is skipped: the day it
    records is a trailer premiere, not a launch.
    """
    own_name = (case.get("game") or {}).get("name")
    curves = []
    for comp in case.get("comparables") or []:
        if own_name and comp.get("name") == own_name:
            continue
        try:
            start = parse_ts(comp["day_start"])
        except (KeyError, ValueError):
            continue
        by_hour = {}
        for point in comp.get("hourly") or []:
            try:
                h = hour_of(start, parse_ts(point["from"]))
                v = float(point.get("viewers") or 0)
            except (KeyError, ValueError, TypeError):
                continue
            if 1 <= h <= 24 and v > 0:
                by_hour[h] = v
        c1 = by_hour.get(1)
        if not c1 or c1 <= 0:
            continue
        ratios = {h: math.log(v / c1) for h, v in by_hour.items() if h >= 2}
        if len(ratios) < 12:
            continue
        curves.append((c1, unlock_factor(comp), ratios))
    return curves


def scale_weight(c1, p):
    """How much a comparable counts: launches of a similar scale count more."""
    if p <= 0 or c1 <= 0:
        return 1.0
    return 1.0 / (1.0 + abs(math.log10(c1) - math.log10(p)))


def weighted_quantile(pairs, tau):
    """tau-quantile of (value, weight) pairs, linearly interpolated."""
    if not pairs:
        return None
    pairs = sorted(pairs)
    total = sum(w for _, w in pairs)
    if total <= 0:
        return pairs[len(pairs) // 2][0]
    target = tau * total
    acc = 0.0
    prev_value, prev_acc = pairs[0][0], 0.0
    for value, w in pairs:
        acc += w
        if acc >= target:
            if acc == prev_acc:
                return value
            frac = (target - prev_acc) / (acc - prev_acc)
            return prev_value + frac * (value - prev_value)
        prev_value, prev_acc = value, acc
    return pairs[-1][0]


def pooled_log_quantiles(curves, p, hour):
    """The five log-ratio quantiles for one hour, pooled and smoothed.

    Neighbouring hours lend their samples at reduced weight: with only a
    few dozen comparables, a single hour's tail quantiles are noisy, and
    the true curve is smooth, so borrowing from +-1 hour is a fair trade.
    """
    by_level = []
    for tau in LEVELS:
        pairs = []
        for c1, ufactor, ratios in curves:
            w = scale_weight(c1, p) * ufactor
            for dh, factor in ((-1, 0.25), (0, 0.5), (1, 0.25)):
                if hour + dh in ratios:
                    pairs.append((ratios[hour + dh], w * factor))
        by_level.append(weighted_quantile(pairs, tau) if len(pairs) >= 6 else None)
    return by_level


def baseline_quantiles(p, hour):
    """The house baseline's row: flat median, spread 0.15 * sqrt(hour - 1)."""
    spread = 0.15 * math.sqrt(hour - 1)
    return [p * math.exp(z * spread) for z in Z]


def forecast(case):
    p = first_hour_print(case)
    curves = comparable_curves(case)
    rows = []
    for hour in HOURS:
        log_qs = pooled_log_quantiles(curves, p, hour) if curves else [None] * 5
        if any(q is None for q in log_qs):
            rows.append({"hour": hour, "q": baseline_quantiles(p, hour)})
            continue
        qs = []
        prev = 1.0
        for log_q in log_qs:
            value = p * math.exp(log_q)
            value = min(1_000_000_000.0, max(1.0, value))
            value = max(value, prev)  # quantiles never decrease
            qs.append(round(value, 2))
            prev = value
        rows.append({"hour": hour, "q": qs})
    return {"hours": rows}


def main():
    in_dir = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    for in_file in sorted(in_dir.glob("*.in")):
        case = json.loads(in_file.read_text(encoding="utf-8"))
        result = forecast(case)
        out_file = out_dir / (in_file.stem + ".out")
        out_file.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
