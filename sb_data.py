from pathlib import Path
from sb_data_scrapper import SBData, scrape_data


def upload_data(data, filename):
    """
    Uploads the scraped data to a CSV file.

    Args:
        data (list): The scraped data.
        filename (str): The name of the file to save the data to.
    """
    if Path(filename).exists():
        base = filename.split('.')[0]
        ext = filename.split('.')[-1]
        count = 1
        while Path(filename).exists():
            filename = f"{base}_{count}.{ext}"
            count += 1

    with open(filename, 'w') as file:
        # Get header from the SBData class elements
        header = [field for field in SBData.__annotations__.keys()]
        file.write(','.join(header) + '\n')

        # Write each data entry
        for entry in data:
            line = ','.join(str(getattr(entry, field)) for field in header)
            file.write(line + '\n')


if __name__ == '__main__':
    # Year ranges [2016 - 2025]
    start_yr = 2024
    end_yr = 2025
    url = "https://baseballsavant.mlb.com/leaderboard/basestealing-run-value"
    data = scrape_data(start_yr, end_yr, url)
    upload_data(data, f"sb_data_{start_yr}-{end_yr}.csv")