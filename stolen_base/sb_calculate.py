import pandas as pd
from math import sqrt
from scipy.stats import norm

from pathlib import Path

from utils import get_catchers_data, get_pitchers_pitch_data, get_player_speed

from pybaseball import statcast_running_splits


def get_pop_time_stats(catcher_id: int, target_base: str) -> tuple:
    """
    Get the distribution, mean, and standard deviation of the pop time for a catcher throwing to a specific base.

    Args:
        catcher_id: ID of the catcher.
        target_base: "second" or "third".

    Returns:
        A tuple containing:
        - DataFrame with pop time data for the catcher.
        - Mean pop time in seconds.
        - Standard deviation of pop time in seconds.
    """
    base_col = f'pop_{target_base.lower()}_sba'

    catcher_df = get_catchers_data(catcher_id)

    mean_pop_time = round(catcher_df[base_col].dropna().mean(), 3)
    std_dev_pop_time = round(catcher_df[base_col].dropna().std(), 3)

    return catcher_df, mean_pop_time, std_dev_pop_time


def get_pitcher_windup_stats(pitcher_id: id) -> tuple:
    """
    Get the distribution, mean, and standard deviation of the windup time for a pitcher.

    Args:
        pitcher_id: ID of the catcher.

    Returns:
        A tuple containing:
        - DataFrame with pitcher windup data.
        - Mean pitcher windup time in seconds.
        - Standard deviation of pitcher windup time in seconds.
    """
    pass


def get_velocity_stats(pitcher_id: id, pitch_type: str) -> tuple:
    """
    Get the distribution, mean, and standard deviation for the velocity of a specific pitch thrown by a pitcher.

    Args:
        pitcher_id: ID of the catcher.
        pitch_type: Abbreviation of the pitch type (e.g., 'FF' for four-seam fastball).

    Returns:
        A tuple containing:
        - DataFrame with pitcher pitch data.
        - Mean pitch velo in mph.
        - Standard deviation of velo in mph.
    """
    pitcher_df = get_pitchers_pitch_data(pitcher_id, pitch_type)

    # Add release release_speed, release_extension - 5 ( air resistance ) for row in pitcher_df
    mean_velocity = round(pitcher_df['release_speed'].dropna().mean(), 3)
    std_dev_velocity = round(pitcher_df['release_speed'].dropna().std(), 3)

    return pitcher_df, mean_velocity, std_dev_velocity


def get_time_to_base_stats(player_id: int, lead_distance: float) -> tuple:
    """
    Get the distribution, mean, and standard deviation for the time to base for a player stealing.

    Args:
        player_id: ID of the player stealing.
        lead_distance: Lead distance in feet.

    Returns:
        A tuple containing:
        - DataFrame with player time to base data.
        - Mean time to base in seconds.
        - Standard deviation of time to base in seconds.
    """
    player_df = get_player_speed(player_id)  # ft/sec

    mean_speed = player_df['sprint_speed'].iloc[0]
    std_dev_speed = player_df['sprint_speed'].iloc[0]

    mean_time_to_base = round(90 - lead_distance / mean_speed, 3)
    std_dev_time_to_base = round(90 - lead_distance / std_dev_speed, 3)

    return None, mean_time_to_base, std_dev_time_to_base


def get_tag_time_stats(fielder_id: int) -> tuple:
    """
    Get the distribution, mean, and standard deviation for the tag time of a fielder.

    Args:
        fielder_id: ID of the catcher.

    Returns:
        A tuple containing:
        - DataFrame with fielder tag time data.
        - Mean tag time in seconds.
        - Standard deviation of tag time in seconds.
    """
    pass


def generate_speed_df(file_path: Path):
    """
    Generate a DataFrame with player speeds from 2008 to today and save it as a CSV.
    """
    # Read the stolen base data
    sb_data = pd.read_csv(file_path)

    # Get unique players
    players = set(sb_data['runner_id'].unique().astype(int))

    # Collect player speeds
    mu_speeds = []
    for player in players:
        player_df = get_player_speed(player)
        mu_speeds.append(round(player_df['sprint_speed'].iloc[0], 3))

    speed_df = pd.DataFrame({
        'player_id': list(players),
        'sprint_speed': mu_speeds
    })

    # Save to CSV
    speed_df.to_csv('/Users/robbykapua/Documents/GitHub/idea-lab/sb_probability/data/player_speed.csv', index=False)


