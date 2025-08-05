import time
import random
import pickle
from pathlib import Path
from dataclasses import dataclass
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm
import multiprocessing as mp
import os


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
    strike_zone: str = ""
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

    pitcher_name = safe_get(data, 1)
    if pitcher_name:
        name = pitcher_name.split(',')
        if len(name) > 1:
            first = name[1].strip()
            last = name[0].strip()
            sbdata.pitcher_name = f"{first} | {last}"

    count = safe_get(data, 2)
    if '-' in count:
        parts = count.split('-')
        sbdata.ball_count = parts[0].strip()
        sbdata.strike_count = parts[1].strip()

    sbdata.pitch_type = safe_get(data, 3)
    sbdata.velo = safe_get(data, 4)
    sbdata.match_up = safe_get(data, 7)

def upload(data, filename):
    file_exists = Path(filename).exists()
    is_empty = not file_exists or Path(filename).stat().st_size == 0
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
    options.add_argument('--start-maximized')
    options.add_argument('--disable-popup-blocking')
    return uc.Chrome(options=options)

def scrape_worker(worker_id, start_idx, end_idx, url, checkpoint=None):
    checkpoint = f"checkpoint_{worker_id}.pkl" if checkpoint is None else checkpoint
    file_path = f"sb_data_worker_{worker_id}.csv"

    driver = init_driver()
    wait = WebDriverWait(driver, 60)

    try:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.ID, "ddlSeasonStart")))
        Select(driver.find_element(By.ID, "ddlSeasonStart")).select_by_visible_text("2016")
        Select(driver.find_element(By.ID, "ddlSeasonEnd")).select_by_visible_text("2021")
        driver.find_element(By.ID, "btn-update").click()
        wait.until(EC.presence_of_element_located((By.ID, "basestealing_running_game_table")))

        if Path(checkpoint).exists() and os.path.getsize(checkpoint) > 0:
            with open(checkpoint, "rb") as f:
                sb_rows = pickle.load(f)
            print(f"[Worker {worker_id}] Resuming from checkpoint with {len(sb_rows)} rows.")
        else:
            sb_rows = []

            player_rows = driver.find_elements(By.CLASS_NAME, "default-table-row")
            target_rows = player_rows[start_idx:end_idx]

            for row in tqdm(target_rows, desc=f"Worker {worker_id} scraping", position=worker_id):
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
                    time.sleep(random.uniform(2, 4))
                    driver.execute_script("arguments[0].click();", row)
                    time.sleep(random.uniform(2, 4))
                except:
                    continue

            time.sleep(3)
            sub_data_rows = driver.find_elements(By.XPATH, "//tr[@class='tr-sub-data' and @data-open='true']")
            for sub in tqdm(sub_data_rows, desc=f"Worker {worker_id} parsing rows", position=worker_id):
                try:
                    sub_data_div = sub.find_element(By.CLASS_NAME, "all-tab-pane")
                    rows = sub_data_div.find_elements(By.CLASS_NAME, "default-table-row")
                    for row in rows:
                        spans = row.find_elements(By.TAG_NAME, "span")
                        values = [s.text.strip() if not s.find_elements(By.TAG_NAME, "a") else s.find_element(By.TAG_NAME, "a").get_attribute("href").split("/")[-1] for s in spans]
                        sb = SBData()
                        upload_data(sb, values)
                        try:
                            sb.video_link = row.find_element(By.CLASS_NAME, "video-col").find_element(By.TAG_NAME, "a").get_attribute("href")
                        except:
                            sb.video_link = ""
                        sb_rows.append(sb)
                except:
                    continue

            with open(checkpoint, "wb") as f:
                pickle.dump(sb_rows, f)

        for i, sb in enumerate(tqdm(sb_rows, desc=f"Worker {worker_id} video scrape", position=worker_id)):
            if not sb.video_link:
                continue
            try:
                driver.execute_script("window.open(arguments[0]);", sb.video_link)
                time.sleep(1)
                if len(driver.window_handles) < 2:
                    print(f"[Worker {worker_id}] Failed to open video window for link: {sb.video_link}")
                    continue
                # Switch to the newest window/tab
                driver.switch_to.window(driver.window_handles[-1])
                wait.until(EC.presence_of_element_located((By.ID, "sporty_video")))
                sb.description = driver.find_element(By.TAG_NAME, "h3").text.strip().replace(',', '|')
                sb.strike_zone = driver.find_element(By.ID, "zone_chart-zone").get_attribute("innerHTML")
                bullets = driver.find_elements(By.CLASS_NAME, "mod")[-1].find_elements(By.TAG_NAME, "li")
                bullet_data = [b.text.split(":")[-1].strip() for b in bullets]
                upload_remaining_data(sb, bullet_data)
            except Exception as e:
                print(f"[Worker {worker_id}] Error while scraping video link: {e}")
                continue
            finally:
                try:
                    if len(driver.window_handles) > 1:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                except Exception as e:
                    print(f"[Worker {worker_id}] Error during window close/switch: {e}")

            upload([sb], file_path)
            with open(checkpoint, "wb") as f:
                pickle.dump(sb_rows[i + 1:], f)

    finally:
        driver.quit()


def main(
        url = "https://baseballsavant.mlb.com/leaderboard/basestealing-run-value",
        n_workers: int = 2,
        checkpoints: list = None
):

    try:
        driver = init_driver()
        wait = WebDriverWait(driver, 60)
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.ID, "ddlSeasonStart")))
        Select(driver.find_element(By.ID, "ddlSeasonStart")).select_by_visible_text("2016")
        Select(driver.find_element(By.ID, "ddlSeasonEnd")).select_by_visible_text("2025")
        driver.find_element(By.ID, "btn-update").click()
        wait.until(EC.presence_of_element_located((By.ID, "basestealing_running_game_table")))
    except Exception:
        pass

    player_rows = driver.find_elements(By.CLASS_NAME, "default-table-row")
    total = len(player_rows)
    driver.quit()

    num_workers = n_workers if not checkpoints else len(checkpoints)
    chunk_size = total // num_workers

    processes = []
    for i in range(num_workers):
        # try to set up the worker 3 times if it fails
        if i == num_workers - 1:
            chunk_size = total - (chunk_size * i)
        if chunk_size <= 0:
            print(f"Chunk size for worker {i} is zero or negative, skipping.")
            continue

        print(f"Starting worker {i} with range {i * chunk_size} to {min((i + 1) * chunk_size, total)}")

        start = i * chunk_size
        end = min(start + chunk_size, total)
        if checkpoints:
            p = mp.Process(target=scrape_worker, args=(i, start, end, url, checkpoints[i]))
        else:
            p = mp.Process(target=scrape_worker, args=(i, start, end, url))
        p.start()
        processes.append(p)
        time.sleep(1)

    for p in processes:
        p.join()

if __name__ == '__main__':
    main(
    )