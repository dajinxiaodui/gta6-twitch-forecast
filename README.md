# gta6-twitch-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/dajinxiaodui/gta6-twitch-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/dajinxiaodui/gta6-twitch-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

A launch-day Twitch viewership forecaster for Grand Theft Auto VI. Given
everything recorded up to the end of release day's first hour (2026-11-19,
UTC), it forecasts the concurrent viewers of the "Grand Theft Auto VI"
Twitch category for each of hours 2 to 24, as five quantiles per hour.

Method: the case file carries 42 past big game launches with their full
hourly curves. For each comparable, the forecaster expresses its release
day as log-ratios to its own first hour, pools those ratios hour by hour
(weighted toward launches of a similar scale, smoothed across neighbouring
hours), and reads the five quantiles straight off the pooled distribution,
rescaled by this case's first-hour print. No network, no randomness:
Python 3 standard library only, byte-identical output on every run.

## Run it

```sh
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
# reads every *.in case in the input dir, writes <id>.out per case
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=qtgxrqfw&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
