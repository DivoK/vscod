import asyncio
import dataclasses
import json
import re
import typing
from pathlib import Path

import aiohttp
from loguru import logger

from .utils import download_url, get_request, get_original_filename

MARKETPLACE_DOWNLOAD_LINK = '''
    https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{publisher_name}/vsextensions/{extension_name}/{version}/vspackage
'''.strip()
MARKETPLACE_PAGE_LINK = '''
    https://marketplace.visualstudio.com/items?itemName={extension_id}
'''.strip()
VERSION_REGEX = re.compile(r'"Version":"(.*?)"')


@dataclasses.dataclass
class ExtensionPath:
    path: Path
    extension_id: str
    version: str = 'latest'


def _build_extension_download_url(
    extension_name: str, publisher_name: str, version: str
) -> str:
    return MARKETPLACE_DOWNLOAD_LINK.format(
        extension_name=extension_name, publisher_name=publisher_name, version=version
    )


def _build_extension_download_url_from_ext_path(ext_path: ExtensionPath) -> str:
    publisher_name, extension_name = ext_path.extension_id.split('.')
    return _build_extension_download_url(extension_name, publisher_name, ext_path.version)


async def _download_extension(
    session: aiohttp.ClientSession,
    extension_name: str,
    publisher_name: str,
    version: str,
    save_path: Path,
) -> None:
    logger.info(f'Downloading {extension_name}...')
    url = _build_extension_download_url(extension_name, publisher_name, version)
    await download_url(session, url, save_path, return_type=bytes)
    logger.info(f'Downloaded {extension_name} to {save_path}.')


async def download_extension_by_id(
    session: aiohttp.ClientSession, extension_id: str, version: str, save_path: Path
) -> None:
    publisher_name, extension_name = extension_id.split('.')
    await _download_extension(session, extension_name, publisher_name, version, save_path)


def _recursive_parse_to_dict(
    root_dict: typing.Dict[str, typing.Union[str, typing.Dict]],
) -> typing.List[ExtensionPath]:
    path_list = []
    for key, value in root_dict.items():
        if isinstance(value, str):
            if not value:
                raise ValueError(f'Value for key {key} was empty.')
            path_list.append(ExtensionPath(Path(key) / f'{value}', value))
        elif isinstance(value, dict):
            for ext_path in _recursive_parse_to_dict(value):
                ext_path.path = Path(key, ext_path.path)
                path_list.append(ext_path)
        else:
            raise TypeError(f'Value for key {key} was neither str or dict.')
    return path_list


def parse_extensions_json(
    json_data: typing.Union[typing.Dict[str, str], Path],
) -> typing.List[ExtensionPath]:
    if isinstance(json_data, Path):
        with json_data.open() as json_file:
            json_data = json.load(json_file)['extensions']
    return _recursive_parse_to_dict(json_data)


async def get_extension_version(session: aiohttp.ClientSession, extension_id: str) -> str:
    logger.debug(f'Requesting version of extension {extension_id}...')
    url = MARKETPLACE_PAGE_LINK.format(extension_id=extension_id)
    try:
        text: str = await get_request(session, url, return_type=str)
        match = re.search(r'"Version":"(.*?)"', text)
        if not match:
            raise ValueError('Extension marketplace page data doesn\'t contain a version.')
        version = match.group(1)  # The captured version specifier.
    except Exception as error:
        logger.debug(error)
        logger.warning('Can\'t get extension version, setting version to \'latest\'...')
        version = 'latest'
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
        # ext_path.path = ext_path.path.with_suffix(f'.{version}._')
        ext_path.version = version


async def patch_extension_paths(
    session: aiohttp.ClientSession,
    extension_paths: typing.List[ExtensionPath],
    *,
    versionize: bool = True,
) -> None:
    if versionize:
        await versionize_extension_paths(session, extension_paths)
    real_name_tasks = [
        get_original_filename(session, _build_extension_download_url_from_ext_path(ext_path))
        for ext_path in extension_paths
    ]
    original_filenames = await asyncio.gather(*real_name_tasks)
    for filename, ext_path in zip(original_filenames, extension_paths):
        ext_path.path = ext_path.path.with_name(filename)


async def download_extensions_json(
    json_data: typing.Union[typing.Dict[str, str], Path],
    save_path: Path,
    *,
    real_name: typing.Optional[bool] = None,
    versionize: typing.Optional[bool] = None,
) -> None:
    if real_name is None:
        real_name = True
    if versionize is None:
        versionize = True
    extension_paths = parse_extensions_json(json_data)
    async with aiohttp.ClientSession() as session:
        if real_name:
            await patch_extension_paths(session, extension_paths, versionize=versionize)
        download_extension_tasks = []
        for ext_path in extension_paths:
            extension_full_save_path = save_path / ext_path.path.with_suffix('.vsix')
            extension_full_save_path.parent.mkdir(parents=True, exist_ok=True)
            download_extension_tasks.append(
                download_extension_by_id(
                    session, ext_path.extension_id, ext_path.version, extension_full_save_path
                )
            )
        await asyncio.gather(*download_extension_tasks)