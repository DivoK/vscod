import setuptools

setuptools.setup(
    name='vscodownloader',
    version='0.1',
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=[
        'loguru',
        'aiohttp',
        'aiofiles',
        'cchardet',
        'aiodns',
        'click',
    ],
    entry_points='''
        [console_scripts]
        vscodownloader=vscode_offline_downloader.scripts.vscodownloader:cli
    ''',
)
