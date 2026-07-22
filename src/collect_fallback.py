# -*- coding: utf-8 -*-
"""Naver Finance ETF Data Collector for Static Dashboard Fallback.

This module fetches real-time ETF sise data from Naver Finance API,
parses the JSONP response, extracts the dataset, processes the data
by adding derived columns like brand, and saves it as a JSON file
to be used as a fallback dataset for the static dashboard.
"""

import os
import re
import json
from typing import Dict, Any, List
import requests
import pandas as pd

def parse_jsonp(jsonp_text: str) -> Dict[str, Any]:
    """Strips the JSONP callback wrapper to extract the pure JSON object.

    Args:
        jsonp_text: The raw response string from the Naver Finance API.

    Returns:
        A dictionary representation of the parsed JSON data.

    Raises:
        ValueError: If the response is not in the expected JSONP format.
    """
    cleaned_text: str = jsonp_text.strip()
    # Matches callbackName(jsonData); or callbackName(jsonData)
    match = re.match(r"^\w+(\.\w+)*\s*\((.*)\);?$", cleaned_text, re.DOTALL)
    if not match:
        raise ValueError("Response is not in a valid JSONP callback format.")
    
    json_data_str: str = match.group(2)
    return json.loads(json_data_str)

def extract_brand(item_name: str) -> str:
    """Extracts the asset management brand from the ETF name.

    Args:
        item_name: The name of the ETF (e.g., 'KODEX 200', 'TIGER 미국S&P500').

    Returns:
        The extracted brand name (e.g., 'KODEX', 'TIGER'). Defaults to '기타' if unknown.
    """
    known_brands: List[str] = [
        "KODEX", "TIGER", "KBSTAR", "ACE", "SOL", "RISE", "ARIRANG", 
        "HANARO", "WOORI", "KoAct", "KOSEF", "PLUS", "UNICORN", 
        "MASTER", "HANA", "TREX", "EON", "KINDEX"
    ]
    
    # Check if any known brand is contained in the item name (case insensitive)
    upper_name: str = item_name.upper()
    for brand in known_brands:
        if brand in upper_name:
            return brand
            
    # Fallback to the first word if it contains alphabets or Korean characters
    words: List[str] = item_name.split()
    if words:
        first_word: str = words[0]
        # Clean special characters
        cleaned_word: str = re.sub(r"[^a-zA-Z가-힣]", "", first_word)
        if cleaned_word:
            return cleaned_word
            
    return "기타"

def collect_and_save_etf_data(output_path: str) -> None:
    """Fetches ETF sise data from Naver Finance, processes it, and saves it to a JSON file.

    Args:
        output_path: The file path where the JSON output should be saved.

    Raises:
        requests.exceptions.HTTPError: If the API request fails.
        ValueError: If the data cannot be parsed.
    """
    url: str = "https://finance.naver.com/api/sise/etfItemList.nhn?etfType=0&targetColumn=market_sum&sortOrder=desc&_callback=window.__jindo2_callback._7957"
    headers: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print("Fetching data from Naver Finance API...")
    response: requests.Response = requests.get(url, headers=headers)
    response.raise_for_status()

    raw_data: Dict[str, Any] = parse_jsonp(response.text)
    etf_list: List[Dict[str, Any]] = raw_data.get("result", {}).get("etfItemList", [])
    
    if not etf_list:
        raise ValueError("No ETF item list found in the API response.")

    print(f"Successfully fetched {len(etf_list)} ETF items. Preprocessing data...")
    
    # Convert to DataFrame for easier data manipulation
    df = pd.DataFrame(etf_list)
    
    # Clean column names (e.g. resolve typo 'amonut' to 'amount')
    if "amonut" in df.columns:
        df.rename(columns={"amonut": "amount"}, inplace=True)
    
    # Fill missing values and ensure correct data types
    df["nowVal"] = pd.to_numeric(df["nowVal"], errors="coerce").fillna(0).astype(int)
    df["changeVal"] = pd.to_numeric(df["changeVal"], errors="coerce").fillna(0).astype(int)
    df["changeRate"] = pd.to_numeric(df["changeRate"], errors="coerce").fillna(0.0).astype(float)
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce").fillna(0.0).astype(float)
    df["threeMonthEarnRate"] = pd.to_numeric(df["threeMonthEarnRate"], errors="coerce").fillna(0.0).astype(float)
    df["quant"] = pd.to_numeric(df["quant"], errors="coerce").fillna(0).astype(int)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)
    df["marketSum"] = pd.to_numeric(df["marketSum"], errors="coerce").fillna(0).astype(int)
    
    # 1. Extract Brand
    df["brand"] = df["itemname"].apply(extract_brand)
    
    # 2. Calculate NAV Premium (괴리율)
    # Formula: ((nowVal - nav) / nav) * 100
    # Avoid division by zero
    df["navPremium"] = np.where(
        df["nav"] > 0,
        ((df["nowVal"] - df["nav"]) / df["nav"]) * 100,
        0.0
    )
    df["navPremium"] = df["navPremium"].round(4)

    # Convert back to dict list to save as JSON
    processed_list: List[Dict[str, Any]] = df.to_dict(orient="records")

    # Ensure target directory exists
    dir_name: str = os.path.dirname(output_path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)

    # Save to file (Minify JSON to minimize file size on static hosting)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(processed_list, f, ensure_ascii=False, separators=(',', ':'))

    print(f"Data saved successfully (minified) to {output_path}")

if __name__ == "__main__":
    import numpy as np  # Imported here for safety in case not loaded in context
    output_file: str = os.path.join("data", "etf_fallback.json")
    collect_and_save_etf_data(output_file)
