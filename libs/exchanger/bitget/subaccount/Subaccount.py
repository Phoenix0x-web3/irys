from libs.eth_async.utils.web_requests import request_params
from libs.exchanger.bitget.Base import Base
from libs.exchanger.bitget.models import FundingToken, Methods


class Subaccount(Base):
    """
    Provides access to Bitget Subaccount API endpoints.

    This class implements methods for retrieving subaccount information and balances.
    It inherits request handling and authentication from Base.

    Attributes:
        section_user (str): Path prefix for subaccount-related API calls.
        section_spot (str): Path prefix for spot wallet-related API calls.
    """

    section_user: str = "user/subaccount"
    section_spot: str = "spot/wallet"

    async def list(self) -> list[str]:
        """
        Retrieve a list of subaccount IDs that currently hold non-zero spot balances.

        Endpoint:
            GET /api/v2/spot/account/subaccount-assets

        Returns:
            list[str]: A list of subaccount identifiers (UIDs or user IDs).

        Notes:
            • Bitget only returns subaccounts that have balances greater than zero.
            • The function tries to extract the most stable identifier available: subUid, subAccountUid, uid, userId, or id.
        """
        # Send request to Bitget to get all subaccount asset data
        response = await self.make_request(
            method=Methods.GET,
            request_path="/api/v2/spot/account/subaccount-assets",
            body=request_params({}),
        )
        # Prepare a list to store unique subaccount identifiers
        result: list[str] = []
        data = response.get("data", []) or []
        # Parse each returned record and extract subaccount ID
        for row in data:
            sub_id = row.get("subUid") or row.get("subAccountUid") or row.get("uid") or row.get("userId") or row.get("id")
            if sub_id is not None:
                result.append(str(sub_id))
        # Return list of all discovered subaccount UIDs
        return result

    async def asset_balances(self, subAcct: str, token_symbol: str | None = None) -> dict[str, FundingToken]:
        """
        Retrieve the token balances for a specific subaccount.

        Endpoint:
            GET /api/v2/spot/account/subaccount-assets

        Args:
            subAcct (str): Identifier (UID) of the subaccount.
            token_symbol (Optional[str]): If provided, filters results to a single token symbol.

        Returns:
            dict[str, FundingToken]: Dictionary of token symbol → FundingToken object.

        Notes:
            • Bitget does not provide a dedicated per-subaccount balance endpoint for standard accounts.
            • This method queries all subaccount assets and filters them by UID.
        """

        response = await self.make_request(
            method=Methods.GET,
            request_path="/api/v2/spot/account/subaccount-assets",
            body=request_params({}),
        )
        data = response.get("data", []) or []

        tokens: dict[str, FundingToken] = {}
        for row in data:
            sub_id = row.get("subUid") or row.get("subAccountUid") or row.get("uid") or row.get("userId") or row.get("id")

            if str(sub_id) != str(subAcct):
                continue

            assets = row.get("assetsList") or row.get("assets") or []
            for item in assets:
                coin = item.get("coin") or item.get("currency") or item.get("symbol")

                if not coin:
                    continue
                if token_symbol and coin.upper() != token_symbol.upper():
                    continue
                tokens[coin] = FundingToken(data=item)

            break

        return tokens
