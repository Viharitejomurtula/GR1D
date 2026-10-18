"""Download NASA PCoE Capacitor Electrical Stress dataset (#12; electrolytic capacitors at 10/12/14 V stress)."""
from common import RAW, download, today, update_source

URL = "https://phm-datasets.s3.amazonaws.com/NASA/12.+Capacitor+Electrical+Stress.zip"

if __name__ == "__main__":
    download(URL, RAW / "nasa_capacitor" / "12.Capacitor_Electrical_Stress.zip")
    update_source("F2f", url="https://www.nasa.gov/content/prognostics-center-of-excellence-data-set-repository",
                  license="NASA public data (verify)", version="PCoE #12 Capacitor Electrical Stress", download_date=today())
