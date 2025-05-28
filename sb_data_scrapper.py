import time
import random
import pickle
from pathlib import Path
from dataclasses import dataclass
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm, trange


@dataclass
class SBData:
    date: str = ""
    catcher_name: str = ""
    pitcher_name: str = ""
    runner_name: str = ""
    batter_name: str = ""
    fielder_name: str = ""
    target_base: str = ""
    result: str = ""
    runner_stealing_runs: str = ""
    lead_distance_gained: str = ""
    at_pitchers_first_move: str = ""
    at_pitch_release: str = ""
    ball_count: str = ""
    strike_count: str = ""
    pitch_type: str = ""
    velo: str = ""
    description: str = ""
    match_up: str = ""
    video_link: str = ""


def safe_get(data: list, index: int) -> str:
    return data[index] if index < len(data) else ""


def upload_data(sbdata: SBData, data: list[str]):
    sbdata.date = safe_get(data, 0)
    sbdata.catcher_name = safe_get(data, 1)
    sbdata.runner_name = safe_get(data, 3)
    sbdata.fielder_name = safe_get(data, 4)
    sbdata.target_base = safe_get(data, 5)
    sbdata.result = safe_get(data, 6)
    sbdata.runner_stealing_runs = safe_get(data, 7)
    sbdata.lead_distance_gained = safe_get(data, 8)
    sbdata.at_pitchers_first_move = safe_get(data, 9)
    sbdata.at_pitch_release = safe_get(data, 10)


def upload_remaining_data(sbdata: SBData, data: list[str]):
    batter_name = safe_get(data, 0)
    if batter_name:
        name = batter_name.split(',')
        if len(name) > 1:
            first = name[1].strip()
            last = name[0].strip()
            sbdata.batter_name = f"{first} | {last}"

    sbdata.pitcher_name = safe_get(data, 1)

    count = safe_get(data, 2)
    if '-' in count:
        parts = count.split('-')
        sbdata.ball_count = parts[0].strip()
        sbdata.strike_count = parts[1].strip()

    sbdata.pitch_type = safe_get(data, 3)
    sbdata.velo = safe_get(data, 4)
    sbdata.match_up = safe_get(data, 7)



def upload(data, filename):
    """
    Uploads the scraped data to a CSV file.

    Args:
        data (list): The scraped data.
        filename (str): The name of the file to save the data to.
    """
    file_exists = Path(filename).exists()
    is_empty = not file_exists or Path(filename).stat().st_size == 0

    # Open in append mode if the file exists and isn't empty
    mode = 'a' if file_exists and not is_empty else 'w'

    with open(filename, mode) as file:
        header = [field for field in SBData.__annotations__.keys()]

        if mode == 'w':
            file.write(','.join(header) + '\n')

        for entry in data:
            line = ','.join(str(getattr(entry, field)) for field in header)
            file.write(line + '\n')


def init_driver():
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-infobars')
    options.add_argument("--disable-popup-blocking")
    options.add_argument('--start-maximized')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    return uc.Chrome(options=options)


def countdown(seconds):
    for _ in trange(seconds, desc=f"🛑 Sleeping between batches for {seconds} seconds", ncols=100):
        time.sleep(1)


