import random
from datetime import datetime

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column
from data.settings import Settings

class Base(DeclarativeBase):
    pass

class Wallet(Base):
    __tablename__ = 'wallets'

    id: Mapped[int] = mapped_column(primary_key=True)
    private_key: Mapped[str] = mapped_column(unique=True, index=True)
    address: Mapped[str] = mapped_column(unique=True)
    proxy_status: Mapped[str] = mapped_column(default="OK", nullable=True)
    proxy: Mapped[str] = mapped_column(default=None, nullable=True)
    twitter_token: Mapped[str] = mapped_column(default=None, nullable=True)
    twitter_status: Mapped[str] = mapped_column(default="OK", nullable=True)
    typing_level: Mapped[int] = mapped_column(nullable=False)
    completed_games: Mapped[int] = mapped_column(nullable=False, default=0)
    points: Mapped[int] = mapped_column(nullable=True, default=None)
    rank: Mapped[int] = mapped_column(nullable=True, default=None)
    completed: Mapped[bool] = mapped_column(default=False)
    next_game_action_time: Mapped[datetime] = mapped_column(default=datetime.now)


    def __repr__(self):
        if Settings().show_wallet_address_log:
            return f'[{self.id}][{self.address}]'
        return f'[{self.id}]'
        
