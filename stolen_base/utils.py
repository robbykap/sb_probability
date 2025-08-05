import csv
import json
import pickle
import chardet
import pandas as pd
from datetime import datetime

from tqdm import tqdm

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from sb_data_scrapper import init_driver

from pybaseball import (playerid_lookup, playerid_reverse_lookup,
                        statcast_catcher_poptime,
                        statcast_pitcher,
                        statcast_sprint_speed,
                        statcast_running_splits
                        )


# ---------------------------------------------------------------------------- #
#                             Generate Player Data                             #
# ---------------------------------------------------------------------------- #


def generate_player_data(file_path: str):
    ids = list(range(1, 900000))
    players_df = playerid_reverse_lookup(ids, key_type='mlbam')

    players_df = players_df.dropna(subset=['name_first', 'name_last'])

    players_df['full_name'] = players_df['name_first'] + ' ' + players_df['name_last']

    players_df = players_df[['key_mlbam', 'name_first', 'name_last', 'full_name']]

    players_df.to_csv(file_path, index=False)


# ---------------------------------------------------------------------------- #
#                             Required Runner Speed                            #
# ---------------------------------------------------------------------------- #


# Distances (in inches)
TARGETS = {
    "second": {"from_first": 1080, "from_home": 1527.375},
    "third": {"from_second": 1080, "from_home": 1080},
}
MOUND_HOME = 726  # Distance from mound to home plate in inches


def calculate_required_speed(
    target_base: str,
    runner_lead: float,
    runner_speed: float,
    pitcher_velo: float,
    catcher_pop: float,
) -> float:
    """
    Calculate the required speed for a runner to successfully steal a base.

    Args:
        target_base: "second" or "third".
        runner_lead: Lead distance in inches.
        runner_speed: Runner speed in inches/sec.
        pitcher_velo: Pitch velocity in inches/sec.
        catcher_pop: Catcher pop time in seconds.

    Returns:
        Required runner speed in inches/sec.
    """
    if target_base not in TARGETS:
        raise ValueError(f"Invalid target base: {target_base}")

    target_distance = TARGETS[target_base][f"from_{'first' if target_base == 'second' else 'second'}"] - runner_lead
    time_to_base = (MOUND_HOME / pitcher_velo) + catcher_pop
    time_runner = target_distance / runner_speed

    return target_distance / (time_to_base - time_runner)


# ---------------------------------------------------------------------------- #
#                                 Data Cleaning                                #
# ---------------------------------------------------------------------------- #


def load_csv(file_path: str) -> pd.DataFrame:
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
        print(result)  # shows likely encoding

    df = pd.read_csv(file_path, encoding=result['encoding'])
    return df


def merge_csvs(file_paths: list, output_file: str):
    """
    Merge multiple CSV files into a single DataFrame and save it.

    Args:
        file_paths: List of paths to CSV files.
        output_file: Path to save the merged CSV.
    """
    dfs = []
    for file_path in file_paths:
        df = load_csv(file_path)
        dfs.append(df)

    merged_df = pd.concat(dfs, ignore_index=True)
    merged_df.to_csv(output_file, index=False)
    print(f"Merged {len(file_paths)} files into {output_file}.")


def lookup_player(player_name: str) -> str:
    """
    Lookup MLBAM player ID from a formatted name "First|Last".

    Args:
        player_name: Player name as "First|Last".

    Returns:
        MLBAM ID as string.
    """
    first, last = map(str.strip, player_name.split('|'))
    data = playerid_lookup(last=last.strip(), first=first.strip())
    if data.empty:
        raise ValueError(f"Player {player_name} not found.")
    return str(data.iloc[0]['key_mlbam'])


