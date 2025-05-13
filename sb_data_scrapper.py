import time

from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC


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
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    return webdriver.Chrome(options=options)


def process_player(driver, wait, player, start_year, end_year, url, all_data, is_retry=False) -> bool:
    try:
        driver.get(url)

        wait.until(EC.presence_of_element_located((By.ID, "ddlSeasonStart")))
        Select(driver.find_element(By.ID, "ddlSeasonStart")).select_by_visible_text(str(start_year))
        Select(driver.find_element(By.ID, "ddlSeasonEnd")).select_by_visible_text(str(end_year))
        driver.find_element(By.ID, "btn-update").click()

        wait.until(EC.presence_of_element_located((By.ID, "basestealing_running_game_table")))
        updated_rows = driver.find_elements(By.CLASS_NAME, "default-table-row")
        match_row = next((r for r in updated_rows if r.find_element(By.TAG_NAME, "a").text == player), None)

        if not match_row:
            print(f"{'Retry' if is_retry else 'Initial'}: Player row not found: {player}")
            return False

        match_row.click()
        time.sleep(1)  # Optional but helps with flaky rendering

        # Wait for sub-data row to be open and visible
        wait.until(EC.presence_of_element_located(
            (By.XPATH, "//tr[@class='tr-sub-data' and @data-open='true']")
        ))

        sub_data_div = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//tr[@class='tr-sub-data' and @data-open='true']//div[contains(@class, 'all-tab-pane')]")
            )
        )

        sb_rows = sub_data_div.find_elements(By.CLASS_NAME, "default-table-row")

        for j, sb_row in enumerate(sb_rows):
            spans = sb_row.find_elements(By.TAG_NAME, "span")
            values = []
            for s in spans:
                if s.find_elements(By.TAG_NAME, "a"):
                    href = s.find_element(By.TAG_NAME, "a").get_attribute("href")
                    id = href.split("/")[-1]
                    values.append(id)
                else:
                    values.append(s.text.strip())
            sb = SBData()
            upload_data(sb, values)

            video_link = sb_row.find_element(By.CLASS_NAME, "video-col").find_element(By.TAG_NAME, "a").get_attribute(
                "href")
            driver.execute_script("window.open(arguments[0]);", video_link)
            driver.switch_to.window(driver.window_handles[1])

            try:
                wait.until(EC.presence_of_element_located((By.ID, "sporty_video")))
                sb.description = driver.find_element(By.TAG_NAME, "h3").text.strip()
                bullets = driver.find_elements(By.CLASS_NAME, "mod")[-1].find_elements(By.TAG_NAME, "li")
                bullet_data = [b.text.split(':')[-1].strip() for b in bullets]
                upload_remaining_data(sb, bullet_data)
                all_data.append(sb)

                print(f"  ✓ Row {j + 1}/{len(sb_rows)} for {player} complete.")

            except Exception as e:
                print(f"  ⚠️ Video data error: {e}")
            finally:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

        match_row.click()
        return True

    except Exception as e:
        print(f"{'Retry' if is_retry else 'Initial'} failed for {player}: {e}")
        return False


def scrape_data(start_year: int, end_year: int, url: str) -> list[SBData]:
    driver = init_driver()
    wait = WebDriverWait(driver, 15)
    all_data = []

    try:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.ID, "basestealing_running_game_table")))
        rows = driver.find_elements(By.CLASS_NAME, "default-table-row")
        players = [r.find_element(By.TAG_NAME, "a").text for r in rows]

        for i, player in enumerate(players):
            if len(all_data) >= 3:
                break
            print(f"\nProcessing player {i + 1}/{len(players)}: {player}")

            process_player(driver, wait, player, start_year, end_year, url, all_data)

    finally:
        driver.quit()

    return all_data


if __name__ == '__main__':
    # Year ranges [2016 - 2025]
    start_yr = 2023
    end_yr = 2023
    url = "https://baseballsavant.mlb.com/leaderboard/basestealing-run-value"
    data = scrape_data(start_yr, end_yr, url)
