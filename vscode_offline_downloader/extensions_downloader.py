import asyncio
import dataclasses
import json
import re
import sys
import typing
from pathlib import Path

import aiofiles
import aiohttp
from loguru import logger


MARKETPLACE_DOWNLOAD_LINK = '''
    https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{publisher_name}/vsextensions/{extension_name}/latest/vspackage
'''.strip()
MARKETPLACE_PAGE_LINK = '''
    https://marketplace.visualstudio.com/items?itemName={extension_id}
'''.strip()
VERSION_REGEX = re.compile(r'"Version":"(.*?)"')


@dataclasses.dataclass
class ExtensionPath:
    path: Path
    extension_id: str


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


async def _download_extension(
    session: aiohttp.ClientSession, extension_name: str, publisher_name: str, save_path: Path
) -> None:
    logger.info(f'Downloading {extension_name}...')
    url = MARKETPLACE_DOWNLOAD_LINK.format(
        extension_name=extension_name, publisher_name=publisher_name
    )
    data: bytes = await _get_request(session, url)
    async with aiofiles.open(save_path, 'wb') as save_file:
        await save_file.write(data)
    logger.info(f'Downloaded {extension_name} to {save_path}.')


async def download_extension_by_id(
    session: aiohttp.ClientSession, extension_id: str, save_path: Path
) -> None:
    publisher_name, extension_name = extension_id.split('.')
    await _download_extension(session, extension_name, publisher_name, save_path)


def _recursive_parse_to_dict(
    root_dict: typing.Dict[str, typing.Union[str, typing.Dict]],
    *,
    append_name: typing.Optional[bool] = None,
) -> typing.List[ExtensionPath]:
    if append_name is None:
        append_name = False
    path_list = []
    for key, value in root_dict.items():
        if isinstance(value, str):
            if not value:
                raise ValueError(f'Value for key {key} was empty.')
            path_list.append(
                ExtensionPath(Path(key) / f'{value}._' if append_name else '', value)
            )
        elif isinstance(value, dict):
            for ext_path in _recursive_parse_to_dict(value):
                ext_path.path = Path(key, ext_path.path)
                path_list.append(ext_path)
        else:
            raise TypeError(f'Value for key {key} was neither str or dict.')
    return path_list


def parse_extensions_json(
    json_path: Path, *, append_name: typing.Optional[bool] = None
) -> typing.List[ExtensionPath]:
    if append_name is None:
        append_name = False
    with json_path.open() as json_file:
        extensions_dict = json.load(json_file)
    return _recursive_parse_to_dict(extensions_dict, append_name=append_name)


async def get_extension_version(session: aiohttp.ClientSession, extension_id: str) -> str:
    logger.debug(f'Requesting version of extension {extension_id}...')
    url = MARKETPLACE_PAGE_LINK.format(extension_id=extension_id)
    text: str = await _get_request(session, url, return_type=str)
    match = re.search(r'"Version":"(.*?)"', text)
    if not match:
        raise ValueError('Extension marketplace page data doesn\'t contain a version.')
    version = match.group(1)  # The captured version specifier.
    logger.debug(f'Extension {extension_id} is of version {version}.')
    return version


async def versionize_extension_paths(
    session: aiohttp.ClientSession, extension_paths: typing.List[ExtensionPath]
) -> None:
    get_version_tasks = [
        get_extension_version(session, ext_path.extension_id) for ext_path in extension_paths
    ]
    versions = await asyncio.gather(*get_version_tasks)
    for ext_path, version in zip(extension_paths, versions):
        ext_path.path = ext_path.path.with_suffix(f'.{version}._')


async def download_extensions_json(
    json_path: Path, save_path: Path, *, versioned: typing.Optional[bool] = None
) -> None:
    if versioned is None:
        versioned = False
    extension_paths = parse_extensions_json(json_path, append_name=True)
    async with aiohttp.ClientSession() as session:
        if versioned:
            await versionize_extension_paths(session, extension_paths)
        download_extension_tasks = []
        for ext_path in extension_paths:
            extension_full_save_path = save_path / ext_path.path.with_suffix('.vsix')
            extension_full_save_path.parent.mkdir(parents=True, exist_ok=True)
            download_extension_tasks.append(
                download_extension_by_id(
                    session, ext_path.extension_id, extension_full_save_path
                )
            )
        await asyncio.gather(*download_extension_tasks)


if __name__ == '__main__':
    import time

    start = time.time()
    logger.info('START')
    asyncio.run(
        download_extensions_json(
            Path('vscode_offline_downloader/extensions.json'),
            Path('downloads'),
            versioned=True,
        )
    )
    logger.info(f'END: execution time = {time.time() - start}')
