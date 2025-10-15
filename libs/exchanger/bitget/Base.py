import base64
import hmac
import json
import time
from datetime import datetime
from urllib.parse import urlencode

from libs.eth_async.utils.web_requests import async_get, async_post
from libs.exchanger.bitget import exceptions
from libs.exchanger.bitget.models import BitgetCredentials, Methods


class Base:
    """
    The base class for all section classes.

    Attributes:
        entrypoint_url (str): an entrypoint URL.
        proxy (str): an HTTP or SOCKS5 IPv4 proxy dictionary.
        connector (Optional[ProxyConnector]): a connector.

    """

    __credentials: BitgetCredentials
    entrypoint_url: str
    proxy: str | None
    # connector: ProxyConnector | TCPConnector = TCPConnector(force_close=True)

    def __init__(self, credentials: BitgetCredentials, entrypoint_url: str, proxy: str | None) -> None:
        """
        Initialize the class.

        Args:
            credentials (BitgetCredentials): an instance with all Bitget API key data.
            entrypoint_url (str): an API entrypoint url.
            proxy (Optional[str]): an HTTP or SOCKS5 IPv4 proxy in one of the following formats:
                - login:password@proxy:port
                - http://login:password@proxy:port
                - socks5://login:password@proxy:port
                - proxy:port
                - http://proxy:port

        """
        self.__credentials = credentials
        self.entrypoint_url = entrypoint_url
        self.proxy = proxy

    _time_offset_ms: int = 0

    @staticmethod
    def _now_ms() -> int:
        """Current local timestamp in milliseconds."""
        return int(time.time() * 1000)

    async def _sync_time(self) -> None:
        """Synchronize local time offset using Bitget public endpoint `/api/v2/public/time`."""
        url = self.entrypoint_url + "/api/v2/public/time"
        try:
            resp = await async_get(url=url, headers={"Accept": "application/json"}, proxy=self.proxy)
            if isinstance(resp, dict):
                server_ms = None
                if isinstance(resp.get("data"), dict):
                    server_ms = resp.get("data", {}).get("serverTime")
                elif resp.get("data") is not None:
                    server_ms = resp.get("data")
                if server_ms is None and resp.get("requestTime") is not None:
                    server_ms = resp.get("requestTime")
                if server_ms is not None:
                    self._time_offset_ms = int(server_ms) - self._now_ms()
        except Exception:
            pass

    def _timestamp_with_offset(self) -> str:
        """Returns a millisecond timestamp adjusted by the cached Bitget time offset."""
        return str(self._now_ms() + self._time_offset_ms)

    @staticmethod
    async def get_timestamp() -> str:
        """Current UTC timestamp in milliseconds as a string (Bitget v2 format)."""
        return str(int(datetime.utcnow().timestamp() * 1000))

    async def generate_sign(self, timestamp: str, method: str, request_path: str, body: dict | str) -> bytes:
        """
        Generate signed message for Bitget V2 API.

        Args:
            timestamp (str): the current timestamp.
            method (str): the request method is either GET or POST.
            request_path (str): the path of requesting an endpoint.
            body (Union[dict, str]): POST request parameters.

        Returns:
            bytes: the signed message.

        """
        if not body:
            body = ""

        if isinstance(body, dict):
            body = json.dumps(body)

        key = bytes(self.__credentials.secret_key, encoding="utf-8")
        msg = bytes(timestamp + method + request_path + body, encoding="utf-8")
        return base64.b64encode(hmac.new(key, msg, digestmod="sha256").digest())

    async def make_request(self, method: str, request_path: str, body: dict | None = None) -> dict[str, ...] | None:
        """
        Make a signed request to the Bitget API.

        Args:
            method (str): HTTP method, either "GET" or "POST".
            request_path (str): Endpoint path starting with "/api/...".
            body (Optional[dict]): Request parameters/body (None by default).

        Returns:
            Optional[dict[str, ...]]: Parsed JSON response.
        """
        if self._time_offset_ms == 0:
            await self._sync_time()
        timestamp = self._timestamp_with_offset()
        method = method.upper()
        body = body if body else {}
        proxy = self.proxy

        if method == Methods.GET and body:
            request_path += f"?{urlencode(query=body, doseq=True)}"
            body = {}

        body_to_send: str | dict
        body_str_for_sign = ""
        if method == Methods.GET:
            body_to_send = {}
            body_str_for_sign = ""
        else:
            if isinstance(body, dict):
                body_str_for_sign = json.dumps(body, separators=(",", ":"))
                body_to_send = body_str_for_sign
            else:
                body_str_for_sign = body or ""
                body_to_send = body_str_for_sign

        sign_msg = await self.generate_sign(
            timestamp=timestamp,
            method=method,
            request_path=request_path,
            body=body_str_for_sign,
        )
        url = self.entrypoint_url + request_path
        header = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "ACCESS-KEY": self.__credentials.api_key,
            "ACCESS-SIGN": sign_msg.decode(),
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self.__credentials.passphrase,
        }

        try:
            if method == Methods.POST:
                response = await async_post(url=url, headers=header, proxy=proxy, data=body_to_send)
            else:
                response = await async_get(url=url, headers=header, proxy=proxy)
        except Exception as err:
            status = getattr(err, "status", None) or getattr(err, "status_code", None)
            msg = getattr(err, "message", None) or str(err)
            raise exceptions.APIException(
                response={"code": "transport_error", "msg": msg},
                status_code=status,
            )

        if not isinstance(response, dict):
            raise exceptions.APIException(response=None, status_code=None)
        code = response.get("code")
        if code is None:
            return response

        if str(code) == "40008":
            await self._sync_time()

            timestamp = self._timestamp_with_offset()
            sign_msg = await self.generate_sign(
                timestamp=timestamp,
                method=method,
                request_path=request_path,
                body=body_str_for_sign,
            )
            header.update(
                {
                    "ACCESS-SIGN": sign_msg.decode(),
                    "ACCESS-TIMESTAMP": timestamp,
                }
            )
            try:
                if method == Methods.POST:
                    response = await async_post(url=url, headers=header, proxy=proxy, data=body_to_send)
                else:
                    response = await async_get(url=url, headers=header, proxy=proxy)
            except Exception as err:
                status = getattr(err, "status", None) or getattr(err, "status_code", None)
                msg = getattr(err, "message", None) or str(err)
                raise exceptions.APIException(response={"code": "transport_error", "msg": msg}, status_code=status)

            if not isinstance(response, dict):
                raise exceptions.APIException(response=None, status_code=None)
            code = response.get("code")

        if str(code) != "00000":
            raise exceptions.APIException(response=response)

        return response
