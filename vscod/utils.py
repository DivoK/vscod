import re
import sys
import typing
from pathlib import Path

import aiofiles
import aiohttp
from loguru import logger


def configure_verbosity(log_level: str = 'INFO', *, quiet: bool = False):
    """
    Configure the default logger's verbosity.

    :param log_level: The minimum log level, defaults to 'INFO'
    :type log_level: str, optional
    :param quiet: Overrides the log level and turns off the logger, defaults to False
    :type quiet: bool, optional
    """
    logger.configure(handlers=[dict(sink=sys.stderr, level=log_level)] if not quiet else [])


async def get_original_filename(session: aiohttp.ClientSession, url: str) -> str:
    """
    Get the original filename of a desired download link.
    This uses either the `Content-Disposition` header if exists and fallbacks on the url.

    :param session: The session through which to make the request.
    :type session: aiohttp.ClientSession
    :param url: The desired url to get the filename of.
    :type url: str
    :return: The original url filename.
    :rtype: str
    """
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
    """
    Make an asynchronous get request.

    :param session: The session through which to make the request.
    :type session: aiohttp.ClientSession
    :param url: The desired url to get.
    :type url: str
    :param return_type: What type should the returned data be in, defaults to bytes
    :type return_type: typing.Type, optional
    :return: The url's data in the desired type.
    :rtype: typing.AnyStr
    """
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
    """
    Get a url's data and download it to a file.

    :param session: The session through which to make the request.
    :type session: aiohttp.ClientSession
    :param url: The desired url to download.
    :type url: str
    :param save_path: Where to save the downloaded data.
    :type save_path: Path
    :param return_type: What type should the returned data be in, defaults to bytes
    :type return_type: typing.Type, optional
    :return: None.
    :rtype: None
    """
    logger.debug(f'Downloading {url}...')
    data: bytes = await get_request(session, url, return_type=return_type)
    async with aiofiles.open(save_path, 'wb') as save_file:
        await save_file.write(data)
    logger.info(f'Downloaded {url} to {url}.')
