"""Download the public large fraud benchmark used by evaluate_real_fraud.py."""
from pathlib import Path
from urllib.request import urlopen

TARGET = Path(__file__).parent / "real" / "creditcard.csv"
URL = "https://raw.githubusercontent.com/IBM/xgboost-smote-detect-fraud/master/data/creditcard.csv"

def main():
    TARGET.parent.mkdir(exist_ok=True)
    if TARGET.exists():
        print(f"Already present: {TARGET}")
        return
    with urlopen(URL, timeout=60) as source, TARGET.open("wb") as destination:
        while chunk := source.read(1024 * 1024):
            destination.write(chunk)
    print(f"Downloaded {TARGET}")

if __name__ == "__main__":
    main()
