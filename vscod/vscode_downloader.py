import asyncio
import dataclasses
import typing
import json
from pathlib import Path

import aiohttp
from loguru import logger

from .utils import download_url, get_original_filename

# Format string linking to the download of a VSCode binary.
DOWNLOAD_CODE_LINK = 'https://update.code.visualstudio.com/{version}/{platform}/{build}'

# The token for when you want to get the absolute latest version.
LATEST_VERSION = 'latest'


@dataclasses.dataclass
class VSCodeSpec:
    """
    Dataclass for storing info regarding a certain VSCode binary.
    """

    platform: str  # Desired installation platform specific string.
    build: str  # Desired installation build specific string.
    version: str  # Desired installation version string.


class _Platforms:
    """
    A class to store all the special tokens pointing to various platform options.
    """

    WIN64_ADMIN = 'win32-x64'
    WIN64_USER = 'win32-x64-user'
    WIN64_ZIP = 'win32-x64-archive'
    WIN32_ADMIN = 'win32'
    WIN32_USER = 'win32-user'
    WIN32_ZIP = 'win32-archive'
    LINUX64_DEB = 'linux-deb-x64'
    LINUX64_RPM = 'linux-rpm-x64'
    LINUX64_TAR_GZ = 'linux-x64'
    OSX = 'darwin'


class _Builds:
    """
    A class to store all the special tokens pointing to various build options.
    """

    STABLE = 'stable'
    INSIDER = 'insider'


PLATFORMS = _Platforms()  # Platforms singleton.
BUILDS = _Builds()  # Builds singleton


def _build_vscode_download_url(platform: str, build: str, version: str) -> str:
    """
    Build the download url for the given parameters.
    Just a shortcut for the string formatting.

    :param platform: Desired platform.
    :type platform: str
    :param build: Desired build.
    :type build: str
    :param version: Desired version.
    :type version: str
    :return: The formatted download url.
    :rtype: str
    """
    return DOWNLOAD_CODE_LINK.format(platform=platform, build=build, version=version)


def _build_vscode_download_url_from_spec(spec: VSCodeSpec) -> str:
    """
    Build the download url for the given spec object.

    :param spec: A spec object containing all the relevant information to build a download url.
    :type spec: VSCodeSpec
    :return: The formatted download url.
    :rtype: str
    """
    return _build_vscode_download_url(
        platform=spec.platform, build=spec.build, version=spec.version
    )


async def download_vscode(
    session: aiohttp.ClientSession,
    platform: str,
    save_path: Path,
    *,
    build: str = BUILDS.STABLE,
    version: str = LATEST_VERSION,
) -> None:
    """
    Download a VSCode binary according to the passed parameters into the given save path.

    :param session: An aiohttp session object to use.
    :type session: aiohttp.ClientSession
    :param platform: Desired VSCode platform.
    :type platform: str
    :param save_path: Save path for the downloaded binary.
    :type save_path: Path
    :param build: Desired VSCode build, defaults to BUILDS.STABLE
    :type build: str, optional
    :param version: Desired VSCode version, defaults to LATEST_VERSION
    :type version: str, optional
    :return: None.
    :rtype: None
    """
    logger.info(f'Downloading {platform} version...')
    url = _build_vscode_download_url(platform, build, version)
    await download_url(session, url, save_path, return_type=bytes)
    logger.info(f'Downloaded {version}/{platform}/{build} version to {save_path}.')


async def download_vscode_from_spec(
    session: aiohttp.ClientSession, spec: VSCodeSpec, save_path: Path
) -> None:
    """
    Download a VSCode binary according to the passed parameters into the given save path.

    :param session: An aiohttp session object to use.
    :type session: aiohttp.ClientSession
    :param spec: A spec object containing all the relevant information to download a VSCode binary.
    :type spec: VSCodeSpec
    :param save_path: Save path for the downloaded binary.
    :type save_path: Path
    :return: None.
    :rtype: None
    """
    return await download_vscode(
        session=session,
        save_path=save_path,
        platform=spec.platform,
        build=spec.build,
        version=spec.version,
    )


def _parse_vscode_specification_dict(
    specification: typing.Dict[str, str]
) -> typing.List[VSCodeSpec]:
    """
    Parse the given specification list into a list of spec objects.

    :param specification: A list of dicts containing various attributes that describe a VSCode binary.
    :type specification: typing.Dict[str, str]
    :return: A list of spec objects.
    :rtype: typing.List[VSCodeSpec]
    """
    logger.debug(specification)
    return [
        VSCodeSpec(
            platform=spec['platform'],
            build=spec.get('build', BUILDS.STABLE),
            version=spec.get('version', LATEST_VERSION),
        )
        for spec in specification
    ]


def parse_vscode_json(
    json_data: typing.Union[typing.List[typing.Dict[str, str]], Path]
) -> typing.List[VSCodeSpec]:
    """
    Decide wether the data provided was a Path or not and act accordingly:
    If it's valid json format data, parse it and return a list of specs.
    If it's a Path, open it and then do the same thing.

    :param json_data: Either a path to a json config file or it's raw data (dict / list).
    :type json_data: typing.Union[typing.List[typing.Dict[str, str]], Path]
    :return: List of spec objects describing the given VSCodes.
    :rtype: typing.List[VSCodeSpec]
    """
    if isinstance(json_data, Path):
        with json_data.open() as json_file:
            json_data = json.load(json_file)['vscode']
    if not isinstance(json_data, list):
        json_data = [json_data]
    return _parse_vscode_specification_dict(json_data)


async def download_vscode_json(
    json_data: typing.Union[typing.List[typing.Dict[str, str]], Path], save_path: Path
) -> None:
    """
    Parse the given json data and download the given VSCode instances into the save path.

    :param json_data: Either a path to a json config file or it's raw data (dict / list).
    :type json_data: typing.Union[typing.List[typing.Dict[str, str]], Path]
    :param save_path: Save path for all the downloaded VSCode binaries.
    :type save_path: Path
    :return: None.
    :rtype: None
    """
    vscode_specs = parse_vscode_json(json_data)
    async with aiohttp.ClientSession() as session:
        get_vscode_filename_tasks = [
            get_original_filename(session, _build_vscode_download_url_from_spec(spec))
            for spec in vscode_specs
        ]
        vscode_filenames = await asyncio.gather(*get_vscode_filename_tasks)
        download_vscode_tasks = []
        for spec, filename in zip(vscode_specs, vscode_filenames):
            vscode_full_save_path = save_path / spec.platform / filename
            vscode_full_save_path.parent.mkdir(parents=True, exist_ok=True)
            download_vscode_tasks.append(
                download_vscode_from_spec(session, spec, vscode_full_save_path)
            )
        await asyncio.gather(*download_vscode_tasks)
