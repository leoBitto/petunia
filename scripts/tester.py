from src.drive_manager import DriveManager

def main():
    dm = DriveManager()
    tickers = dm.get_universe_tickers()
    print(f"{len(tickers)} tickers trovati:")
    print(tickers[:10])
    print("_"*50)
    secret = dm._get_secret("db_info")
    print(f"secret: {secret}")
    print(f"secret type: {type(secret)}")

if __name__ == "__main__":
    main()
