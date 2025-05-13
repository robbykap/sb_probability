import time
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm


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
    sbdata.pitcher_name = safe_get(data, 2)
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
        first = name[1].strip()
        last = name[0].strip()
        sbdata.batter_name = f"{first} | {last}"
    count = safe_get(data, 2)
    if '-' in count:
        parts = count.split('-')
        sbdata.ball_count = parts[0].strip()
        sbdata.strike_count = parts[1].strip()
    sbdata.pitch_type = safe_get(data, 3)
    sbdata.velo = safe_get(data, 4)
    sbdata.match_up = safe_get(data, 7)


def init_driver() -> webdriver.Chrome:
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    return webdriver.Firefox(options=options)


def scrape_data(start_year: int, end_year: int, url: str) -> list[SBData]:
    driver = init_driver()
    wait = WebDriverWait(driver, 60)
    all_data = []

    try:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.ID, "ddlSeasonStart")))
        Select(driver.find_element(By.ID, "ddlSeasonStart")).select_by_visible_text(str(start_year))
        Select(driver.find_element(By.ID, "ddlSeasonEnd")).select_by_visible_text(str(end_year))
        driver.find_element(By.ID, "btn-update").click()

        wait.until(EC.presence_of_element_located((By.ID, "basestealing_running_game_table")))
        player_rows = driver.find_elements(By.CLASS_NAME, "default-table-row")
        players = [row.find_element(By.TAG_NAME, 'a').text for row in player_rows]

        print(f"📂 Expanding {len(player_rows)} players...")
        failed_rows = []

        i = 0
        for row in tqdm(player_rows, desc="Expanding rows", ncols=80):
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
                time.sleep(4)
                driver.execute_script("arguments[0].click();", row)
                time.sleep(2)
            except Exception:
                failed_rows.append(i)

            i += 1

        print()
        if failed_rows:
            print(f"⚠️ Could not expand the following player row(s):")
            for i in failed_rows:
                print(f"  - {players[i]}")
            print()

        time.sleep(30)

        wait.until(EC.presence_of_all_elements_located((By.XPATH, "//tr[@class='tr-sub-data' and @data-open='true']")))

        sub_data_rows = driver.find_elements(By.XPATH, "//tr[@class='tr-sub-data' and @data-open='true']")
        print(f"🔍 Extracting data from {len(sub_data_rows)} sub-data rows...")
        sb_rows = []
        failed_sub_rows = []

        i = 0
        for sub in tqdm(sub_data_rows, desc="Parsing sub-rows", ncols=80):
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
                    except Exception:
                        sb.video_link = ""

                    sb_rows.append(sb)
            except Exception:
                failed_sub_rows.append(i)

            i += 1

        print()
        if failed_sub_rows:
            print(f"⚠️ Could not extract the following sub-data row(s) ({len(failed_sub_rows)} / {len(sub_data_rows)}):")
            for i in failed_sub_rows:
                print(f"  - {players[i]}")
            print()

        print(f"🎥 Opening {len(sb_rows)} video pages and finalizing data...")

        failed_video_rows = []

        for sb in tqdm(sb_rows, desc="Extracting remaining data", ncols=80):
            if not sb.video_link:
                continue

            try:
                driver.execute_script("window.open(arguments[0]);", sb.video_link)
                driver.switch_to.window(driver.window_handles[1])
                wait.until(EC.presence_of_element_located((By.ID, "sporty_video")))

                sb.description = driver.find_element(By.TAG_NAME, "h3").text.strip()
                bullets = driver.find_elements(By.CLASS_NAME, "mod")[-1].find_elements(By.TAG_NAME, "li")
                bullet_data = [b.text.split(':')[-1].strip() for b in bullets]
                upload_remaining_data(sb, bullet_data)

            except Exception as e:
                failed_video_rows.append(sb)

            finally:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

            all_data.append(sb)

    finally:
        driver.quit()

    return all_data


if __name__ == '__main__':
    start_yr = 2025
    end_yr = 2025
    url = "https://baseballsavant.mlb.com/leaderboard/basestealing-run-value"
    data = scrape_data(start_yr, end_yr, url)
