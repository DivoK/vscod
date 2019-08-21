import asyncio
import dataclasses
import json
import re
import typing
from pathlib import Path

import aiohttp
from loguru import logger

from .utils import download_url, get_request, get_original_filename

# Format string linking to the download of a vscode extension .vsix file.
MARKETPLACE_DOWNLOAD_LINK = '''
    https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{publisher_name}/vsextensions/{extension_name}/{version}/vspackage
'''.strip()

# Format string linking to the marketplace page of some extension.
MARKETPLACE_PAGE_LINK = '''
    https://marketplace.visualstudio.com/items?itemName={extension_id}
'''.strip()

# Regex used to extract the exact version of an extension from it's marketplace page.
VERSION_REGEX = re.compile(r'"Version":"(.*?)"')


@dataclasses.dataclass
class ExtensionPath:
    """
    Dataclass for storing info regarding a certain VSCode extension.
    """

    path: Path  # Extension final save path.
    extension_id: str  # Extension ID.
    version: str = 'latest'  # Extension version.


def _build_extension_download_url(
    extension_name: str, publisher_name: str, version: str
) -> str:
    """
    Build the download url for the given parameters.
    Just a shortcut for the string formatting.

    :param extension_name: Desired extension name.
    :type extension_name: str
    :param publisher_name: Desired extension publisher's name.
    :type publisher_name: str
    :param version: Desired extension version.
    :type version: str
    :return: The formatted download url.
    :rtype: str
    """
    return MARKETPLACE_DOWNLOAD_LINK.format(
        extension_name=extension_name, publisher_name=publisher_name, version=version
    )


def _build_extension_download_url_from_ext_path(ext_path: ExtensionPath) -> str:
    """
    Build the download url for the given parameters.

    :param ext_path: A spec object describing the desired extension.
    :type ext_path: ExtensionPath
    :return: The formatted download url.
    :rtype: str
    """
    publisher_name, extension_name = ext_path.extension_id.split('.')
    return _build_extension_download_url(extension_name, publisher_name, ext_path.version)


async def _download_extension(
    session: aiohttp.ClientSession,
    extension_name: str,
    publisher_name: str,
    version: str,
    save_path: Path,
) -> None:
    """
    Download an extension according to the given parameters.
    When one needs to be a tiny bit more verbose than the `by_id` version.

    :param session: An aiohttp session object to use.
    :type session: aiohttp.ClientSession
    :param extension_name: Desired extension name.
    :type extension_name: str
    :param publisher_name: Desired extension publisher's name.
    :type publisher_name: str
    :param version: Desired extension version.
    :type version: str
    :param save_path: Save path to downloaded the desired extension to.
    :type save_path: Path
    :return: None.
    :rtype: None
    """
    logger.info(f'Downloading {extension_name}...')
    url = _build_extension_download_url(extension_name, publisher_name, version)
    await download_url(session, url, save_path, return_type=bytes)
    logger.info(f'Downloaded {extension_name} to {save_path}.')


async def download_extension_by_id(
    session: aiohttp.ClientSession, extension_id: str, version: str, save_path: Path
) -> None:
    """
    Download an extension according to the given parameters.

    :param session: An aiohttp session object to use.
    :type session: aiohttp.ClientSession
    :param extension_id: Desired extension ID.
    :type extension_id: str
    :param version: Desired extension version.
    :type version: str
    :param save_path: Save path to downloaded the desired extension to.
    :type save_path: Path
    :return: None.
    :rtype: None
    """
    publisher_name, extension_name = extension_id.split('.')
    await _download_extension(session, extension_name, publisher_name, version, save_path)


def _recursive_parse_to_dict(
    root_dict: typing.Dict[str, typing.Union[str, typing.Dict]],
) -> typing.List[ExtensionPath]:
    """
    Recursively parse the given config data:
    If the value of a key is a dict, treat it like a directory and delve one level deeper into the value.
    If the value of a key is a string, create a spec object from it and give it it's "path" down the hierarchy.

    :param root_dict: The current "root" of our config.
    :type root_dict: typing.Dict[str, typing.Union[str, typing.Dict]]
    :raises ValueError: A given key had an empty value.
    :raises TypeError: A given key was neither a str or a dict.
    :return: List of spec objects parsed from the initial config.
    :rtype: typing.List[ExtensionPath]
    """
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
    """
    Decide wether the data provided was a Path or not and act accordingly:
    If it's valid json format data, parse it and return a list of specs.
    If it's a Path, open it and then do the same thing.

    :param json_data: Either a path to a json config file or it's raw data (dict / list).
    :type json_data: typing.Union[typing.Dict[str, str], Path]
    :return: List of spec objects describing the given extensions.
    :rtype: typing.List[ExtensionPath]
    """
    if isinstance(json_data, Path):
        with json_data.open() as json_file:
            json_data = json.load(json_file)['extensions']
    return _recursive_parse_to_dict(json_data)


async def get_extension_version(session: aiohttp.ClientSession, extension_id: str) -> str:
    """
    Get the latest version of an extension on the marketplace.

    :param session: An aiohttp session object to use.
    :type session: aiohttp.ClientSession
    :param extension_id: Desired marketplace extension to get the version of.
    :type extension_id: str
    :raises ValueError: Can't find the extension version.
    :return: String of the extension's latest version.
    :rtype: str
    """
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
    """
    Add the `version` attributes to the extensions spec objects.

    :param session: An aiohttp session object to use.
    :type session: aiohttp.ClientSession
    :param extension_paths: List of extension spec objects to patch.
    :type extension_paths: typing.List[ExtensionPath]
    :return: None, this patches the existing objects.
    :rtype: None
    """
    get_version_tasks = [
        get_extension_version(session, ext_path.extension_id) for ext_path in extension_paths
    ]
    versions = await asyncio.gather(*get_version_tasks)
    for ext_path, version in zip(extension_paths, versions):
        ext_path.version = version


async def patch_extension_paths(
    session: aiohttp.ClientSession,
    extension_paths: typing.List[ExtensionPath],
    *,
    versionize: bool = True,
) -> None:
    """
    Fix up the extension paths by altering their name.
    Basic functionality is to get the real names of extensions.
    Can also append the current version number.

    :param session: An aiohttp session object to use.
    :type session: aiohttp.ClientSession
    :param extension_paths: List of extension spec objects to patch.
    :type extension_paths: typing.List[ExtensionPath]
    :param versionize: Wether to append version names to the paths, defaults to True
    :type versionize: bool, optional
    :return: None, this patches the existing objects.
    :rtype: None
    """
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
    """
    Parse the given json data and download the given VSCode extensions into the save path.

    :param json_data: Either a path to a json config file or it's raw data (dict / list).
    :type json_data: typing.Union[typing.Dict[str, str], Path]
    :param save_path: Save path for all the downloaded VSCode binaries.
    :type save_path: Path
    :param real_name: Wether to patch the real filenames of the extensions, defaults to None (True)
    :type real_name: typing.Optional[bool], optional
    :param versionize: Wether to patch the current version of the extensions, has no effect without `real_name`, defaults to None (True)
    :type versionize: typing.Optional[bool], optional
    :return: None.
    :rtype: None
    """
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
