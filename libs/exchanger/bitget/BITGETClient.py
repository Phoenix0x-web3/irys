from typing import Optional

import requests

from libs.exchanger.bitget.asset.Asset import Asset
from libs.exchanger.bitget.exceptions import InvalidProxy
from libs.exchanger.bitget.models import BitgetCredentials
from libs.exchanger.bitget.subaccount.Subaccount import Subaccount


class BitgetClient:
    """
    Client for interacting with the Bitget API (minimal version).

    Attributes:
        entrypoint_url (str): Base URL for Bitget API.
        proxy (Optional[str]): HTTP or SOCKS5 IPv4 proxy string.
    """

    __credentials: BitgetCredentials
    entrypoint_url: str
    proxy: Optional[str] = None

    _CANDIDATE_ENDPOINTS = (
        "https://api.bitget.com",
        "https://api.bitgetglobal.com",
        "https://capi.bitget.com",
    )

    def __init__(
        self,
        credentials: BitgetCredentials,
        entrypoint_url: str = "https://api.bitget.com",
        proxy: Optional[str] = None,
        check_proxy: bool = True,
    ) -> None:
        """
        Initialize a Bitget API client.

        Args:
            credentials (BitgetCredentials): Object containing Bitget API keys.
            entrypoint_url (str): Starting API URL (default: https://api.bitget.com).
            proxy (Optional[str]): HTTP/SOCKS5 IPv4 proxy string, accepted formats:
                - login:password@proxy:port
                - http://login:password@proxy:port
                - socks5://login:password@proxy:port
                - proxy:port
                - http://proxy:port
            check_proxy (bool): Whether to verify proxy connectivity (default: True).
        """
        self.__credentials = credentials
        self.entrypoint_url = entrypoint_url

        if proxy:
            try:
                if "http" not in proxy and "socks5" not in proxy:
                    proxy = f"http://{proxy}"
                if "socks5" in proxy and "socks5h" not in proxy:
                    proxy = proxy.replace("socks5", "socks5h")

                self.proxy = proxy
                if check_proxy:
                    your_ip = requests.get(
                        "http://eth0.me/",
                        proxies={"http": self.proxy, "https": self.proxy},
                        timeout=10,
                    ).text.rstrip()
                    if your_ip not in proxy:
                        raise InvalidProxy(f"Proxy doesn't work! Your IP is {your_ip}.")
            except InvalidProxy:
                pass
            except Exception as e:
                raise InvalidProxy(str(e))

        self._ensure_reachable_endpoint()

        self.asset = Asset(credentials=self.__credentials, entrypoint_url=self.entrypoint_url, proxy=self.proxy)
        self.subaccount = Subaccount(credentials=self.__credentials, entrypoint_url=self.entrypoint_url, proxy=self.proxy)

    def _ensure_reachable_endpoint(self) -> None:
        """
        Check if the current API entrypoint is reachable; if not, automatically switch to the first available fallback domain.
        """

        proxies = {"http": self.proxy, "https": self.proxy}

        if not self._probe_endpoint(self.entrypoint_url, proxies):
            for url in self._CANDIDATE_ENDPOINTS:
                if self._probe_endpoint(url, proxies):
                    self.entrypoint_url = url
                    break

    @staticmethod
    def _probe_endpoint(base_url: str, proxies: dict) -> bool:
        """
        Return True if Bitget's public time endpoint responds successfully (HTTP 2xx).

        Args:
            base_url (str): The base API URL to check.
            proxies (dict): Proxy settings for requests.

        Returns:
            bool: True if endpoint responds with HTTP 200-series code.
        """
        try:
            resp = requests.get(f"{base_url}/api/v2/public/time", proxies=proxies, timeout=10)
            return resp.ok
        except requests.exceptions.RequestException:
            return False
