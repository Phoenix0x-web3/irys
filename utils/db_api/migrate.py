from sqlalchemy import Column, String, Integer, text, create_engine
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from loguru import logger
from datetime import datetime,timedelta

from utils.db_api.db import DB
from utils.db_api.models import Wallet

db = DB("sqlite:///files/wallets.db")
db.ensure_model_columns(model=Wallet)

