import asyncio
import random
import string
from datetime import datetime, timedelta

from faker import Faker
from loguru import logger

from libs.base import Base
from libs.eth_async.client import Client
from utils.browser import Browser
from utils.db_api.models import Wallet


class AuthClient(Base):
    BASE_LINK = "https://graphigo.prd.galaxy.eco/query"

    def __init__(self, wallet: Wallet, browser: Browser, client: Client):
        self.client = client
        self.wallet = wallet
        self.browser = browser

    async def login(self):
        logger.debug(f"{self.wallet} | {self.__module__} | starting authorizate")
        check_exist = await self.check_exist()
        sign_in = await self.sign_in()
        if not sign_in:
            raise Exception("Can't sign in")
        if not check_exist:
            await self.create_new_account(sign_in)
        return sign_in

    async def create_new_account(self, bearer_token: str):
        username = await self.generate_random_username()
        headers = {"authorization": bearer_token}
        json_data = {
            "operationName": "CreateNewAccount",
            "variables": {
                "input": {
                    "schema": f"EVM:{self.wallet.address}",
                    "socialUsername": f"{username}",
                    "username": f"{username}",
                },
            },
            "query": "mutation CreateNewAccount($input: CreateNewAccount!) {\n  createNewAccount(input: $input)\n}",
        }
        response = await self.browser.post(url=self.BASE_LINK, json=json_data, headers=headers)
        data = response.json()
        if data["data"]["createNewAccount"]:
            logger.success(f"{self.wallet} success register on Galxe with nickname {username}")
        return data["data"]["createNewAccount"]

    async def generate_random_username(self):
        faker = Faker()
        while True:
            username = faker.user_name()
            json_data = {
                "operationName": "UserNameExists",
                "variables": {
                    "username": f"{username}",
                },
                "query": "query UserNameExists($username: String!) {\n  userNameExists(username: $username) {\n    exists\n    errorMessage\n    __typename\n  }\n}",
            }
            response = await self.browser.post(url=self.BASE_LINK, json=json_data)
            data = response.json()
            if not data["data"]["userNameExists"]["exists"]:
                return username
            await asyncio.sleep(2)
            continue

    async def check_exist(self):
        json_data = {
            "operationName": "GalxeIDExist",
            "variables": {
                "schema": f"EVM:{self.wallet.address}",
            },
            "query": "query GalxeIDExist($schema: String!) {\n  galxeIdExist(schema: $schema)\n}",
        }
        response = await self.browser.post(url=self.BASE_LINK, json=json_data)
        data = response.json()
        if isinstance(data, dict):
            return data["data"]["galxeIdExist"]

    def generate_random_string(self, length=17):
        characters = string.ascii_uppercase + string.ascii_lowercase + string.digits
        random_string = "".join(random.choice(characters) for _ in range(length))
        return random_string

    async def sign_in(self):
        current_time = datetime.utcnow()
        expiration_time = current_time + timedelta(days=7)
        current_time = current_time.isoformat("T") + "Z"
        expiration_time = expiration_time.isoformat("T") + "Z"
        message = {
            "domain": "app.galxe.com",
            "address": self.wallet.address,
            "statement": "Sign in with Ethereum to the app.",
            "uri": "https://app.galxe.com",
            "version": "1",
            "chainId": 1,
            "nonce": self.generate_random_string(),
            "issuedAt": current_time,
            "expiration": expiration_time,
        }

        message_str = (
            f"{message['domain']} wants you to sign in with your Ethereum account:\n"
            f"{message['address']}\n\n"
            f"{message['statement']}\n\n"
            f"URI: {message['uri']}\n"
            f"Version: {message['version']}\n"
            f"Chain ID: {message['chainId']}\n"
            f"Nonce: {message['nonce']}\n"
            f"Issued At: {message['issuedAt']}\n"
            f"Expiration Time: {message['expiration']}"
        )
        signature = await self.sign_message(text=message_str)
        json_data = {
            "operationName": "SignIn",
            "variables": {
                "input": {
                    "address": f"{self.wallet.address}",
                    "signature": signature,
                    "message": message_str,
                    "addressType": "EVM",
                    "publicKey": "1",
                },
            },
            "query": "mutation SignIn($input: Auth) {\n  signin(input: $input)\n}",
        }
        response = await self.browser.post(url=self.BASE_LINK, json=json_data)
        data = response.json()
        return data["data"]["signin"]
