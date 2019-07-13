import sys
import typing
from pathlib import Path

import aiofiles
import aiohttp
from loguru import logger


def configure_verbosity(log_level: str = 'INFO'):
    logger.configure(handlers=[dict(sink=sys.stderr, level=log_level)])


async def _get_request(
    session: aiohttp.ClientSession, url: str, *, return_type: typing.Type = bytes
) -> typing.AnyStr:
    async with session.get(url) as response:
        logger.debug(f'Got answer from {url}')
        if return_type is str:
            return await response.text()
        return await response.read()


async def _download_url(
    session: aiohttp.ClientSession,
    url: str,
    save_path: Path,
    *,
    return_type: typing.Type = bytes,
) -> None:
    logger.debug(f'Downloading {url}...')
    data: bytes = await _get_request(session, url, return_type=return_type)
    async with aiofiles.open(save_path, 'wb') as save_file:
        await save_file.write(data)
    logger.info(f'Downloaded {url} to {url}.')