def names_to_id(file_path: str, column: str, player_info: str = None):
    """
    Replace batter names with MLBAM player IDs in a CSV.

    Args:
        file_path: Path to CSV file.
        column: Column name containing player names.
        player_info: Optional fallback dictionary of player names to IDs.
    """
    df = load_csv(file_path)
    player_ids = {}
    failed = []

    for name in df[column].unique():
        try:
            player_ids[name] = lookup_player(name)
        except Exception:
            try:
                first, last = map(str.strip, name.split('|'))
                full_name = f"{first} {last}"
            except Exception:
                full_name = name
            if player_info:
                with open(player_info, 'r') as f:
                    info = f.read()
                    info = json.loads(info)
            else:
                info = None
            fallback_id = info.get(full_name, name) if info else name
            player_ids[name] = fallback_id
            failed.append(name)

    print('Failed to lookup the following players:')
    for player in failed:
        if not str(player).isdigit():
            print(player)

    df[column] = df[column].replace(player_ids)
    df.to_csv(file_path, index=False)


def update_description(file_path: str):
    """
    Simplify pitch descriptions to 'ball', 'strike', or 'unknown'.

    Args:
        file_path: Path to the CSV.
    """
    df = load_csv(file_path)

    def simplify(desc):
        try:
            desc_lower = desc.lower()
            if "ball" in desc_lower:
                return "ball"
            elif "strike" in desc_lower:
                return "strike"
        except Exception:
            pass
        return "unknown"

    df['call'] = df['description'].apply(simplify)
    df.drop(columns=['description'], inplace=True)
    df.to_csv(file_path, index=False)


def remove_duplicates(file_path: str):
    """
    Remove duplicate rows from a CSV, preserving the header.

    Args:
        file_path: Path to the CSV file.
    """
    df = load_csv(file_path)

    # Remove duplicate rows
    df.drop_duplicates(inplace=True)

    # Save the updated DataFrame back to the CSV file
    df.to_csv(file_path, index=False)

def update_nan_values(file_path: str):
    """
    Replaces '--' with NaN values in a CSV file.

    Args:
        file_path: Path to the CSV file.
    """
    df = load_csv(file_path)

    # Replace '--' with NaN
    df.replace('--', pd.NA, inplace=True)

    # Save the updated DataFrame back to the CSV file
    df.to_csv(file_path, index=False)


def drop_rows(file_path: str):
    """
    Drop rows with NaN values in 'pitcher_name', 'catcher_name', 'runner_name',
    'lead_distance_gained', 'at_pitchers_first_move', and 'at_pitch_release'

    Args:
        file_path: Path to the CSV file.
    """
    df = load_csv(file_path)

    columns_to_check = [
        'pitcher_name',
        'catcher_name',
        'runner_name',
        'lead_distance_gained',
        'at_pitchers_first_move',
        'at_pitch_release'
    ]
    df.dropna(subset=columns_to_check, inplace=True)

    df.to_csv(file_path, index=False)


def clean_whitespace(file_path: str, columns: list):
    """
    Clean leading and trailing whitespace from specified columns in a CSV.

    Args:
        file_path: Path to the CSV file.
        columns: List of column names to clean.
    """
    df = load_csv(file_path)

    for col in columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    df.to_csv(file_path, index=False)


# ---------------------------------------------------------------------------- #
#                            Random Checks And Gets                            #
# ---------------------------------------------------------------------------- #


def unique_items(file_path: str, col: str) -> list:
    """
    Return a list of unique values from a column in a CSV.

    Args:
        file_path: Path to CSV file.
        col: Column name.

    Returns:
        List of unique items.
    """
    df = pd.read_csv(file_path)
    return df[col].dropna().unique().tolist()


def pkl_content(file_path: str):
    """
    Load and return content from a pickle file.

    Args:
        file_path: Path to .pkl file.

    Returns:
        The object stored in the pickle file.
    """
    try:
        with open(file_path, 'rb') as f:
            content = pickle.load(f)
            if content:
                return content
            raise ValueError("The pkl file is empty.")
    except Exception as e:
        raise ValueError(f"Error reading the pkl file: {e}")


def get_name_from_id(player_id: int) -> str:
    """
    Get player name from MLBAM ID.

    Args:
        player_id: Player's MLBAM ID.

    Returns:
        Player's last, first name.
    """
    df = playerid_reverse_lookup([player_id])
    first = df.iloc[0]['name_first']
    last = df.iloc[0]['name_last']
    return f"{last}, {first}"

