import asyncio
import random
from datetime import datetime, timedelta
from typing import List
from loguru import logger

from functions.controller import Controller
from data.settings import Settings
from utils.encryption import check_encrypt_param
from utils.db_api.models import Wallet
from utils.db_api.wallet_api import db, update_next_game_time
from libs.eth_async.client import Client
from libs.eth_async.data.models import Networks

async def random_sleep_before_start(wallet):
    random_sleep = random.randint(Settings().random_pause_start_wallet_min, Settings().random_pause_start_wallet_max)
    now = datetime.now()

    logger.info(f"{wallet} Start at {now + timedelta(seconds=random_sleep)} sleep {random_sleep} seconds before start actions")
    await asyncio.sleep(random_sleep)
    
async def execute(wallets : List[Wallet], task_func, random_pause_wallet_after_completion : int = 0):
    while True:
        semaphore = asyncio.Semaphore(min(len(wallets), Settings().threads))

        if Settings().shuffle_wallets:
            random.shuffle(wallets)

        async def sem_task(wallet : Wallet):
            async with semaphore:
                try:
                    await task_func(wallet)
                except Exception as e:
                    logger.error(f"[{wallet.id}] failed: {e}")

        tasks = [asyncio.create_task(sem_task(wallet)) for wallet in wallets]
        await asyncio.gather(*tasks, return_exceptions=True)

        if random_pause_wallet_after_completion == 0:
            break
 
        # update dynamically the pause time
        random_pause_wallet_after_completion = random.randint(Settings().random_pause_wallet_after_completion_min,
                                                              Settings().random_pause_wallet_after_completion_max)
        
        next_run = datetime.now() + timedelta(seconds=random_pause_wallet_after_completion)
        logger.info(
            f"Sleeping {random_pause_wallet_after_completion} seconds. "
            f"Next run at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await asyncio.sleep(random_pause_wallet_after_completion)

async def activity(action: int):
    if not check_encrypt_param():
        logger.error(f"Decryption Failed | Wrong Password")
        return

    wallets = db.all(Wallet)
    range_wallets = Settings().range_wallets_to_run
    if range_wallets != [0, 0]: 
        start, end = range_wallets
        wallets = [
            wallet for i, wallet in enumerate(wallets, start=1)
            if start <= i <= end
        ]
    else:
        if Settings().exact_wallets_to_run:
            wallets = [
                wallet for i, wallet in enumerate(wallets, start=1)
                if i in Settings().exact_wallets_to_run
            ]

    logger.info(f"Found {len(wallets)} wallets for action")
    if action == 1 and wallets:
        await execute(wallets, start_main_action, random.randint(Settings().random_pause_wallet_after_completion_min, Settings().random_pause_wallet_after_completion_max))

    if action == 2 and wallets:
        await execute(wallets, complete_games,random.randint(Settings().random_pause_wallet_after_completion_min, Settings().random_pause_wallet_after_completion_max))

    if action == 3 and wallets:
        await execute(wallets, complete_galxe_quests)

async def start_main_action(wallet):
    now = datetime.now()
    if wallet.next_game_action_time >= now:
        return
    
    await random_sleep_before_start(wallet=wallet)
    
    client = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.Gravity)

    controller = Controller(client=client, wallet=wallet)

    c = await controller.complete_games()
    
    if c:
        now = datetime.now()
        if 20 >= random.randint(1, 100):
            random_delay = random.randint(Settings().random_pause_wallet_long_delay_min, Settings().random_pause_wallet_long_delay_max)
            next_time = now + timedelta(seconds=random_delay)
            await controller.complete_galxe_quests()
        else:
            random_delay = random.randint(Settings().random_pause_wallet_after_completion_min, Settings().random_pause_wallet_after_completion_max)
            next_time = now + timedelta(seconds=random_delay)
        success_update = update_next_game_time(address=wallet.address, next_game_action_time=next_time)
        if success_update:
            logger.info(f"{wallet} Next action scheduled at {next_time}")
        else:
            logger.error(f"{wallet} Failed to update next_game_action_time")

async def complete_galxe_quests(wallet):
    
    await random_sleep_before_start(wallet=wallet)
    
    client = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.Gravity)

    controller = Controller(client=client, wallet=wallet)

    await controller.complete_galxe_quests()
    
async def complete_games(wallet):
    now = datetime.now()
    if wallet.next_game_action_time >= now:
        return

    await random_sleep_before_start(wallet=wallet)
    
    client = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.Gravity)

    controller = Controller(client=client, wallet=wallet)

    c = await controller.complete_games()
    
    if c:
        now = datetime.now()
        if 20 >= random.randint(1, 100):
            random_delay = random.randint(Settings().random_pause_wallet_long_delay_min, Settings().random_pause_wallet_long_delay_max)
            next_time = now + timedelta(seconds=random_delay)
        else:
            random_delay = random.randint(Settings().random_pause_wallet_after_completion_min, Settings().random_pause_wallet_after_completion_max)
            next_time = now + timedelta(seconds=random_delay)
        success_update = update_next_game_time(address=wallet.address, next_game_action_time=next_time)
        if success_update:
            logger.info(f"{wallet} Next action scheduled at {next_time}")
        else:
            logger.error(f"{wallet} Failed to update next_game_action_time")
