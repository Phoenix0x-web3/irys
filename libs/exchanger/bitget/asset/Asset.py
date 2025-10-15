import asyncio
from typing import Dict, Optional, Union

from libs.eth_async.utils.web_requests import request_params
from libs.exchanger.bitget.asset.models import (
    Currency,
    Deposit,
    DepositStatus,
    TransactionType,
    TransactionTypes,
    Transfer,
    TransferType,
    TransferTypes,
    Withdrawal,
    WithdrawalStatus,
    WithdrawalToken,
)
from libs.exchanger.bitget.Base import Base
from libs.exchanger.bitget.models import AccountType, AccountTypes, FundingToken, Methods


class Asset(Base):
    """
    Client class for the **Asset** section (spot wallets) of Bitget API v2.

    Provides methods for retrieving coin lists, balances, deposit/withdrawal histories,
    and for performing withdrawals and internal transfers (including subaccount ↔ master transfers).

    Attributes:
        section (str): API section name. For spot wallet, it is "spot/wallet".
    """

    section: str = "spot/wallet"

    _master_uid: Optional[str] = None

    async def _get_master_uid(self) -> str:
        """
        Fetches and caches the master account UID (userId) using `/api/v2/spot/account/info`.

        Returns:
            str: The user ID (as a string). Empty string if unavailable.
        """
        if self._master_uid:
            return self._master_uid
        resp = await self.make_request(
            method=Methods.GET,
            request_path="/api/v2/spot/account/info",
            body=request_params({}),
        )
        uid = str(resp.get("data", {}).get("userId", ""))
        if not uid:
            data = resp.get("data")
            if isinstance(data, list) and data:
                uid = str(data[0].get("userId", ""))
        self._master_uid = uid
        return uid

    async def _to_millis(self, ts: int) -> int:
        """
        Converts Unix time (seconds or milliseconds) to milliseconds.

        Args:
            ts (int): Timestamp in seconds or milliseconds.

        Returns:
            int: Timestamp in milliseconds.
        """
        try:
            res = secs_to_millisecs(secs=ts)
            if asyncio.iscoroutine(res):
                res = await res
            return int(res)
        except Exception:
            return int(ts * 1000)

    async def currencies(self, token_symbol: Optional[str] = None) -> Dict[str, Currency]:
        """
        Fetches a dictionary of supported coins on Bitget.

        Args:
            token_symbol (Optional[str]): Single or comma-separated list of coin symbols (e.g., "BTC" or "BTC,ETH").

        Returns:
            Dict[str, Currency]: Mapping of coin symbol → Currency object.
        """
        method = "spot/public/coins"
        params = {}
        if token_symbol:
            params["coin"] = token_symbol
        response = await self.make_request(
            method=Methods.GET,
            request_path=f"/api/v2/{method}",
            body=request_params(params),
        )
        currencies = {}
        for currency in response.get("data", []):
            currencies[currency.get("coin")] = Currency(data=currency)
        return currencies

    async def balances(self, token_symbol: Optional[str] = None) -> Dict[str, FundingToken]:
        """
        Retrieves balances for the **master account** spot wallet.

        Args:
            token_symbol (Optional[str]): Coin symbol filter (e.g., "ETH"). If None, returns all coins.

        Returns:
            Dict[str, FundingToken]: Mapping of coin symbol → FundingToken object containing available/frozen balances.
        """
        params = {}
        if token_symbol:
            params["coin"] = token_symbol

        response = await self.make_request(
            method=Methods.GET,
            request_path="/api/v2/spot/account/assets",
            body=request_params(params),
        )

        tokens: Dict[str, FundingToken] = {}
        data = response.get("data", {})
        rows = []
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            rows = data.get("assets") or data.get("details") or data.get("assetList") or []
        for token in rows:
            if not isinstance(token, dict):
                continue
            coin_code = token.get("coin") or token.get("symbol") or token.get("currency")
            if coin_code:
                tokens[coin_code] = FundingToken(data=token)
        return tokens

    async def deposit_history(
        self,
        token_symbol: Optional[str] = None,
        from_: Optional[str] = None,
        to_: Optional[str] = None,
        state: Optional[DepositStatus] = None,
        after: Optional[int] = None,
        before: Optional[int] = None,
        limit: int = 100,
    ) -> Dict[int, Deposit]:
        """
        Fetches deposit history records.

        Args:
            token_symbol (Optional[str]): Coin symbol (e.g., "BTC"). If None, returns all.
            from_ (Optional[str]): Deposit source address filter.
            to_ (Optional[str]): Deposit destination address filter.
            state (Optional[DepositStatus]): Deposit status filter.
            after (Optional[int]): Return records **after** this timestamp (s/ms).
            before (Optional[int]): Return records **before** this timestamp (s/ms).
            limit (int): Number of results (max 100).

        Returns:
            Dict[int, Deposit]: Mapping depositId → Deposit object.
        """
        method = "deposit-records"
        params = {
            "coin": token_symbol,
            "fromAddress": from_,
            "toAddress": to_,
            "state": state.state if state else None,
            "limit": limit,
        }
        if after is not None:
            params["startTime"] = after if after >= 10**12 else await self._to_millis(after)
        if before is not None:
            params["endTime"] = before if before >= 10**12 else await self._to_millis(before)

        response = await self.make_request(method=Methods.GET, request_path=f"/api/v2/{self.section}/{method}", body=request_params(params))
        deposits = {}
        for deposit in response.get("data", []):
            did = deposit.get("id")
            if did is None:
                continue
            try:
                key = int(str(did))
            except Exception:
                digits = "".join(ch for ch in str(did) if ch.isdigit())
                if not digits:
                    continue
                key = int(digits)
            deposits[key] = Deposit(data=deposit)
        return deposits

    async def withdrawal_history(
        self,
        token_symbol: Optional[str] = None,
        wdId: Optional[Union[str, int]] = None,
        clientId: Optional[Union[str, int]] = None,
        orderId: Optional[Union[str, int]] = None,
        toAddr: Optional[str] = None,
        chain: Optional[str] = None,
        state: Optional[WithdrawalStatus] = None,
        after: Optional[int] = None,
        before: Optional[int] = None,
        limit: int = 100,
    ) -> Dict[int, Withdrawal]:
        """
        Fetches withdrawal history records.

        Args:
            token_symbol (Optional[str]): Coin symbol (e.g., "ETH"). If None, returns all.
            wdId (Optional[Union[str, int]]): Withdrawal ID (withdrawalId).
            clientId (Optional[Union[str, int]]): Client-supplied ID (clientOid).
            orderId (Optional[Union[str, int]]): Internal Bitget order ID (v2).
            toAddr (Optional[str]): Destination address filter.
            chain (Optional[str]): Chain/network filter (e.g., "Optimism").
            state (Optional[WithdrawalStatus]): Withdrawal status filter.
            after (Optional[int]): Return records **after** this timestamp (s/ms).
            before (Optional[int]): Return records **before** this timestamp (s/ms).
            limit (int): Number of results (max 100).

        Returns:
            Dict[int, Withdrawal]: Mapping withdrawalId/orderId → Withdrawal object.

        Notes:
            • Normalizes transaction hash field to `txId` (aliases supported: txHash/hash/transactionHash/txid/chainTxHash/hashId/tx_id/tradeId).
            • Supports multiple possible record IDs (id/withdrawalId/wdId/orderId/clientOid/bizId).
        """
        method = "withdrawal-records"
        params = {
            "coin": token_symbol,
            "withdrawalId": str(wdId) if wdId else None,
            "clientOid": str(clientId) if clientId else None,
            "orderId": str(orderId) if orderId else None,
            "toAddress": toAddr,
            "chain": chain,
            "state": state.state if state else None,
            "pageSize": limit,
            "limit": limit,
        }
        if after is not None:
            params["startTime"] = after if after >= 10**12 else await self._to_millis(after)
        if before is not None:
            params["endTime"] = before if before >= 10**12 else await self._to_millis(before)

        response = await self.make_request(method=Methods.GET, request_path=f"/api/v2/{self.section}/{method}", body=request_params(params))
        withdrawals = {}
        for withdrawal in response.get("data", []):
            wid = (
                withdrawal.get("id")
                or withdrawal.get("withdrawalId")
                or withdrawal.get("wdId")
                or withdrawal.get("orderId")
                or withdrawal.get("clientOid")
                or withdrawal.get("bizId")
            )
            if wid is None:
                continue
            try:
                key = int(str(wid))
            except Exception:
                digits = "".join(ch for ch in str(wid) if ch.isdigit())
                if not digits:
                    continue
                key = int(digits)
            if isinstance(withdrawal, dict) and not withdrawal.get("txId"):
                for _alias in ("txHash", "hash", "transactionHash", "txid", "chainTxHash", "hashId", "tx_id", "tradeId"):
                    if withdrawal.get(_alias):
                        withdrawal["txId"] = withdrawal.get(_alias)
                        break
            withdrawals[key] = Withdrawal(data=withdrawal)
        return withdrawals

    async def withdrawal(
        self,
        token_symbol: str,
        amount: Union[float, int, str],
        toAddr: str,
        chain: str,
        dest: TransactionType = TransactionTypes.OnChain,
        fee: Optional[Union[float, int, str]] = None,
        clientId: Optional[Union[str, int]] = None,
    ) -> WithdrawalToken:
        """
        Creates a **withdrawal request** from the spot wallet.

        Args:
            token_symbol (str): Coin symbol (e.g., "ETH").
            amount (Union[float, int, str]): Withdrawal amount. Sent as string.
            toAddr (str): Destination address (must be whitelisted in Bitget address book).
            chain (str): Withdrawal network (e.g., "Optimism", "ERC20", "Arbitrum One").
            dest (TransactionType): Transaction type (default: on_chain).
            fee (Optional[Union[float, int, str]]): Optional fee if supported.
            clientId (Optional[Union[str, int]]): Client-supplied request ID (clientOid).

        Returns:
            WithdrawalToken: Response token with orderId/clientOid and related data.
        """
        method = "withdrawal"
        body = {
            "coin": token_symbol,
            "address": toAddr,
            "chain": chain,
            "size": str(amount),  # Bitget требует строку
            "transferType": "on_chain" if dest == TransactionTypes.OnChain else "inner_transfer",
        }

        if fee:
            body["fee"] = str(fee)
        if clientId:
            body["clientOid"] = str(clientId)

        response = await self.make_request(
            method=Methods.POST,
            request_path=f"/api/v2/{self.section}/{method}",
            body=request_params(body),
        )

        return WithdrawalToken(data=response.get("data"))

    async def cancel_withdrawal(self, wdId: Union[str, int]) -> str:
        """
        Cancels a withdrawal request.

        Args:
            wdId (Union[str, int]): Withdrawal ID.

        Returns:
            str: The canceled withdrawal ID returned by Bitget.
        """
        method = "cancel-withdrawal"
        body = {"withdrawalId": str(wdId)}
        response = await self.make_request(method=Methods.POST, request_path=f"/api/v2/{self.section}/{method}", body=request_params(body))
        return response.get("data", "")

    async def transfer(
        self,
        token_symbol: str,
        amount: Union[float, int, str],
        from_: AccountType = AccountTypes.Spot,
        to_: AccountType = AccountTypes.Margin,
        subAcct: Optional[str] = None,
        type: TransferType = TransferTypes.WithinAccount,
        clientId: Optional[Union[str, int]] = None,
    ) -> Transfer:
        """
        Performs an **internal transfer**:
        — Between account types (spot ↔ margin) within the same user, or
        — Between subaccount and master (via /subaccount-transfer).

        Args:
            token_symbol (str): Coin symbol (e.g., "USDT").
            amount (Union[float, int, str]): Transfer amount (sent as string).
            from_ (AccountType): Source account (default: spot).
            to_ (AccountType): Destination account (default: margin).
            subAcct (Optional[str]): Subaccount UID (if provided, uses /subaccount-transfer).
            type (TransferType): Transfer type.
            clientId (Optional[Union[str, int]]): Client-supplied request ID.

        Returns:
            Transfer: Transfer object containing transfer details.

        Notes:
            • If `subAcct` is provided, uses `/api/v2/spot/wallet/subaccount-transfer` and automatically fetches master UID.
            • Removes None fields from body; preserves zeros and empty strings.
        """

        request_path = f"/api/v2/{self.section}/transfer"  # /api/v2/spot/wallet/transfer
        body = {
            "coin": token_symbol,
            "amount": str(amount),  # Bitget expects string
            "fromType": from_.state if hasattr(from_, "state") else str(from_),
            "toType": to_.state if hasattr(to_, "state") else str(to_),
            "transferType": type.state if hasattr(type, "state") else str(type),
            "clientOid": str(clientId) if clientId else None,
        }
        if subAcct:
            request_path = "/api/v2/spot/wallet/subaccount-transfer"
            master_uid = await self._get_master_uid()
            body = {
                "coin": token_symbol,
                "amount": str(amount),
                "fromType": "spot",
                "toType": "spot",
                "fromUserId": str(subAcct),
                "toUserId": master_uid,
                "clientOid": str(clientId) if clientId else None,
            }

        body = {k: v for k, v in body.items() if v is not None}

        response = await self.make_request(
            method=Methods.POST,
            request_path=request_path,
            body=request_params(body),
        )
        return Transfer(data=response.get("data"))
