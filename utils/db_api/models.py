from datetime import datetime

from sqlalchemy import JSON
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from data.constants import PROJECT_SHORT_NAME
from data.settings import Settings


class Base(DeclarativeBase):
    pass


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(primary_key=True)
    private_key: Mapped[str] = mapped_column(unique=True, index=True)
    address: Mapped[str] = mapped_column(unique=True)
    proxy_status: Mapped[str] = mapped_column(default="OK", nullable=True)
    proxy: Mapped[str] = mapped_column(default=None, nullable=True)
    galxe_account_banned: Mapped[bool] = mapped_column(default=False)
    galxe_tokens_win: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)
    twitter_token: Mapped[str] = mapped_column(default=None, nullable=True)
    twitter_status: Mapped[str] = mapped_column(default="OK", nullable=True)
    typing_level: Mapped[int] = mapped_column(nullable=False)
    completed_games: Mapped[int] = mapped_column(nullable=False, default=0)
    points: Mapped[int] = mapped_column(nullable=True, default=None)
    rank: Mapped[int] = mapped_column(nullable=True, default=None)
    completed: Mapped[bool] = mapped_column(default=False)
    next_action_time: Mapped[datetime] = mapped_column(default=datetime.now)
    next_game_action_time: Mapped[datetime] = mapped_column(default=datetime.now)
    last_faucet_claim: Mapped[datetime | None] = mapped_column(default=None)

    def __repr__(self):
        if Settings().show_wallet_address_logs:
            return f"[{PROJECT_SHORT_NAME} | {self.id} | {self.address}]"
        return f"[{PROJECT_SHORT_NAME} | {self.id}]"
