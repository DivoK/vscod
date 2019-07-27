import asyncio
import dataclasses
import typing
import json
from pathlib import Path

import aiohttp
from loguru import logger

from .utils import download_url

DOWNLOAD_CODE_LINK = 'https://update.code.visualstudio.com/{version}/{platform}/{build}'
LATEST_VERSION = 'latest'


@dataclasses.dataclass
class VSCodeSpec:
    platform: str
    build: str
    version: str


class _Platforms:
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
    STABLE = 'stable'
    INSIDERS = 'insiders'


PLATFORMS = _Platforms()
BUILDS = _Builds()


def _build_vscode_download_url(platform: str, build: str, version: str) -> str:
    return DOWNLOAD_CODE_LINK.format(platform=platform, build=build, version=version)


async def download_vscode(
    session: aiohttp.ClientSession,
    platform: str,
    save_path: Path,
    *,
    build: str = BUILDS.STABLE,
    version: str = LATEST_VERSION,
) -> None:
    logger.info(f'Downloading {platform} version...')
    url = _build_vscode_download_url(platform, build, version)
    await download_url(session, url, save_path, return_type=bytes)
    logger.info(f'Downloaded {version}/{platform}/{build} version to {save_path}.')


async def download_vscode_from_spec(
    session: aiohttp.ClientSession, spec: VSCodeSpec, save_path: Path
) -> None:
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
    if isinstance(json_data, Path):
        with json_data.open() as json_file:
            json_data = json.load(json_file)['vscode']
    if not isinstance(json_data, list):
        json_data = [json_data]
    return _parse_vscode_specification_dict(json_data)


async def download_vscode_json(
    json_data: typing.Union[typing.List[typing.Dict[str, str]], Path], save_path: Path
) -> None:
    vscode_specs = parse_vscode_json(json_data)
    async with aiohttp.ClientSession() as session:
        download_vscode_tasks = []
        for spec in vscode_specs:
            # TODO: get the original filename from the response's redirected url.
            vscode_full_save_path = save_path / f'{spec.platform}{spec.build}{spec.version}'
            vscode_full_save_path.parent.mkdir(parents=True, exist_ok=True)
            download_vscode_tasks.append(
                download_vscode_from_spec(session, spec, vscode_full_save_path)
            )
        await asyncio.gather(*download_vscode_tasks)
