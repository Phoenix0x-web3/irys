import asyncio
import random

from loguru import logger

from data.models import bitget_credentials
from data.settings import Settings
from libs.exchanger.bitget.asset.models import Currency, TransactionTypes, Withdrawal
from libs.exchanger.bitget.BITGETClient import BitgetClient
from libs.exchanger.bitget.exceptions import APIException
from libs.exchanger.bitget.models import AccountTypes, BitgetCredentials, Chains
from utils.db_api.models import Wallet


async def bitget_withdraw(wallet: Wallet, amount, chain, symbol):
    """
    Initiate a withdrawal from Bitget to a given wallet address.

    This function creates a BitgetActions instance and attempts to withdraw the specified
    amount of a token to the provided wallet address and chain. It logs actions and
    errors, and sleeps for a random duration between withdrawals to avoid hitting rate limits.

    Args:
        wallet (Wallet): The wallet object containing the destination address.
        amount: Amount of the token to withdraw.
        chain: Blockchain network (e.g., 'ETH', 'Optimism').
        symbol: Token symbol (e.g., 'ETH').

    Returns:
        str: "Success" if withdrawal is initiated successfully, None otherwise.
    """

    logger.info(f"Bitget | {wallet.address} - Trying to withdraw {symbol} on {chain} ")

    try:
        bitget = BitgetActions(credentials=bitget_credentials)

        res = await bitget.withdraw(to_address=str(wallet.address), amount=amount, token_symbol=symbol, chain=chain)

        if "Failed" not in str(res):
            logger.success(f"{wallet}: {res} | Bitget withdraw successfully with {wallet.address} on {chain}")

            sleep = random.randint(180, 360)
            logger.debug(f"{wallet.address} | Sleeping between withdraws: {sleep} secs")
            await asyncio.sleep(sleep)
            return "Success"
        else:
            logger.error(f"Error in withdraw via Bitget to {chain}")

    except Exception as error:
        logger.error(f"{wallet}: {error} | For {chain}")


