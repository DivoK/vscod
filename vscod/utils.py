import re
import sys
import typing
from pathlib import Path

import aiofiles
import aiohttp
from loguru import logger


def configure_verbosity(log_level: str = 'INFO', *, quiet: bool = False):
    logger.configure(handlers=[dict(sink=sys.stderr, level=log_level)] if not quiet else [])


async def get_original_filename(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url) as response:
        content_disposition = response.headers.get('Content-Disposition')
        if content_disposition:
            name = re.findall('filename=(.+);', content_disposition)[0]
        else:
            name = Path(str(response.url)).name
        logger.debug(f'{url} file name is {name}.')
        return name


async def get_request(
    session: aiohttp.ClientSession, url: str, *, return_type: typing.Type = bytes
) -> typing.AnyStr:
    async with session.get(url) as response:
        logger.debug(f'Got answer from {url}')
        if return_type is str:
            return await response.text()
        return await response.read()


async def download_url(
    session: aiohttp.ClientSession,
    url: str,
    save_path: Path,
    *,
    return_type: typing.Type = bytes,
) -> None:
    logger.debug(f'Downloading {url}...')
    data: bytes = await get_request(session, url, return_type=return_type)
    async with aiofiles.open(save_path, 'wb') as save_file:
        await save_file.write(data)
    logger.info(f'Downloaded {url} to {url}.')