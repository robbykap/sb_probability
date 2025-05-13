from pybaseball import playerid_lookup, statcast_sprint_speed, statcast_catcher_poptime, statcast_pitcher_arsenal_stats

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
        player_data = playerid_lookup(last=last, first=first)
        if not player_data.empty:
            return player_data.iloc[0]['key_mlbam']
        else:
            raise ValueError(f"Player {player_name} not found.")
    except Exception as e:
        raise ValueError(f"Error looking up player {player_name}: {e}")


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

