import pandas as pd
from math import sqrt
from scipy.stats import norm

from utils import get_catchers_data, get_pitchers_pitch_data, get_player_speed


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
    with open('sb_data_2023-2025.csv', 'r') as f:
        sb_data = pd.read_csv(f)

    example = sb_data.iloc[0]

    pop_time_df, mu_pop_time, sigma_pop_time = get_pop_time_stats(663743, "2B")

    # pitcher_df, mu_pitcher_windup, sigma_pitcher_windup = get_pitcher_windup_stats(example['pitcher_name'])
    pitcher_windup_df, mu_pitcher_windup, sigma_pitcher_windup = None, 1.5, 0.2  # Placeholder values for windup stats

    velocity_df, mu_velocity, sigma_velocity = get_velocity_stats(645261, "SI")

    time_to_base_df, mu_time_to_base, sigma_time_to_base = get_time_to_base_stats(665833, 10.9)

    # tag_time_df, mu_tag_time, sigma_tag_time = get_tag_time_stats(example['fielder_name'])
    tag_time_df, mu_tag_time, sigma_tag_time = None, 0.3, 0.1

    probability = sb_probability(
        mu_pop_time, sigma_pop_time,
        mu_pitcher_windup, sigma_pitcher_windup,
        mu_velocity, sigma_velocity,
        mu_time_to_base, sigma_time_to_base,
        mu_tag_time, sigma_tag_time
    )
    print(f"Probability of successful stolen base: {probability:.2f}")


