import asyncio
import logging
from logging import Logger
from typing import Optional
import base64

import aiohttp

from .const import BASE_URL
from .exceptions import (
    Trading212InvalidParameter,
    Trading212NotFound,
    Trading212BadApiKey,
    Trading212Limited,
    Trading212ScopeError,
    Trading212TimeOut,
    Trading212Error,
    Trading212AttemptsExceeded,
)

logger: Logger = logging.getLogger(__package__)


class Trading212API:
    """
    A class that creates an API object, to be used to call against the Trading 212 API

    Attributes
    ----------
    auth_token : str
        once autherntiacted the auth token will be stored in the object to be used for future api calls
    session : aiohttp.ClientSession
        The aiohttp session is stored to be called against

    Methods
    -------
    close:
        Closes the aiohttp ClientSession that is stored in the session variable
    request:
        get the current data from the api and returns the json response given
    """

    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        session: aiohttp.ClientSession = None,
    ) -> None:
        """
        Sets all the necessary variables for the API caller based on the passed in information, if a session is not passed in then one is created

        Parameters
        ---------
        auth_token (str):Once authentiacted the auth token will be stored in the object to be used for future api calls
        session (aiohttp.ClientSession), optional:The aiohttp session is stored to be called against
        """

        if not api_key or not api_secret:
            raise ValueError("auth_token is required")

        authroisation = f"{api_key}:{api_secret}"

        encoded_authorisation = base64.b64encode(authroisation.encode("utf-8")).decode(
            "utf-8"
        )
        self.session = session

        if self.session is None:
            self.session = aiohttp.ClientSession()

        self._headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.67",
            "Authorization": f"Basic {encoded_authorisation}",
        }

    async def close(self) -> None:
        """
        Closes the aiohttp ClientSession

        Returns
        -------
        None
        """
        if self.session:
            await self.session.close()

    async def check_response(self, response: aiohttp.ClientResponse):
        """
        Checks API response and raises relevant exceptions.

        Parameters:
        -----------
        response : aiohttp.ClientResponse
            The response object to check.

        Raises:
        -------
        Trading212BadApiKey: If API key is invalid.
        Trading212ScopeError: If access is forbidden.
        Trading212TimeOut: If request times out.
        Trading212Limited: If rate-limited.
        Trading212Error: For other errors.
        """
        if response.status == 200:
            return

        error_text = await response.text()

        match response.status:
            case 400:
                raise Trading212InvalidParameter(error_text)
            case 401:
                raise Trading212BadApiKey(error_text)
            case 403:
                raise Trading212ScopeError(error_text)
            case 404:
                raise Trading212NotFound(error_text)
            case 408:
                raise Trading212TimeOut(error_text)
            case 429:
                raise Trading212Limited(
                    int(response.headers.get("x-ratelimit-period", 5))
                )
            case _:
                raise Trading212Error(
                    f"Unexpected Error {response.status}: {error_text}"
                )

    async def _get(self, endpoint: str, retries: int = 3) -> dict:
        """Helper function for making GET requests."""
        url = f"{BASE_URL}{endpoint}"

        for attempt in range(retries):
            try:
                async with self.session.get(
                    url, headers=self._headers, timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    await self.check_response(response)
                    return await response.json()

            except Trading212Limited as e:
                if attempt == retries - 1:
                    raise Trading212AttemptsExceeded(
                        f"Requests still limited after {attempt + 1} attempts"
                    )

                logger.warning(
                    "Rate limited. Retry %s/%s in %s seconds.",
                    attempt + 1,
                    retries,
                    e.retry_after,
                )
                await asyncio.sleep(e.retry_after)

        raise Trading212AttemptsExceeded("Rate limit exceeded")

    async def get_positions(self, ticker: Optional[str] = None) -> dict:
        """
        Method for calling the Trading212 API for open positions

        Returns
        ------
        dict: Dictionary containing the response
        """
        return await self._get(
            f"equity/portfolio/{ticker}" if ticker else "equity/portfolio"
        )

    async def get_exchanges(self) -> dict:
        """
        Method for calling the Trading212 API for exchanges

        Returns
        ------
        dict: Dictionary containing the response
        """
        return await self._get("metadata/exchanges")

    async def get_instruments(self) -> dict:
        """
        Method for calling the Trading212 API for instruments

        Returns
        ------
        dict: Dictionary containing the response
        """
        return await self._get("metadata/instruments")

    async def get_orders(self, order: Optional[int] = None) -> dict:
        """
        Method for calling the Trading212 API for returning equity orders

        Returns
        ------
        dict: Dictionary containing the response
        """
        return await self._get(f"equity/orders/{order}" if order else "equity/orders")

    async def get_account_metadata(self) -> dict:
        """
        Method for calling the Trading212 API for returning account info

        Returns
        ------
        dict: Dictionary containing the response
        """
        return await self._get("equity/account/summary")
