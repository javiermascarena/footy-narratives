import os
import subprocess
import sys
from datetime import datetime, timedelta


if __name__ == "__main__":
    # Get the script's directory and build an absolute path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    txt_path = os.path.join(script_dir, "check_dates.txt")

    # Define the paths to the scraper scripts
    sky_path = os.path.join(script_dir, "sky_scraper.py")
    bbc_path = os.path.join(script_dir, "bbc_scraper.py")
    theguardian_path = os.path.join(script_dir, "theguardian_scraper.py")

    # Get the current date and the last date (24 hours ago)
    # Since the script is run daily, we can use the current date and the last date
    date_format = "%Y-%m-%d %H:%M:%S.%f"
    current_date = datetime.now()
    last_date = current_date - timedelta(days=1)

    # Convert the dates to strings
    last_date = last_date.strftime(date_format)
    current_date = current_date.strftime(date_format)

    # Run the scraper scripts with the last date and current date as arguments
    print("Starting scrapers...\n")
    subprocess.run([
        sys.executable, 
        sky_path,
        last_date, 
        current_date
    ])
    print("SkySports finished!\n")
    subprocess.run([
        sys.executable, 
        bbc_path,
        last_date, 
        current_date
    ])
    print("BBC finished!\n")
    subprocess.run([
        sys.executable, 
        theguardian_path,
        last_date, 
        current_date
    ])
    print("TheGuardian finished!")


    