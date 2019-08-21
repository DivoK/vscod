# VSCOD

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/vscod.svg)](https://pypi.python.org/pypi/vscod/)
[![PyPI version fury.io](https://badge.fury.io/py/vscod.svg)](https://pypi.python.org/pypi/vscod/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

**_VSCOD_** is short for **V**isual **S**tudio **C**ode **O**ffline **D**ownloader. This tool will allow you to download batches of extensions as well as VSCode binaries so you can later on use them to install your favorite editor and it's extensions.
This tool could help greatly if you're a frustrated admin that needs to update a local artifact repository, if you don't have access to the official repositories from your station and need to pass things by hand or just if you're an automation freak and for some reason want to mess up with the Visual Studio Marketplace.

I tried to find a tool that does that and when I failed I tried to at least find a convenient API to use but to my surprise the Marketplace doesn't have one at the time of writing these lines (and if you find one, feel free to send a PR!), and so I ended up writing **VSCOD**!

## Installation

Use the Python package manager [pip](https://pip.pypa.io/en/stable/) to install `vscod`.

```bash
pip install vscod
```

## Usage

### Shell

```bash
# Display the help
vscod --help
# Download the insider binaries for Linux (64bit deb), Windows (32bit) and Mac to the 'downloads' dir.
vscod download editor --output 'downloads' --build insider linux-deb-x64 win32-archive darwin
# Download the official Python extension and the Vim keymap to the 'extensions' dir.
vscod download extensions --output 'extensions' ms-python.python vscodevim.vim
# Download the requested config data (see below) to the current directory (the default path if none is specified btw).
vscod download config --output '.' /path/to/config.json
# List all the supported platform and build strings.
vscod list-opts
```

### Python

```python
from vscod import extensions_downloader, vscode_downloader
from vscod.vscode_downloader import BUILDS, PLATFORMS, LATEST_VERSION
import asyncio
import aiohttp

async def vscod_demo():
    async with aiohttp.ClientSession() as session:  # It's all asynchronous!
        # Download the latest version of the official Python extension to the path.
        await extensions_downloader.download_extension_by_id(session, 'ms-python.python', 'latest', '/path/to/save')
        # Find what the latest version of the Vim keymap is.
        vim_version = await extensions_downloader.get_extension_version(session, 'vscodevim.vim')
        # Download the latest stable Linux deb version to the path.
        await vscode_downloader.download_vscode(session, PLATFORMS.LINUX64_DEB, '/path/to/save', build=BUILDS.STABLE, version=LATEST_VERSION)

asyncio.run(vscod_demo())
```

### Config

You can also supply a JSON configuration that looks something like this:

```json
{
    "vscode": [
        {
            "platform": "linux-deb-x64"
        },
        {
            "platform": "win32-x64-user",
            "version": "latest",
            "build": "stable"
        }
    ],
    "extensions": {
        "gitlens": "eamodio.gitlens",
        "languages": {
            "go": "ms-vscode.go",
            "python": {
                "python": "ms-python.python",
                "auto_docstring": "njpwerner.autodocstring"
            }
        }
    }
}
```

The top level `"vscode"` and `"extensions"` signals that these are the editor and extensions download settings respectively (duh).
The parsing process then goes as follows:

* For extensions:
    1. Go through the loaded dictionary's items recursively:
        * If the value is a string, we got to the extension ID.
        * If the value is a dict, delve deeper.
    1. Build a directory hierarchy using the keys as directories.
    1. Download each extension ID to it's designated location.
* For VSCode binaries:
    1. Go through the loaded list of specification dicts. If the value of the top level `"vscode"` key is a dict, treat it like a list with a single dict.
    1. For each of them download the binary according to the specification given in the dict into a designated directory.

So it will generate the following hierarchy:

```text
|-- root_path
    |-- gitlens
    |   |-- eamodio.gitlens-9.9.3.vsix
    |-- languages
    |   |-- go
    |   |   |-- ms-vscode.go-0.11.4.vsix
    |   |-- python
    |       |-- auto_docstring
    |       |   |-- njpwerner.autodocstring-0.3.0.vsix
    |       |-- python
    |           |-- ms-python.python-2019.8.30787.vsix
    |-- linux-deb-x64
    |   |-- code_1.37.1-1565886362_amd64.deb
    |-- win32-x64-user
        |-- VSCodeUserSetup-x64-1.37.1.exe
```

## License

[MIT](LICENSE.txt)
