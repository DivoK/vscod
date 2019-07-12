import dataclasses
import json
import re
import typing
from pathlib import Path

import requests
from loguru import logger

MARKETPLACE_DOWNLOAD_LINK = 'https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{publisher_name}/vsextensions/{extension_name}/latest/vspackage'
MARKETPLACE_PAGE_LINK = 'https://marketplace.visualstudio.com/items?itemName={extension_id}'
VERSION_REGEX = re.compile(r'"Version":"(.*?)"')


@dataclasses.dataclass
class ExtensionPath:
    path: Path
    extension_id: str


def download_extension(extension_name: str, publisher_name: str, save_path: Path) -> None:
    response = requests.get(
        MARKETPLACE_DOWNLOAD_LINK.format(
            extension_name=extension_name, publisher_name=publisher_name
        )
    )
    save_path.write_bytes(response.content)


def download_extension_by_id(extension_id: str, save_path: Path) -> None:
    publisher_name, extension_name = extension_id.split('.')
    download_extension(extension_name, publisher_name, save_path)


def recursive_parse_to_dict(
    root_dict: typing.Dict[str, typing.Union[str, typing.Dict]]
) -> typing.List[ExtensionPath]:
    path_list = []
    for key, value in root_dict.items():
        if isinstance(value, str):
            if not value:
                raise ValueError(f'Value for key {key} was empty.')
            path_list.append(ExtensionPath(Path(key), value))
        elif isinstance(value, dict):
            for ext_path in recursive_parse_to_dict(value):
                ext_path.path = Path(key, ext_path.path)
                path_list.append(ext_path)
        else:
            raise TypeError(f'Value for key {key} was neither str or dict.')
    return path_list


def parse_extensions_json(json_path: Path) -> typing.List[ExtensionPath]:
    with json_path.open() as json_file:
        extensions_dict = json.load(json_file)
    return recursive_parse_to_dict(extensions_dict)


def get_extension_version(extension_id: str) -> str:
    logger.debug(f'Requesting version of extension {extension_id}...')
    resp = requests.get(MARKETPLACE_PAGE_LINK.format(extension_id=extension_id))
    match = re.search(r'"Version":"(.*?)"', str(resp.content))
    if not match:
        raise ValueError('Extension marketplace page data doesn\'t contain a version.')
    version = match.group(1)  # The captured version specifier.
    logger.debug(f'Extension {extension_id} is of version {version}.')
    return version


def download_extensions_json(
    json_path: Path, save_path: Path, *, versioned: typing.Optional[bool] = None
) -> None:
    if versioned is None:
        versioned = False
    extension_paths = parse_extensions_json(json_path)
    for ext_path in extension_paths:
        logger.info(f'Working on {ext_path.extension_id}...')
        extension_save_dir = save_path / ext_path.path
        extension_save_dir.mkdir(parents=True, exist_ok=True)
        extension_full_save_path = extension_save_dir / f'{ext_path.extension_id}._'
        if versioned:
            extension_version = get_extension_version(ext_path.extension_id)
            extension_full_save_path = extension_full_save_path.with_suffix(
                f'.{extension_version}._'
            )
        extension_full_save_path = extension_full_save_path.with_suffix('.vsix')
        download_extension_by_id(ext_path.extension_id, extension_full_save_path)
        logger.info(
            f'Finished working on {ext_path.extension_id}: final path is {extension_full_save_path}.'
        )


if __name__ == '__main__':
    download_extensions_json(
        Path('vscode_offline_downloader/extensions.json'), Path('downloads'), versioned=True
    )
