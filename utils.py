from pybaseball import playerid_lookup, statcast_sprint_speed, statcast_catcher_poptime, statcast_pitcher_arsenal_stats, playerid_reverse_lookup
import pickle
import pandas as pd


# Distances (in)
TARGETS = {
    "second": {
        "from_first": 1080,
        "from_home": 1527.375
    },
    "third": {
        "from_second": 1080,
        "from_home": 1080
    },
}
MOUND_HOME = 726


# Calculate how fast a runner needs to be to steal a base
def calcu_required_speed(
        target_base:str,
        runner_lead:float,
        runner_speed:float,
        pitcher_velo:float,
        catcher_pop:float,
) -> float:
    """
    Calculate how fast a runner needs to be to steal a given base.

    Args:
        target_base: str - The target base to steal, either "second" or "third".
        runner_lead: float - The distance the runner is leading off the base (in inches).
        runner_speed: float - The speed of the runner (in inches per second).
        pitcher_velo: float - The speed of the pitcher's throw to home plate (in inches per second).
        catcher_pop: float - The time it takes for the catcher to pop up and throw (in seconds).

    Returns: required_speed: float - The required speed of the runner to steal the base.

    """

    # Calculate the distance to the target base
    if target_base == "second":
        target_distance = TARGETS["second"]["from_first"] - runner_lead
    elif target_base == "third":
        target_distance = TARGETS["third"]["from_second"] - runner_lead
    else:
        raise ValueError(f"Invalid target base: {target_base}, must be one of {list(TARGETS.keys())}")

    # Calculate the time it takes the ball to reach the target base
    time_home = MOUND_HOME / pitcher_velo

    time_ball = time_home + catcher_pop

    # Calculate the time it takes the runner to reach the target base
    time_runner = target_distance / runner_speed

    # Calculate the required speed
    required_speed = target_distance / (time_ball - time_runner)

    return required_speed


def lookup_player(player_name: str) -> str:
    """
    Lookup player ID using playerid_lookup from pybaseball.
    Args:
        player_name: str - The name of the player to lookup.

    Returns:
        str - The player ID.
    """
    first, last = player_name.split('|')
    try:
        player_data = playerid_lookup(last=last.strip(), first=first.strip())
        if not player_data.empty:
            return player_data.iloc[0]['key_mlbam']
        else:
            raise ValueError(f"Player {player_name} not found.")
    except Exception as e:
        raise ValueError(f"Error looking up player {player_name}: {e}")


def update_batters(file_path: str, player_info: dict = None):
    """
    Update the batters column with player IDs.
    Args:
        file_path: str - The path to the batters file.
    """

    # Load the csv file into a DataFrame
    df = pd.read_csv(file_path)

    # Get all unique batter names
    unique_batters = df['batter_name'].unique()

    # Create a dictionary to store player IDs
    player_ids = {}
    failed = []
    for batter in unique_batters:
        try:
            player_id = lookup_player(batter)
            player_ids[batter] = player_id
        except ValueError as _:
            try:
                first, last = batter.split('|')
                batter_name = f"{first.strip()} {last.strip()}"
            except ValueError as _:
                batter_name = batter
            player_ids[batter] = player_info.get(f"{batter_name}", f"{batter}")
    print('Failed to lookup the following players:')
    for player in failed:
        try:
            int(player)
        except ValueError as _:
            print(player)


    # Replace batter names with player IDs in the DataFrame
    df['batter_name'] = df['batter_name'].replace(player_ids)

    # Save the updated DataFrame
    df.to_csv(file_path, index=False)


def update_description(file_path: str):
    """
    Update the description column to simply include if it was a ball or strike
    Args:
        file_path: str - The path to the description file.
    """

    # Go through each row and update the description
    df = pd.read_csv(file_path)
    for index, row in df.iterrows():
        try:
            if "ball" in row['description'].lower():
                df.at[index, 'description'] = "ball"
            elif "strike" in row['description'].lower():
                df.at[index, 'description'] = "strike"
            else:
                df.at[index, 'description'] = "unknown"
        except AttributeError as e:
            print(f"Error processing row {index}: {e}")
            df.at[index, 'description'] = "unknown"

    # rename the column to "call"
    df.rename(columns={'description': 'call'}, inplace=True)

    # Save the updated DataFrame
    df.to_csv(file_path, index=False)


def remove_duplicates(file_path: str):
    """
    Remove duplicate lines from a csv file while preserving the header.
    Args:
        file_path: str - The path to the file to remove duplicates from.
    """
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Separate the header and the rest of the lines
    header = lines[0]
    unique_lines = list(set(lines[1:]))  # Exclude the header from deduplication

    # Write back the header and unique lines
    with open(file_path, 'w') as file:
        file.write(header)
        file.writelines(unique_lines)


def remove_video_link_col(file_path: str):
    """
    Remove the video link column from a csv file.
    Args:
        file_path: str - The path to the file to remove duplicates from.
    """
    df = pd.read_csv(file_path)
    df.drop(columns=['video_link'], inplace=True)
    df.to_csv(file_path, index=False)


def pkl_content(file_path: str) -> int:
    """
    See if the pkl file is empty or not.
    Then return the content if not empty.

    Args:
        file_path:

    Returns: str | int
        The content of the pkl file if not empty.
    """

    try:
        with open(file_path, 'rb') as file:
            content = pickle.load(file)
            if content:
                return content
            else:
                raise ValueError("The pkl file is empty.")
    except Exception as e:
        raise ValueError(f"Error reading the pkl file: {e}")


if __name__ == '__main__':
    file_path = "sb_data_2023-2025.csv"
