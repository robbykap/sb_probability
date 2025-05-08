# Stolen Base Scraper

This is a web scraper that extracts the following data from the website [Basestealing Run Value Leaderboard](https://baseballsavant.mlb.com/leaderboard/basestealing-run-value):


## Data Collected

- `player` - person making attempt
- `pitcher` 
- `catcher` 
- `fielder` 
- `batter`  
- `target` - target of the steal
- `result` - result of the steal attempt
- `lead_dist_gained` - distance in feet a runner has advanced from the start of delivery to pitch release
- `at_first_move` - distance a runner has advanced from the start of delivery to pitch release 
- `at_release` - distance a runner has advanced from the start of delivery to pitch release 
- `pitch_type` - type of pitch thrown
  - `FF` - Four-seam fastball
  - `SL` - Slider
  - `CH` - Changeup
  - `CU` - Curveball
  - `FS` - Splitter
  - `FC` - Cutter
  - `SI` - Sinker
  - `ST` - Sweeper
- `strike_count` - number of strikes on the batter
- `ball_count` - number of balls on the batter
- `location` - location of the pitch

## Goal 
The goal of this project is to successfully predict if a player will be successful in stealing a base or not.
We will be using a Bayesian model to predict this outcome.