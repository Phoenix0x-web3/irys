async def secs_to_millisecs(secs: int | float | str) -> int:
    secs = int(secs)
    return secs * 1000 if len(str(secs)) == 10 else secs
