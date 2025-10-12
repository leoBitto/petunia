from src.drive_manager import DriveManager

def main():
    dm = DriveManager()
    tickers = dm.get_universe_tickers()
    print(f"{len(tickers)} tickers trovati:")
    print(tickers[:10])

if __name__ == "__main__":
    main()
