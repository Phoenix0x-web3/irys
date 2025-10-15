from dataclasses import dataclass
from typing import Any, Dict, Optional

from libs.exchanger.bitget.models import AccountType, AccountTypes, ReprWithoutData, StateName


class Currency(ReprWithoutData):
    """
    Represents a currency/coin on Bitget (response from /api/v2/spot/public/coins).

    Main fields:
        • `coin` — symbol of the currency.
        • `chains` — list of supported networks.
    This model keeps raw data and provides convenient helper fields.
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        self.data: Dict[str, Any] = data
        self.token_symbol: str = data.get("coin")
        self.chains: list = data.get("chains", [])
        self.canDep: Optional[bool] = data.get("depositable")
        self.canWd: Optional[bool] = data.get("withdrawable")
        self.chain: Optional[str] = None


@dataclass
class TransactionType(StateName):
    """Represents a withdrawal or transfer type on Bitget."""

    pass


class TransactionTypes:
    """Registry of supported transaction types for Bitget withdrawals and transfers."""

    Internal = TransactionType(state="inner_transfer", name="internal")
    OnChain = TransactionType(state="on_chain", name="on-chain")


@dataclass
class DepositStatus(StateName):
    """Represents a deposit status as returned by the Bitget API."""

    pass


class DepositStatuses:
    """
    Mapping of deposit statuses.
    Bitget returns string status values; we keep an empty dict and handle unknown values gracefully.
    """

    statuses_dict: Dict[str, DepositStatus] = {}


class Deposit(ReprWithoutData):
    """
    Represents a deposit record (response from /api/v2/spot/wallet/deposit-records).

    Safely parses Bitget responses which may differ between API versions.
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        self.data: Dict[str, Any] = data
        self.token_symbol: Optional[str] = data.get("coin") or data.get("ccy")
        self.chain: Optional[str] = data.get("chain")
        # amount
        size = data.get("size") or data.get("amt")
        self.amt: float = float(size) if size is not None else 0.0
        self.from_: Optional[str] = data.get("from")
        self.areaCodeFrom: Optional[str] = data.get("areaCodeFrom")
        self.to_: Optional[str] = data.get("to") or data.get("address")
        self.txId: Optional[str] = data.get("txId") or data.get("hash")
        ts = data.get("ts") or data.get("cTime") or data.get("createTime")
        self.ts: int = int(int(ts) / 1000) if ts else 0
        raw_state = str(data.get("state")) if data.get("state") is not None else None
        self.state: Optional[DepositStatus] = (DepositStatuses.statuses_dict.get(raw_state) if raw_state is not None else None) or (
            DepositStatus(state=raw_state or "", name=raw_state or "")
        )
        dep_id = data.get("id") or data.get("depId")
        self.depId: int = int(dep_id) if dep_id is not None else 0
        self.fromWdId: Optional[int] = None
        if data.get("fromWdId") is not None:
            try:
                self.fromWdId = int(data.get("fromWdId"))
            except (TypeError, ValueError):
                self.fromWdId = None

        try:
            self.actualDepBlkConfirm: Optional[int] = int(data.get("confirmations") or data.get("actualDepBlkConfirm"))
        except (TypeError, ValueError):
            self.actualDepBlkConfirm = None


@dataclass
class WithdrawalStatus(StateName):
    """Represents a withdrawal status from Bitget API."""

    pass


class WithdrawalStatuses:
    """
    Mapping of withdrawal statuses.
    """

    statuses_dict: Dict[str, WithdrawalStatus] = {}