def scrape_data(start_year: int, end_year: int, url: str, checkpoint: str = None, file_path: str = None, load_checkpoint: bool = False):
    driver = init_driver()
    wait = WebDriverWait(driver, 60)

    try:
        driver.get(url)

        main_window = driver.current_window_handle

        # Load the checkpoint data if provided
        if load_checkpoint:
            with open(checkpoint, "rb") as f:
                sb_rows = pickle.load(f)

        else:
            wait.until(EC.presence_of_element_located((By.ID, "ddlSeasonStart")))
            Select(driver.find_element(By.ID, "ddlSeasonStart")).select_by_visible_text(str(start_year))
            Select(driver.find_element(By.ID, "ddlSeasonEnd")).select_by_visible_text(str(end_year))
            driver.find_element(By.ID, "btn-update").click()

            wait.until(EC.presence_of_element_located((By.ID, "basestealing_running_game_table")))
            player_rows = driver.find_elements(By.CLASS_NAME, "default-table-row")

            BATCH_SIZE = 25
            total_batches = len(player_rows) // BATCH_SIZE + (1 if len(player_rows) % BATCH_SIZE != 0 else 0)

            for batch_index, batch_start in enumerate(range(0, len(player_rows), BATCH_SIZE)):
                batch = player_rows[batch_start:batch_start + BATCH_SIZE]

                for i, row in enumerate(tqdm(batch, desc=f"🚀 Expanding batch {batch_index + 1} of {total_batches}", ncols=80)):
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
                        time.sleep(random.uniform(3, 6))
                        driver.execute_script("arguments[0].click();", row)
                        time.sleep(random.uniform(2, 5))
                    except Exception:
                        pass

                wait_time = random.randint(0, 120)
                countdown(wait_time)
                print()

            wait.until(EC.presence_of_all_elements_located((By.XPATH, "//tr[@class='tr-sub-data' and @data-open='true']")))
            sub_data_rows = driver.find_elements(By.XPATH, "//tr[@class='tr-sub-data' and @data-open='true']")

            sb_rows = []

            for i, sub in enumerate(tqdm(sub_data_rows, desc="Parsing sub-rows", ncols=80)):
                try:
                    driver.execute_script("window.scrollBy(0, 100);")
                    time.sleep(0.5)
                    sub_data_div = sub.find_element(By.CLASS_NAME, "all-tab-pane")
                    rows = sub_data_div.find_elements(By.CLASS_NAME, "default-table-row")

                    for row in rows:
                        spans = row.find_elements(By.TAG_NAME, "span")
                        values = [s.text.strip() if not s.find_elements(By.TAG_NAME, "a") else s.find_element(By.TAG_NAME, "a").get_attribute("href").split("/")[-1] for s in spans]
                        sb = SBData()
                        upload_data(sb, values)
                        try:
                            sb.video_link = row.find_element(By.CLASS_NAME, "video-col").find_element(By.TAG_NAME, "a").get_attribute("href")
                        except Exception:
                            sb.video_link = ""
                        sb_rows.append(sb)
                except Exception:
                    print(f"Error processing sub-row {i + 1}: {sub.text}")
                    continue

            # Upload the current data to a checkpoint file
            with open(checkpoint, "wb") as f:
                pickle.dump(sb_rows, f)

        for i, sb in enumerate(tqdm(sb_rows, desc="Extracting remaining data", ncols=80)):
            if not sb.video_link:
                continue
            try:
                driver.execute_script("window.open(arguments[0]);", sb.video_link)
                driver.switch_to.window(driver.window_handles[1])

                try:
                    # Wait with a timeout (e.g., 10 seconds max)
                    wait.until(EC.presence_of_element_located((By.ID, "sporty_video")))

                    # Check for "Bad Gateway"
                    if "Bad Gateway" in driver.page_source or "502" in driver.title:
                        print("Bad Gateway detected. Refreshing...")
                        driver.refresh()
                        wait.until(EC.presence_of_element_located((By.ID, "sporty_video")))

                    # Continue only if sporty_video exists
                    sb.description = driver.find_element(By.TAG_NAME, "h3").text.strip().replace(',', '|')
                    bullets = driver.find_elements(By.CLASS_NAME, "mod")[-1].find_elements(By.TAG_NAME, "li")
                    bullet_data = [b.text.split(":")[-1].strip() for b in bullets]
                    upload_remaining_data(sb, bullet_data)

                except Exception as e:
                    print(f"Timeout or content issue: {e}")
                    continue

            except Exception as e:
                print(f"Error opening video link: {sb.video_link} | {e}")
                continue

            finally:
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

            # time.sleep(random.uniform(3, 5))

            # Upload the data to a CSV file
            upload([sb], file_path)

            # Updated the checkpoint file after each entry to remove the processed data
            with open(checkpoint, "wb") as f:
                pickle.dump(sb_rows[i + 1:], f)

    finally:
        driver.quit()


if __name__ == '__main__':
    # Year ranges [2016 - 2025]
    start_yr = 2022
    end_yr = 2025
    url = "https://baseballsavant.mlb.com/leaderboard/basestealing-run-value"
    scrape_data(
        start_yr, end_yr, url,
        checkpoint='checkpoint.pkl',
        file_path=f"sb_data_{start_yr}-{end_yr}.csv",
        load_checkpoint=False
    )
