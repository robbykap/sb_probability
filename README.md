# [Stolen Base Scraper](sb_data_scrapper.py)

This is a web scraper that extracts the following data from the website [Basestealing Run Value Leaderboard](https://baseballsavant.mlb.com/leaderboard/basestealing-run-value):

## Data Collected

The scraper collects data on stolen base attempts, including the following fields:

- `date`  
- `cather_name` 
- `pitcher_name` 
- `runner_name` 
- `batter_name`
- `fielder_name`
- `target_base`  
- `result`
  - **`SB` – Stolen Base**: Runner successfully advances to the next base during the pitch without being tagged out.
  - **`CS` – Caught Stealing**: Runner is thrown out while attempting to steal a base.
  - **`BK` – Balk**: Illegal pitching motion; all runners advance one base.
  - **`PK` – Pickoff**: Pitcher or catcher attempts to throw out a runner leading off a base.
  - **`FB` – Picked Off and Caught Stealing**: Runner is picked off but attempts to advance and is thrown out; ruled as a caught stealing.
- `runner_stealing_runs`  
- `lead_distance_gained`
- `at_pitchers_first_move`  
- `at_pitch_release`  
- `ball_count`
- `strike_count`
- `pitch_type`  
  - **`FF` – Four-Seam Fastball**: A straight, high-velocity pitch with backspin; typically the fastest pitch.
  - **`SL` – Slider**: A sharp breaking ball with lateral and downward movement; faster than a curveball.
  - **`CH` – Changeup**: A slower pitch thrown with fastball arm speed to disrupt timing.
  - **`CU` – Curveball**: A slow, looping pitch with significant downward break due to topspin.
  - **`FS` – Splitter (Split-Finger Fastball)**: Drops sharply late; thrown with fingers split on the seams.
  - **`FC` – Cutter (Cut Fastball)**: A fastball that breaks slightly glove-side at the last moment.
  - **`SI` – Sinker**: Has arm-side run and downward movement; designed to induce ground balls.
  - **`ST` – Sweeper**: A wide-breaking slider with more horizontal movement and less drop.
  - **`PO` – Pitch Out**: A purposeful ball thrown outside the strike zone, often to defend a steal.
  - **`KC` – Knuckle Curve**: A curveball thrown with a spiked or knuckle grip for tight spin and drop.
  - **`SV` – Slurve**: A hybrid between slider and curveball; sweeping break with some drop.
  - **`KN` – Knuckleball**: A slow pitch with little to no spin, causing erratic movement.
  - **`FO` – Forkball**: Similar to a splitter but slower and with a more exaggerated drop.
  - **`SC` – Screwball**: Rare pitch that breaks opposite a slider (toward arm side).
  - **`CS` – Called Strike**: Sometimes used as a tag for a pitch resulting in a called strike; not a distinct pitch type.
  - **`EP` – Eephus**: A very slow, high-arcing pitch thrown for surprise or deception.
- `velo`
- `call`
  - `ball` - Called Ball
  - `strike` - Called Strike
  - `unknown` - Not given or not applicable
- `matchup`
- `video_link`

## Goal 
The goal of this project is to successfully predict if a player will be successful in stealing a base or not.
We will be using a Bayesian model to predict this outcome.