class BitgetActions:
    """
    Wrapper class for BitgetClient providing higher-level operations for asset management,
    subaccount fund collection, withdrawal operations, and utility queries.

    This class encapsulates common workflows and logic for interacting with Bitget's
    API, such as collecting funds from subaccounts, initiating withdrawals, resolving
    chain names, checking withdrawal status, and querying fees or minimums.
    """

    def __init__(self, credentials: BitgetCredentials):
        self.entrypoint_url = "https://api.bitget.com"
        self.credentials = credentials
        self.bitget_client = None
        self.client = None

        if self.credentials.completely_filled():
            self.client = BitgetClient(credentials=credentials, entrypoint_url=self.entrypoint_url)

    async def all_balances_are_zero(self) -> bool:
        """
        Check that all subaccounts have zero available ETH on spot wallet.

        Returns:
            bool: True if all subaccounts have zero available ETH, False otherwise.
        """
        # Iterate over all subaccounts
        for subaccount_name in await self.client.subaccount.list():
            balances = await self.client.subaccount.asset_balances(subAcct=subaccount_name, token_symbol="ETH")
            # Check if any balance is nonzero
            for balance in balances.values():
                if balance.availBal > 0:
                    return False
        return True

    async def collect_funds_from_subaccounts(self):
        """
        Transfer available ETH from all subaccounts to the master spot wallet.

        Iterates through each subaccount, and if any ETH is available, transfers it
        internally to the master account's spot wallet.
        """

        for subaccount_name in await self.client.subaccount.list():
            balances = await self.client.subaccount.asset_balances(subAcct=subaccount_name, token_symbol="ETH")
            for balance in balances.values():
                avail_bal = balance.availBal
                if avail_bal > 0:
                    await self.client.asset.transfer(
                        token_symbol="ETH",
                        amount=avail_bal,
                        to_=AccountTypes.Spot,
                        subAcct=subaccount_name,
                        type=TransactionTypes.Internal,
                    )

    async def get_master_acc_balance(self, token_symbol: str = "ETH") -> float | int:
        """
        Fetch the available balance of a specific token in the master Bitget account.

        Args:
            token_symbol (str): The token symbol to check (default: "ETH").

        Returns:
            float | int: The available balance of the token.
        """
        balances = await self.client.asset.balances(token_symbol)
        return balances[token_symbol].availBal

    async def get_subaccounts_frozen_balances(self):
        """
        Calculate the total frozen ETH balance across all subaccounts.

        Returns:
            float | int: The sum of frozen ETH balances in all subaccounts.
        """
        total_frozen_bal = 0

        for subaccount_name in await self.client.subaccount.list():
            balances = await self.client.subaccount.asset_balances(subAcct=subaccount_name, token_symbol="ETH")
            for balance in balances.values():
                frozen_bal = balance.frozenBal
                if frozen_bal > 0:
                    total_frozen_bal += frozen_bal
        return total_frozen_bal

    async def get_minimal_withdrawal(self, token_symbol: str, chain: str) -> float | None:
        """
        Return minimal withdrawal amount for the given token and chain on Bitget.

        Args:
            token_symbol (str): The token symbol (e.g., "ETH").
            chain (str): The blockchain network (e.g., "Optimism").

        Returns:
            float | None: The minimum withdrawal amount if found, else None.

        Notes:
            Matches chain names case-/format-insensitively across common fields in the Bitget API.
        """

        def _norm(x: str) -> str:
            return "".join(ch for ch in x.lower() if ch.isalnum()) if isinstance(x, str) else ""

        token_symbol = (token_symbol or "").upper()
        want = _norm(chain or "")

        currencies = await self.client.asset.currencies(token_symbol=token_symbol)
        currency: Currency | None = currencies.get(token_symbol)
        if not currency:
            currency = currencies.get(token_symbol.lower()) or currencies.get(token_symbol.upper())
            if not currency:
                return None

        raw = getattr(currency, "data", None) or {}
        chains = currency.chains or raw.get("chains") or raw.get("networks") or raw.get("chainList") or []
        if not isinstance(chains, list):
            return None

        target = None
        for c in chains:
            if not isinstance(c, dict):
                continue
            names = [
                c.get("chain"),
                c.get("chainName"),
                c.get("network"),
                c.get("name"),
                c.get("symbol"),
                c.get("chainSymbol"),
                c.get("withdrawChain"),
                c.get("displayName"),
            ]
            names = [n for n in names if isinstance(n, str)]
            if any(_norm(n) == want for n in names) or any(want in _norm(n) or _norm(n) in want for n in names):
                target = c
                break
        if target is None:
            return None

        for key in ("minWithdrawAmount", "minWithdraw", "minWd", "min", "minAmount"):
            val = target.get(key)
            if val is None:
                continue
            try:
                return float(val)
            except (TypeError, ValueError):
                try:
                    return float(str(val))
                except Exception:
                    pass
        return None

    async def get_withdrawal_fee(self, token_symbol: str, chain: str) -> float | None:
        """
        Return withdrawal fee for a given token and chain, if Bitget exposes it in public coins data.

        Args:
            token_symbol (str): The token symbol (e.g., "ETH").
            chain (str): The blockchain network (e.g., "Optimism").

        Returns:
            float | None: The withdrawal fee if found, else None.

        Notes:
            Tries multiple common field names and matches chain name case-/format-insensitively.
        """

        def _norm(x: str) -> str:
            return "".join(ch for ch in x.lower() if ch.isalnum()) if isinstance(x, str) else ""

        token_symbol = (token_symbol or "").upper()
        want = _norm(chain or "")

        coins = await self.client.asset.currencies(token_symbol=token_symbol)
        info: Currency | None = coins.get(token_symbol)
        if not info:
            info = coins.get(token_symbol.lower()) or coins.get(token_symbol.upper())
        if not info:
            return None

        raw = getattr(info, "data", None) or {}
        chains = raw.get("chains") or raw.get("networks") or raw.get("chainList") or info.chains or []
        if not isinstance(chains, list):
            return None

        target = None
        for c in chains:
            if not isinstance(c, dict):
                continue
            names = [
                c.get("chain"),
                c.get("chainName"),
                c.get("network"),
                c.get("name"),
                c.get("symbol"),
                c.get("chainSymbol"),
                c.get("withdrawChain"),
                c.get("displayName"),
            ]
            names = [n for n in names if isinstance(n, str)]
            if any(_norm(n) == want for n in names) or any(want in _norm(n) or _norm(n) in want for n in names):
                target = c
                break
        if target is None:
            return None

        fee_keys = ("withdrawFee", "wdFee", "chainFee", "fee", "networkFee", "minFee", "fixedFee")
        for k in fee_keys:
            v = target.get(k)
            if v is None:
                continue
            try:
                return float(v)
            except (TypeError, ValueError):
                try:
                    return float(str(v))
                except Exception:
                    pass
        return None

    async def try_to_get_tx_hash(self, wd_id: str | int) -> str | None:
        """
        Fetch the transaction hash for a withdrawal by any known id type (orderId/wdId/clientOid).

        Args:
            wd_id (str | int): The withdrawal identifier (orderId, wdId, or clientOid).

        Returns:
            str | None: The transaction hash if found, else None.
        """
        if wd_id is None:
            return None
        wd_str = str(wd_id)

        candidates = []
        try:
            if wd_str.isdigit():
                candidates.append(await self.client.asset.withdrawal_history(orderId=wd_str, limit=50))
                candidates.append(await self.client.asset.withdrawal_history(wdId=wd_str, limit=50))
            candidates.append(await self.client.asset.withdrawal_history(clientId=wd_str, limit=50))
        except Exception:
            pass

        def _tx_from_record(rec: Withdrawal) -> str | None:
            if not isinstance(rec, Withdrawal):
                return None
            tx = getattr(rec, "txId", None)
            if tx:
                return tx
            raw = getattr(rec, "data", None) or getattr(rec, "__dict__", None) or {}
            if isinstance(raw, dict):
                for k in ("txId", "txHash", "hash", "transactionHash", "txid"):
                    if raw.get(k):
                        return raw.get(k)
            return None

        def _is_same_withdrawal(target: str, rec: Withdrawal) -> bool:
            raw = getattr(rec, "data", None) or getattr(rec, "__dict__", None) or {}
            vals = [getattr(rec, "wdId", None), getattr(rec, "clientId", None)]
            if isinstance(raw, dict):
                vals.extend([raw.get("wdId"), raw.get("withdrawalId"), raw.get("orderId"), raw.get("clientOid"), raw.get("bizId")])
            vals = [str(v) for v in vals if v is not None]
            return target in vals

        for hist in candidates:
            if not hist:
                continue
            for _, rec in hist.items():
                if _is_same_withdrawal(wd_str, rec):
                    txh = _tx_from_record(rec)
                    if txh:
                        return txh
        return None

    async def _resolve_chain_name(self, token_symbol: str, user_chain: str) -> str | None:
        """
        Map a user-supplied chain name (e.g. 'arbitrum', 'Arbitrum One') to the exact Bitget chain string.

        Args:
            token_symbol (str): The token symbol (e.g., "ETH").
            user_chain (str): The user-supplied chain name.

        Returns:
            str | None: The canonical Bitget chain name if found, else None.

        Notes:
            Reads /api/v2/spot/public/coins via asset.currencies() and matches case-/format-insensitively.
        """

        def _norm(x: str) -> str:
            return "".join(ch for ch in x.lower() if ch.isalnum()) if isinstance(x, str) else ""

        token_symbol = (token_symbol or "").upper()
        want = _norm(user_chain or "")
        if not want:
            return None

        coins = await self.client.asset.currencies(token_symbol=token_symbol)
        info = coins.get(token_symbol) or coins.get(token_symbol.lower()) or coins.get(token_symbol.upper())
        if not info:
            return None

        raw = getattr(info, "data", None) or {}
        chains = raw.get("chains") or raw.get("networks") or raw.get("chainList") or []
        if not isinstance(chains, list):
            return None

        for c in chains:
            if not isinstance(c, dict):
                continue
            names = [
                c.get("chain"),
                c.get("chainName"),
                c.get("network"),
                c.get("name"),
                c.get("symbol"),
                c.get("chainSymbol"),
                c.get("withdrawChain"),
                c.get("displayName"),
            ]
            names = [n for n in names if isinstance(n, str)]
            if any(_norm(n) == want for n in names) or any(want in _norm(n) or _norm(n) in want for n in names):
                return c.get("chainName") or c.get("displayName") or c.get("withdrawChain") or c.get("chain") or c.get("network") or names[0]
        return None

    async def withdraw(
        self,
        to_address: str,
        amount: float | int | str,
        token_symbol: str = "ETH",
        chain: str = Chains.Optimism,
    ) -> bool | int:
        """
        Initiate a withdrawal from Bitget to an external address.

        Args:
            to_address (str): The destination address for the withdrawal.
            amount (float | int | str): The amount to withdraw.
            token_symbol (str): The token symbol (default: "ETH").
            chain (str): The blockchain network (default: Chains.Optimism).

        Returns:
            bool | int: The withdrawal id if successful, False otherwise.

        Notes:
            Handles API and generic exceptions, and attempts to resolve the chain name
            to Bitget's canonical value before initiating the withdrawal.
        """
        failed_text = "Failed to withdraw from Bitget"
        try:
            if not self.client:
                logger.error(f"{failed_text}: there is no Bitget client")
                return False

            resolved_chain = await self._resolve_chain_name(token_symbol, chain)
            if not resolved_chain:
                logger.error(f"Failed to withdraw from Bitget: cannot resolve chain name '{chain}' for {token_symbol}")
                return False

            logger.info(f"Bitget withdraw | {to_address} | {token_symbol} on '{resolved_chain}' amount={amount}")

            try:
                withdrawal_token = await self.client.asset.withdrawal(
                    token_symbol=token_symbol,
                    amount=amount,
                    toAddr=to_address,
                    chain=resolved_chain,
                    dest=TransactionTypes.OnChain,
                )
            except APIException as e:
                logger.error(f"Bitget API withdraw failed | code={getattr(e, 'code', None)} | msg={str(e)}")
                return False
            except Exception as e:
                logger.error(f"Unexpected withdraw error: {e}")
                return False

            raw = getattr(withdrawal_token, "data", None) if hasattr(withdrawal_token, "data") else None
            candidates = [
                getattr(withdrawal_token, "wdId", None),
                getattr(withdrawal_token, "clientId", None),
                raw.get("withdrawalId") if isinstance(raw, dict) else None,
                raw.get("orderId") if isinstance(raw, dict) else None,
                raw.get("clientOid") if isinstance(raw, dict) else None,
            ]
            withdrawal_id = next((c for c in candidates if c), None)
            if withdrawal_id:
                return withdrawal_id

            safe_repr = None
            try:
                safe_repr = getattr(withdrawal_token, "__dict__", None) or str(withdrawal_token)
            except Exception:
                safe_repr = "<unrepr-withdrawal-token>"
            logger.error(f"{failed_text}! No id in response. token={safe_repr}")
            return False
        except APIException as e:
            logger.error(f"{to_address} | {e}")
            return False
        except BaseException as e:
            logger.exception(f"withdraw: {e}")
            return False

    async def check_withdrawal_status(
        self,
        settings: Settings,
        to_address: str,
        chain: str = Chains.Optimism,
    ) -> bool | None:
        """
        Check latest withdrawal records and return True if a matching transaction is completed.

        Args:
            settings (Settings): Settings object containing withdrawal timestamp limit.
            to_address (str): The destination address of the withdrawal.
            chain (str): The blockchain network (default: Chains.Optimism).

        Returns:
            bool | None: True if a matching withdrawal is completed, False if not found or not completed.

        Notes:
            Considers 'success', 'completed', 'done', 'finished' as completed states.
        """

        withdrawls_txs = await self.client.asset.withdrawal_history(token_symbol="ETH", before=settings.volume.timestamp)

        for wdId in withdrawls_txs:
            tx: Withdrawal = withdrawls_txs[wdId]
            if tx.chain == chain and tx.to_ == to_address:
                state = (tx.state.state or "").lower() if tx.state else ""
                if state in {"success", "completed", "done", "finished"}:
                    return True
                else:
                    return False

        return False
