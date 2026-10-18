"""Download NLR GenAI power profile dataset (OpenEI submission 8651, CC BY 4.0)."""
from common import RAW, download, today, update_source

URL = "https://data.nlr.gov/system/files/312/1775845072-dataset.zip"

if __name__ == "__main__":
    download(URL, RAW / "nlr_genai" / "dataset.zip")
    update_source("F1b", url="https://data.openei.org/submissions/8651", license="CC BY 4.0",
                  version="data from 2026-03-31, last updated 2026-07-17", download_date=today())
