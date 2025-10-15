from dataclasses import dataclass
from typing import Any, Dict, Optional

from libs.exchanger.bitget.models import ReprWithoutData, StateName


@dataclass
class SubaccountType(StateName):
    """
    Represents a single subaccount type in the Bitget system.
    Used for identifying whether an account is standard, managed, or custody type.
    """

    pass


class SubaccountTypes:
    """
    Registry of all available Bitget subaccount types.

    Attributes:
        Standard: Regular subaccount type.
        ManagedTrading: Managed trading subaccount type.
        Custody: Custody subaccount type.
        types_dict: Mapping of type code → SubaccountType.
    """

    Standard = SubaccountType(state="1", name="standard")
    ManagedTrading = SubaccountType(state="2", name="managed trading")
    Custody = SubaccountType(state="5", name="custody")

    types_dict = {"1": Standard, "2": ManagedTrading, "5": Custody}


class SubaccountInfo(ReprWithoutData):
    """
    Represents a Bitget subaccount, including its status, permissions, and metadata.

    Attributes:
        data (Dict[str, Any]): Raw API response data.
        enable (bool): Whether the subaccount is active (True = normal, False = frozen).
        subAcct (str): Subaccount identifier (can be UID, name, or alias).
        type (Optional[SubaccountTypes]): Type of subaccount.
        label (str): Custom label or note associated with the subaccount.
        mobile (Optional[str]): Mobile number linked to the subaccount.
        gAuth (bool): Whether Google Authenticator is enabled for login.
        canTransOut (bool): Whether this subaccount can transfer out funds.
        ts (int): Account creation timestamp (seconds since epoch).
    """

    def __init__(self, data: Dict) -> None:
        """
        Initializes a SubaccountInfo instance from raw Bitget API data.

        Args:
            data (Dict[str, Any]): Raw dictionary returned by Bitget subaccount endpoint.
        """
        self.data: Dict[str, Any] = data
        enable_raw = data.get("enable")
        if enable_raw is None:
            status = data.get("status", "").lower()
            if status in ("enabled", "normal"):
                self.enable = True
            elif status in ("frozen", "disabled"):
                self.enable = False
            else:
                self.enable = False
        else:
            self.enable = enable_raw
        self.subAcct: Optional[str] = data.get("subAcct") or data.get("subAccount") or data.get("subUid") or data.get("uid") or data.get("name")
        type_key = str(data.get("type") or data.get("accountType") or data.get("accType") or "")
        self.type: Optional[SubaccountTypes] = SubaccountTypes.types_dict.get(type_key)
        self.label: str = data.get("label") or data.get("note") or ""
        self.mobile: Optional[str] = data.get("mobile") or data.get("phone")
        g_auth_raw = data.get("gAuth")
        if g_auth_raw is None:
            self.gAuth: bool = bool(data.get("googleAuth"))
        else:
            self.gAuth = g_auth_raw
        can_trans_out_raw = data.get("canTransOut")
        if can_trans_out_raw is None:
            self.canTransOut: bool = bool(data.get("transferOut"))
        else:
            self.canTransOut = can_trans_out_raw
        ts_raw = data.get("ts") or data.get("cTime") or data.get("createTime")
        self.ts: int = int(int(ts_raw) / 1000) if ts_raw else 0
