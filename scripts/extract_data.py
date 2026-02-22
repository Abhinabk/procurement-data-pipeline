import requests
import os 
from dotenv import load_dotenv
import pandas as pd
import time
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from pathlib import Path
import sys

#force --cli flag to redownload data even exists

force = "--force" in sys.argv
#loads my key from .env 
load_dotenv()

base_url = "https://api.data.gov.in"
resource_path = ['/resource/91e35f71-68d2-4e77-ae6b-e5a16642ffc1',
             '/resource/d9a9fd53-4edd-4f65-8dcd-d5844f7fa76e',
             '/resource/64fa2910-4d48-469d-92d8-d00086d1e462',
             '/resource/deadcf24-4261-4574-b766-ccb377dd0f3b',
             '/resource/fbf7f636-5926-41d5-b168-b030c3415a5c',
             '/resource/48571d3f-38c8-4cba-b94f-fa12dddbdcdf'
             ]

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY not found in environment variables")

def fetch_dataset(url, api_key, file_path, limit=100, offset=0,sleep_time=4):

    resource_id = url.split("/")[-1]
    output_dir = Path(file_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check if file already exists, skip if not --force flag used
    existing_files = list(output_dir.glob(f"{resource_id}*.csv"))
    if existing_files and not force:
        print(f"Skipping {resource_id} — already exists. Use --force to redownload.")
        return

    session = requests.Session()
    retries = Retry(
        total=5,                   # total retries
        backoff_factor=2,          # 2s → 4s → 8s → 16s…
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))

    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    params = {
        "api-key":api_key,
        "format":"json",
        "offset":offset,
        "limit":limit

    }

    all_data = []
    total = None
    # handling pagenation +offset tille no record
    while True:
        params['offset'] = offset

        try:
            response = session.get(url=url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            records = data.get('records', [])

            if total is None:
                total = data.get('total', 0)
                print("Total records:", total)
        except Exception as e:
            print("Request failed:", e)
            break

        if not records:
            break

        all_data.extend(records)
        offset+=limit
        print(f"Fetched {len(all_data)} / {total} records (offset={offset})")
        if offset >= total:
            break
        #sending frequent requests
        time.sleep(sleep_time)  

    df = pd.DataFrame(all_data)
    os.makedirs(file_path, exist_ok=True)
    resource_id = url.split("/")[-1]

    if not df.empty and 'fiscal_year' in df.columns:
        fiscal = str(df.loc[0, 'fiscal_year']).replace("-", "_")
        filename = f"{resource_id}_{fiscal}"
    else:
        filename =resource_id

    csv_path =  output_dir / f"{filename}.csv"
    df.to_csv(csv_path,index=False)
    print("Saved:", csv_path)


if __name__== "__main__":
    for fp in resource_path:
        url = base_url+fp
        fetch_dataset(url,API_KEY,file_path="data")
        time.sleep(2)