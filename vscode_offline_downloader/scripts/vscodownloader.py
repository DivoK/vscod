import asyncio
import click
import functools
import typing
from pathlib import Path

from ..vscode_downloader import BUILDS, PLATFORMS, LATEST_VERSION, download_vscode_json
from ..extensions_downloader import download_extensions_json
from ..utils import configure_verbosity


def coroutine(
    async_func: typing.Callable, *args: typing.Any, **kwargs: typing.Any
) -> typing.Callable:
    @functools.wraps(async_func)
    def func(*args, **kwargs):
        return asyncio.run(async_func(*args, **kwargs))

    return func


@click.group()
@click.option('--verbose', is_flag=True, help='Make the downloader more verbose.')
@click.option(
    '--quiet', is_flag=True, help='Make the downloader shut up. Overrides `verbose`.'
)
def cli(verbose: bool, quiet: bool):
    if verbose:
        configure_verbosity('DEBUG')
    if quiet:
        configure_verbosity('SHUT_UP', quiet=True)


@cli.group()
def download():
    pass


@download.command()
@click.argument('config_path', type=click.Path(exists=True))
@click.option(
    '-o',
    '--output',
    'output_path',
    type=click.Path(),
    default='.',
    help='Where to output the downloaded files.',
)
@coroutine
async def config(json_path: str, output_path: str):
    download_vscode_json(Path(json_path), Path(output_path))
    download_extensions_json(Path(json_path), Path(output_path))


@download.command()
@click.argument('extension_ids', type=click.STRING, required=True, nargs=-1)
@click.option(
    '-o',
    '--output',
    'output_path',
    type=click.Path(),
    default='.',
    help='Where to output the downloaded files.',
)
@coroutine
async def extensions(extension_ids: typing.List[str], output_path: str):
    output_path = Path(output_path)
    config_dict = {ext_id: ext_id for ext_id in extension_ids}
    await download_extensions_json(config_dict, output_path)


def _get_constant_values(obj) -> typing.List[typing.Tuple[str, str]]:
    ret_list = []
    for k, v in obj.__class__.__dict__.items():
        if not k.startswith('__'):
            ret_list.append(v)
    return ret_list


@download.command()
@click.argument(
    'platforms', type=click.Choice(_get_constant_values(PLATFORMS)), required=True, nargs=-1
)
@click.option(
    '-b',
    '--build',
    type=click.Choice(_get_constant_values(BUILDS)),
    required=False,
    default=BUILDS.STABLE,
    show_default=True,
    help='Which build to download.',
)
@click.option(
    '-v',
    '--version',
    type=click.STRING,
    required=False,
    default=LATEST_VERSION,
    show_default=True,
    help='Which version to download.',
)
@click.option(
    '-o',
    '--output',
    'output_path',
    type=click.Path(),
    default='.',
    help='Where to output the downloaded files.',
)
@coroutine
async def editor(
    platforms: typing.List[str], build: str, version: str, output_path: click.Path
):
    output_path = Path(output_path)
    config_list = [
        {'platform': platform, 'build': build, 'version': version} for platform in platforms
    ]
    await download_vscode_json(config_list, output_path)


def _print_constants(obj) -> None:
    for k, v in obj.__class__.__dict__.items():
        if not k.startswith('__'):
            click.echo(f'{k}: "{v}"')


@cli.command()
@click.option('-p', '--platforms', is_flag=True)
@click.option('-b', '--builds', is_flag=True)
def list_opts(platforms: bool, builds: bool):
    if not platforms and not builds:
        platforms = True
        builds = True
    if platforms:
        click.echo('PLATFORM OPTIONS')
        _print_constants(PLATFORMS)
    if builds:
        click.echo('{}BUILDS OPTIONS'.format('\n' if platforms else ''))
        _print_constants(BUILDS)
