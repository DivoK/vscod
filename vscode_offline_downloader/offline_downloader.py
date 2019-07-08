import dataclasses
import json
import typing
from pathlib import Path

import requests

MARKETPLACE_DOWNLOAD_LINK = 'https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{publisher_name}/vsextensions/{extension_name}/latest/vspackage'
MARKETPLACE_PAGE_LINK = 'https://marketplace.visualstudio.com/items?itemName={extension_id}'


@dataclasses.dataclass
class ExtensionPath:
    path: Path
    extension_id: str


def download_extension(extension_name: str, publisher_name: str, save_path: Path) -> Path:
    response = requests.get(
        MARKETPLACE_DOWNLOAD_LINK.format(
            extension_name=extension_name, publisher_name=publisher_name
        )
    )
    extension_path = (save_path / extension_name).with_suffix('.vsix')
    extension_path.write_bytes(response.content)
    return extension_path


def download_extension_by_id(extension_id: str, save_path: Path) -> Path:
    publisher_name, extension_name = extension_id.split('.')
    return download_extension(extension_name, publisher_name, save_path)


def recursive_parse_to_dict(root_dict: typing.Dict[str, typing.Union[str, typing.Dict]]) -> typing.List[ExtensionPath]:
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


def download_extensions_json(json_path: Path, save_path: Path) -> None:
    extension_paths = parse_extensions_json(json_path)
    for ext_path in extension_paths:
        extension_save_dir = save_path / ext_path.path
        extension_save_dir.mkdir(parents=True, exist_ok=True)
        print(extension_save_dir)
        download_extension_by_id(ext_path.extension_id, extension_save_dir)


if __name__ == "__main__":
    download_extensions_json(Path('vscode_offline_downloader/extensions.json'), Path('downloads'))
