from dataclasses import dataclass
from typing import Any, Dict, Optional


class ReprWithoutData:
    """
    Helper base class: `__repr__` generates a string representation without the `data` field.
    """

    def __repr__(self) -> str:
        attributes = vars(self).copy()
        if "data" in attributes:
            del attributes["data"]
        values = ("{}={!r}".format(key, value) for key, value in attributes.items())
        return "{}({})".format(self.__class__.__name__, ", ".join(values))


@dataclass
class StateName:
    """
    Pair of (state, name) used for enums or type representations.

    Attributes:
        state (str): Machine-readable value.
        name (str): Human-readable name.
    """

    state: str
    name: str


@dataclass
class BitgetCredentials:
    """
    Bitget API key credentials.

    Attributes:
        api_key (str): API Key.
        secret_key (str): Secret Key.
        passphrase (str): API passphrase (trade password phrase).
    """

    api_key: str
    secret_key: str
    passphrase: str

    def completely_filled(self) -> bool:
        """
        Check if all credential fields are filled.
        """
        return all((self.api_key, self.secret_key, self.passphrase))


class Methods:
    """HTTP request methods."""

    GET = "GET"
    POST = "POST"


class Chains:
    """
    Partial list of network names used on Bitget.
    Note: exact chain codes are returned by the `/api/v2/spot/public/coins` endpoint under `chains[*].chain`.
    This list is only for convenient name comparison and display.
    """

    ERC20 = "ERC20"
    TRC20 = "TRC20"
    BEP20 = "BSC"
    ArbitrumOne = "Arbitrum One"
    Optimism = "Optimism"
    Polygon = "Polygon"
    Solana = "Solana"
    Bitcoin = "Bitcoin"
    Ton = "TON"
    AvalancheC = "Avalanche C-Chain"
    Base = "Base"
    zkSyncEra = "zkSync Era"

    all_chains = {
        "erc20": ERC20,
        "trc20": TRC20,
        "bsc": BEP20,
        "arbitrum one": ArbitrumOne,
        "optimism": Optimism,
        "polygon": Polygon,
        "solana": Solana,
        "bitcoin": Bitcoin,
        "ton": Ton,
        "avalanche c-chain": AvalancheC,
        "base": Base,
        "zksync era": zkSyncEra,
    }

    @staticmethod
    def are_equal(chain_1: str, chain_2: str) -> bool:
        """Compare chain names case-insensitively."""
        return (chain_1 or "").lower() == (chain_2 or "").lower()


class FundingToken(ReprWithoutData):
    """
    Model representing a token balance (Bitget Spot Wallet balance).

    Expected Bitget API fields in `data.details[*]`:
      - `coin`
      - `available` (available balance)
      - `frozen` / `locked` (frozen balance)
      - sometimes `balance` / `total` — total balance

    We try to carefully compute `bal`, `availBal`, and `frozenBal` from these fields.
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        self.data: Dict[str, Any] = data
        self.token_symbol: str = data.get("coin") or data.get("ccy") or ""

        # Helper: safely convert value to float
        def _to_float(x: Optional[Any]) -> float:
            try:
                return float(x)
            except (TypeError, ValueError):
                return 0.0

        available = _to_float(data.get("available") or data.get("availBal"))
        frozen = _to_float(data.get("frozen") or data.get("locked") or data.get("freeze") or data.get("frozenBal"))
        total = _to_float(data.get("balance") or data.get("total") or data.get("bal"))

        # Derive missing total or frozen values if not provided
        if total == 0.0:
            total = available + frozen
        if frozen == 0.0 and total >= available:
            frozen = total - available

        self.bal: float = total
        self.availBal: float = available
        self.frozenBal: float = frozen


@dataclass
class AccountType(StateName):
    """Bitget account type used for transfers and balances."""

    pass


class AccountTypes:
    """Reference of minimal Bitget account types."""

    Spot = AccountType(state="spot", name="spot")
    Margin = AccountType(state="margin", name="margin")

    types_dict: Dict[str, AccountType] = {
        "spot": Spot,
        "margin": Margin,
    }