class Withdrawal(ReprWithoutData):
    """
    Represents a withdrawal record (response from /api/v2/spot/wallet/withdrawal-records).
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        self.data: Dict[str, Any] = data
        self.chain: Optional[str] = data.get("chain")
        fee = data.get("fee")
        self.fee: float = float(fee) if fee is not None else 0.0
        self.token_symbol: Optional[str] = data.get("coin") or data.get("ccy")
        client = data.get("clientOid") or data.get("clientId")
        self.clientId: Optional[int] = None
        try:
            self.clientId = int(client) if client is not None else None
        except (TypeError, ValueError):
            # clientOid can be non-numeric — leave as None
            self.clientId = None
        size = data.get("size") or data.get("amt")
        self.amt: float = float(size) if size is not None else 0.0
        self.txId: Optional[str] = data.get("txId") or data.get("hash")
        self.from_: Optional[str] = data.get("from")
        self.areaCodeFrom: Optional[str] = data.get("areaCodeFrom")
        self.to_: Optional[str] = data.get("to") or data.get("address")
        self.areaCodeTo: Optional[str] = data.get("areaCodeTo")
        raw_state = str(data.get("state")) if data.get("state") is not None else None
        self.state: Optional[WithdrawalStatus] = (WithdrawalStatuses.statuses_dict.get(raw_state) if raw_state is not None else None) or (
            WithdrawalStatus(state=raw_state or "", name=raw_state or "")
        )
        ts = data.get("ts") or data.get("cTime") or data.get("createTime")
        self.ts: int = int(int(ts) / 1000) if ts else 0
        wd_id = data.get("id") or data.get("withdrawalId") or data.get("wdId")
        try:
            self.wdId: int = int(wd_id)
        except (TypeError, ValueError):
            self.wdId = 0
        self.nonTradableAsset: Optional[bool] = data.get("nonTradableAsset")
        self.tag: Optional[str] = data.get("tag")
        self.pmtId: Optional[str] = data.get("pmtId")
        self.memo: Optional[str] = data.get("memo")
        self.addrEx: Optional[str] = data.get("addrEx")
        self.feeCcy: Optional[str] = data.get("feeCcy")


class WithdrawalToken(ReprWithoutData):
    """
    Represents a withdrawal token/receipt (response from /api/v2/spot/wallet/withdrawal).

    Usually contains fields like `withdrawalId`, `clientOid`, `coin`, `chain`, and `size`.
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        self.data: Dict[str, Any] = data
        size = data.get("size") or data.get("amt")
        self.amt: float = float(size) if size is not None else 0.0
        wd = data.get("withdrawalId") or data.get("wdId")
        try:
            self.wdId: int = int(wd)
        except (TypeError, ValueError):
            self.wdId = 0
        self.token_symbol: Optional[str] = data.get("coin") or data.get("ccy")
        client = data.get("clientOid") or data.get("clientId")
        try:
            self.clientId: Optional[int] = int(client) if client is not None else None
        except (TypeError, ValueError):
            self.clientId = None
        self.chain: Optional[str] = data.get("chain")


@dataclass
class TransferType(StateName):
    """Represents a transfer type between accounts."""

    pass


class TransferTypes:
    """
    Registry of transfer types. Values remain compatible with existing code.
    """

    WithinAccount = TransferType(state="0", name="within account")
    MasterToSub = TransferType(state="1", name="master to sub")
    SubToMasterMasterKey = TransferType(state="2", name="sub to master master key")
    SubToMasterSubKey = TransferType(state="3", name="sub to master sub key")
    SubToSub = TransferType(state="4", name="sub to sub")

    statuses_dict = {
        "0": WithinAccount,
        "1": MasterToSub,
        "2": SubToMasterMasterKey,
        "3": SubToMasterSubKey,
        "4": SubToSub,
    }


class Transfer(ReprWithoutData):
    """
    Represents an internal transfer record (response from /api/v2/spot/wallet/transfer).
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        self.data: Dict[str, Any] = data

        trans = data.get("transferId") or data.get("transId") or data.get("id")
        try:
            self.transId: int = int(trans)
        except (TypeError, ValueError):
            self.transId = 0

        client = data.get("clientOid") or data.get("clientId")
        try:
            self.clientId: Optional[int] = int(client) if client is not None else None
        except (TypeError, ValueError):
            self.clientId = None
        self.token_symbol: Optional[str] = data.get("coin") or data.get("ccy")

        frm = data.get("fromType") or data.get("from")
        to = data.get("toType") or data.get("to")
        self.from_: Optional[AccountType] = AccountTypes.types_dict.get(str(frm)) if frm is not None else None

        size = data.get("size") or data.get("amt")
        self.amt: float = float(size) if size is not None else 0.0
        self.to_: Optional[AccountType] = AccountTypes.types_dict.get(str(to)) if to is not None else None
