# /// script
# dependencies = [
#   "requests",
#   "pandas",
# ]
# ///

"""Naver Finance ETF Data Collector.

This module fetches real-time ETF sise data from Naver Finance API,
parses the JSONP response, converts it to a pandas DataFrame, and
saves it as a CSV file in the 'data' directory. It supports both
one-time collection and periodic collection using an infinite loop.
"""

import os
import re
import json
import time
import argparse
from typing import Dict, Any, List
import requests
import pandas as pd
from datetime import datetime

def collect_etf_data() -> None:
    """Fetches ETF data from Naver Finance and saves it to a timestamped CSV file.

    Raises:
        requests.exceptions.HTTPError: If the HTTP request to Naver Finance fails.
        ValueError: If the response is not in the expected JSONP format.
    """
    url: str = "https://finance.naver.com/api/sise/etfItemList.nhn?etfType=0&targetColumn=market_sum&sortOrder=desc&_callback=window.__jindo2_callback._7957"
    headers: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"[{datetime.now()}] Fetching data from Naver Finance...")
    response: requests.Response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Strip the JSONP callback wrapper to extract the pure JSON string.
    # The format is window.__jindo2_callback._7957({...});
    text: str = response.text.strip()
    match = re.match(r"^\w+(\.\w+)*\s*\((.*)\);?$", text, re.DOTALL)
    if not match:
        raise ValueError("Response is not in JSONP format")
    
    json_data_str: str = match.group(2)
    data: Dict[str, Any] = json.loads(json_data_str)
    
    # Extract the ETF item list from the nested dictionary.
    result: Dict[str, Any] = data.get("result", {})
    etf_list: List[Dict[str, Any]] = result.get("etfItemList", [])
    
    if not etf_list:
        print("No ETF items found in the response.")
        return
    
    # Convert list of dicts to a pandas DataFrame.
    df: pd.DataFrame = pd.DataFrame(etf_list)
    
    # Define the output directory (current_dir/data).
    current_dir: str = os.path.dirname(os.path.abspath(__file__))
    data_dir: str = os.path.join(current_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Generate a timestamped file name: etf_data_YYYYMMDD_HHMMSS.csv
    timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path: str = os.path.join(data_dir, f"etf_data_{timestamp}.csv")
    
    # Save the DataFrame to CSV using utf-8-sig for Excel compatibility.
    df.to_csv(file_path, index=False, encoding="utf-8-sig")
    print(f"[{datetime.now()}] Successfully saved ETF data to {file_path}")

def main() -> None:
    """Parses command-line arguments and starts the data collection."""
    parser = argparse.ArgumentParser(description="Collect Naver ETF data.")
    parser.add_argument(
        "--loop", "-l", action="store_true", help="Run in a continuous loop every 60 seconds."
    )
    args = parser.parse_args()

    if args.loop:
        print("Starting continuous collection mode (every 60 seconds). Press Ctrl+C to stop.")
        while True:
            try:
                collect_etf_data()
            except Exception as e:
                print(f"[{datetime.now()}] Error occurred: {e}")
            # Wait for 60 seconds before next collection.
            time.sleep(60)
    else:
        collect_etf_data()

if __name__ == "__main__":
    main()
