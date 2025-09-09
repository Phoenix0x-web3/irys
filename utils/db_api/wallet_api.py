from utils.db_api.models import Base, Wallet
from utils.db_api.db import DB

from data.config import WALLETS_DB


def get_wallets(sqlite_query: bool = False) -> list[Wallet]:
    if sqlite_query:
        return db.execute('SELECT * FROM wallets')

    return db.all(entities=Wallet)


def get_wallet_by_private_key(private_key: str, sqlite_query: bool = False) -> Wallet | None:
    if sqlite_query:
        return db.execute('SELECT * FROM wallets WHERE private_key = ?', (private_key,), True)

    return db.one(Wallet, Wallet.private_key == private_key)
  
def get_wallet_by_address(address: str, sqlite_query: bool = False) -> Wallet | None:
    if sqlite_query:
        return db.execute('SELECT * FROM wallets WHERE address = ?', (address,), True)

    return db.one(Wallet, Wallet.address == address)

def update_next_game_time(address:str, next_game_action_time) -> bool:
    wallet = db.one(Wallet, Wallet.address == address)
    if not wallet:
        return False
    wallet.next_game_action_time = next_game_action_time
    db.commit()
    return True
  

def add_count_game(address: str) -> bool:

    wallet = db.one(Wallet, Wallet.address == address)
    if not wallet:
        return False
    if not wallet.completed_games:
        wallet.completed_games = 1
    
    wallet.completed_games += 1
    db.commit()
    return True

def replace_bad_proxy(id: int, new_proxy: str) -> bool:
    wallet = db.one(Wallet, Wallet.id == id)
    if not wallet:
        return False
    wallet.proxy = new_proxy
    wallet.proxy_status = "OK"
    db.commit()
    return True

def replace_bad_twitter(id: int, new_token: str) -> bool:
    wallet = db.one(Wallet, Wallet.id == id)
    if not wallet:
        return False
    wallet.twitter_token = new_token
    wallet.twitter_status = "OK"
    db.commit()
    return True

def mark_proxy_as_bad(id: int) -> bool:
    wallet = db.one(Wallet, Wallet.id == id)
    if not wallet:
        return False
    wallet.proxy_status = "BAD"
    db.commit()
    return True

def mark_twitter_as_bad(id: int) -> bool:
    wallet = db.one(Wallet, Wallet.id == id)
    if not wallet:
        return False
    wallet.twitter_status = "BAD"
    db.commit()
    return True

def get_wallets_with_bad_proxy() -> list:
    return db.all(Wallet, Wallet.proxy_status == "BAD")

def get_wallets_with_bad_twitter() -> list:
    return db.all(Wallet, Wallet.twitter_status == "BAD")

db = DB(f'sqlite:///{WALLETS_DB}', echo=False, pool_recycle=3600, connect_args={'check_same_thread': False})
db.create_tables(Base)
