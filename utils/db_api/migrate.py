from utils.db_api.db import DB
from utils.db_api.models import Wallet

db = DB("sqlite:///files/wallets.db")
db.ensure_model_columns(model=Wallet)