def generate_pop_time_df(file_path: Path):
    """
    Generate a DataFrame with pop times for all catchers from 2008 to today and save it as a CSV.
    """
    # Read the stolen base data
    sb_data = pd.read_csv(file_path)

    # Get unique catchers
    players = set(sb_data['catcher_id'].unique().astype(int))

    # Collect pop times for 3B
    mu_pop_times_3b = []
    for player in players:
        _, time, _ = get_pop_time_stats(player, '3b')
        mu_pop_times_3b.append(round(time, 3))

    pop_time_3b_df = pd.DataFrame({
        'catcher_id': list(players),
        'target_base': ['3B'] * len(players),
        'pop_time': mu_pop_times_3b
    })

    # Collect pop times for 2B
    mu_pop_times_2b = []
    for player in players:
        _, time, _ = get_pop_time_stats(player, '2b')
        mu_pop_times_2b.append(round(time, 3))

    pop_time_2b_df = pd.DataFrame({
        'catcher_id': list(players),
        'target_base': ['2B'] * len(players),
        'pop_time': mu_pop_times_2b
    })

    # Combine both
    pop_time_df = pd.concat([pop_time_3b_df, pop_time_2b_df], ignore_index=True)

    # Save to CSV
    pop_time_df.to_csv('/Users/robbykapua/Documents/GitHub/idea-lab/sb_probability/data/pop_time.csv', index=False)


def generate_splits_df():
    """
    Generate a DataFrame with averaged sprint split times per player from 2008 to today.
    """
    years = list(range(2008, 2025))
    splits = pd.DataFrame()

    for year in years:
        year_splits = statcast_running_splits(year, min_opp=0, raw_splits=True)
        splits = pd.concat([splits, year_splits], ignore_index=True)

    print("Columns:", splits.columns.tolist())  # Debug

    # Select split time columns dynamically
    split_cols = [col for col in splits.columns if col.startswith('seconds_since_hit_')]

    # Group by player_id (and optionally name) and average split columns
    averaged = (
        splits.groupby(['player_id', 'last_name, first_name', 'name_abbrev', 'team_id', 'position_name', 'age', 'bat_side'])[split_cols]
        .mean()
        .reset_index()
    )

    # Save the averaged result
    averaged.to_csv('/Users/robbykapua/Documents/GitHub/idea-lab/sb_probability/data/speed_splits.csv', index=False)



def sb_probability(
        mu_pop_time: float,
        sigma_pop_time: float,
        mu_pitcher_windup: float,
        sigma_pitcher_windup: float,
        mu_time_to_plate: float,
        sigma_time_to_plate: float,
        mu_time_to_base: float,
        sigma_time_to_base: float,
        mu_tag_time: float,
        sigma_tag_time: float
) -> float:
    """
    Calculate the probability of a successful stolen base attempt. Given
    the mean and standard deviation of the pop time, pitcher windup,
    velocity, time to base, and tag time.

    Args:
        mu_pop_time: Mean pop time.
        sigma_pop_time: Standard deviation of pop time.
        mu_pitcher_windup: Mean pitcher windup time.
        sigma_pitcher_windup: Standard deviation of pitcher windup time.
        mu_time_to_plate: Mean time to plate given the pitch type of a pitcher
        sigma_time_to_plate: Standard deviation of time to plate given the pitch type of a pitcher
        mu_time_to_base: Mean time to base given the lead distance.
        sigma_time_to_base: Standard deviation of time to base.
        mu_tag_time: Mean tag time of the fielder.
        sigma_tag_time: Standard deviation of tag time.

    Returns:
        Probability of a successful stolen base attempt.
    """

    # Calculate the mean and standard deviation of the defence time
    m_defence_time = mu_pitcher_windup + mu_time_to_plate + mu_pop_time + mu_tag_time
    sd_defence_time = sqrt(sigma_pitcher_windup ** 2 + sigma_time_to_plate ** 2 + sigma_pop_time ** 2 + sigma_tag_time ** 2)

    # Calculate chances of a successful stolen base
    z = (m_defence_time - mu_time_to_base) / sqrt(sd_defence_time ** 2 + sigma_time_to_base ** 2)
    p = norm.cdf(z)

    return p


if __name__ == '__main__':
    file = Path('/Users/robbykapua/Documents/GitHub/idea-lab/sb_probability/data/sb_data_complete/sb_data_2016-2025.csv')
    # generate_pop_time_df(file)
    # generate_speed_df(file)
    generate_splits_df()


