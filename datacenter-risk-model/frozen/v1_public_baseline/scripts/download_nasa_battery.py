"""Download the NASA PCoE Li-ion battery aging dataset (Saha & Goebel, 2007)."""
from common import RAW, download, today, update_source

URL = "https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip"

if __name__ == "__main__":
    download(URL, RAW / "nasa_battery" / "5.Battery_Data_Set.zip")
    update_source("F2d", url="https://www.nasa.gov/content/prognostics-center-of-excellence-data-set-repository",
                  license="NASA public data (verify)", version="PCoE Battery Data Set (S3 file dated 2022-09-18)",
                  download_date=today())