# ---------------------------------------------------------------------------- #
#                                 Mean Helpers                                 #
# ---------------------------------------------------------------------------- #


def get_catchers_data(catcher_id: int) -> pd.DataFrame:
    years = list(range(2016, 2026))
    main_df = pd.DataFrame()

    for year in years:
        df = statcast_catcher_poptime(year, min_2b_att=0, min_3b_att=0)
        main_df = pd.concat([main_df, df], ignore_index=True)

    catcher_df = main_df[main_df['entity_name'].str.lower() == get_name_from_id(catcher_id)]

    return catcher_df


def get_pitchers_pitch_data(pitcher_id: int, pitch_type: str) -> pd.DataFrame:
    """
    Retrieve all pitches of a specified type thrown by a given pitcher from 2008 to today.

    Parameters:
    - pitcher_id (int): MLBAM ID of the pitcher.
    - pitch_type (str): Abbreviation of the pitch type (e.g., 'FF' for four-seam fastball).

    Returns:
    - pd.DataFrame: DataFrame containing all matching pitches.
    """
    # Define the start and end dates
    start_date = '2008-01-01'
    end_date = datetime.today().strftime('%Y-%m-%d')

    # Fetch all pitch data for the pitcher within the specified date range
    main_df = statcast_pitcher(start_dt=start_date, end_dt=end_date, player_id=pitcher_id)

    # Check if the DataFrame is empty
    if main_df.empty:
        raise ValueError(f"No data found for pitcher ID {pitcher_id} in the specified date range.")

    # Normalize pitch_type entries to handle potential inconsistencies
    main_df['pitch_type'] = main_df['pitch_type'].astype(str).str.strip().str.upper()
    pitch_type = pitch_type.strip().upper()

    # Retrieve unique pitch types for the pitcher
    unique_pitch_types = main_df['pitch_type'].dropna().unique()

    # Check if the specified pitch_type exists
    if pitch_type not in unique_pitch_types:
        raise ValueError(
            f"Pitch type '{pitch_type}' not found for pitcher ID {pitcher_id}. "
            f"Available pitch types: {', '.join(unique_pitch_types)}"
        )

    # Filter the DataFrame for the specified pitch_type
    pitcher_df = main_df[main_df['pitch_type'] == pitch_type]

    return pitcher_df


def get_player_speed(player_id: int) -> pd.DataFrame:
    years = list(range(2008, 2026))
    main_df = pd.DataFrame()

    for year in years:
        df = statcast_sprint_speed(year, min_opp=0)
        main_df = pd.concat([main_df, df], ignore_index=True)

    player_df = main_df[main_df['player_id'] == player_id]

    return player_df


from selenium.common.exceptions import NoSuchWindowException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from tqdm import tqdm

def get_zone_data(sb_data: str, new_sb_data: str = None):
    sb_df = pd.read_csv(sb_data)

    if 'strike_zone' not in sb_df.columns:
        sb_df['strike_zone'] = None

    if new_sb_data:
        try:
            new_sb_df = pd.read_csv(new_sb_data)
        except FileNotFoundError:
            new_sb_df = pd.DataFrame(columns=sb_df.columns)
    else:
        new_sb_df = pd.DataFrame(columns=sb_df.columns)

    if not new_sb_df.empty:
        compare_cols = sb_df.columns[:-1]
        processed_rows = {
            tuple(row) for row in new_sb_df[compare_cols].itertuples(index=False, name=None)
        }
    else:
        sb_df.iloc[0:0].to_csv(new_sb_data, index=False)
        processed_rows = set()

    try:
        driver = init_driver()
        wait = WebDriverWait(driver, 2)

        # Open a blank tab to avoid closing the main session
        driver.get("about:blank")
        base_tab = driver.current_window_handle

        for row in tqdm(sb_df.itertuples(index=False, name=None), total=len(sb_df), desc="Fetching zone data"):
            row_key = tuple(row[:-1])
            if row_key in processed_rows:
                continue

            video_link = row[-2]
            strike_zone = None

            try:
                # Open new tab and switch to it
                driver.execute_script("window.open('');")
                new_tab = [tab for tab in driver.window_handles if tab != base_tab][-1]
                driver.switch_to.window(new_tab)

                driver.get(video_link)
                wait.until(EC.presence_of_element_located((By.ID, "zone_chart")))
                strike_zone = driver.find_element(By.ID, "zone_chart").get_attribute("innerHTML")

            except (NoSuchWindowException, WebDriverException) as e:
                print(f"[SKIP] Chrome window error for row {row}: {e}")
            except Exception as e:
                print(f"[SKIP] General error fetching zone for row {row}: {e}")
            finally:
                # Close current tab and return to base tab
                try:
                    driver.close()
                    driver.switch_to.window(base_tab)
                except Exception:
                    pass

            if strike_zone is None:
                continue

            new_row = list(row[:-1]) + [strike_zone]
            with open(new_sb_data, 'a') as f:
                pd.DataFrame([new_row], columns=sb_df.columns).to_csv(f, header=False, index=False)

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    print("Strike zone data fetch complete.")





# ---------------------------------------------------------------------------- #
#                          Standard Deviation Helpers                          #
# ---------------------------------------------------------------------------- #

if __name__ == '__main__':
# --------------------------------- File Path -------------------------------- #
#     file = '/Users/robbykapua/Documents/GitHub/idea-lab/sb_probability/data/sb_data_complete/sb_data_2016-2021.csv'
#     file = '/Users/robbykapua/Documents/GitHub/idea-lab/sb_probability/data/sb_data_complete/sb_data_2022-2025.csv'
    file = '/Users/robbykapua/Documents/GitHub/idea-lab/sb_probability/data/sb_data_complete/sb_data_2016-2025.csv'
#     file = '/Users/robbykapua/Documents/GitHub/idea-lab/sb_probability/data/sb_data_complete/new_sb_data_2016-2025.csv'
    # player_info = '/Users/robbykapua/Documents/GitHub/idea-lab/sb_probability/data/name_id_map.json'

    # df = pd.read_csv(file)
    # df["fielder_id"] = df["fielder_id"].fillna(-1).astype(int)  # or use a sentinel like -1

    # Convert float to int
    # df["fielder_id"] = df["fielder_id"].astype(int)

    # Overwrite the original CSV with the updated data
    # df.to_csv(file, index=False)

# -------------------------------- Remove rows ------------------------------- #
#     remove_duplicates(file)
#     update_nan_values(file)
#     drop_rows(file)

# ------------------- Clean whitespace in specific columns ------------------- #
#     clean_whitespace(file, ['batter_name', 'pitcher_name', 'fielder_name', 'catcher_name', 'runner_name'])

# ------------------------ Convert player names to IDs ----------------------- #
#     names_to_id(file, 'batter_name', player_info)
#     names_to_id(file, 'pitcher_name', player_info)

# ------------------------- Update pitch descriptions ------------------------ #
#     update_description(file)

    # merge_csvs(['/Users/robbykapua/Documents/GitHub/idea-lab/sb_probability/sb_data_worker_0.csv',
    #                      '/Users/robbykapua/Documents/GitHub/idea-lab/sb_probability/sb_data_worker_1.csv'],
    #            '/Users/robbykapua/Documents/GitHub/idea-lab/sb_probability/data/sb_data_complete/sb_data_2016-2021.csv')

    # merge_csvs([
    #     '/Users/robbykapua/Documents/GitHub/idea-lab/sb_probability/data/sb_data_complete/sb_data_2016-2021.csv',
    #     '/Users/robbykapua/Documents/GitHub/idea-lab/sb_probability/data/sb_data_complete/sb_data_2022-2025.csv'
    # ],
    # '/Users/robbykapua/Documents/GitHub/idea-lab/sb_probability/data/sb_data_complete/sb_data_2016-2025.csv')

    get_zone_data(file, '/Users/robbykapua/Documents/GitHub/idea-lab/sb_probability/data/sb_data_complete/new_sb_data_2016-2025.csv')
