import typing

import setuptools


def _get_long_description_data() -> typing.Tuple[str, str]:
    """
    Get data regarding the long description of the package.

    :return: tuple of the README.md text and the long_description type.
    :rtype: typing.Tuple[str, str]
    """
    with open('README.md', 'r') as readme:
        return (readme.read(), 'text/markdown')


LONG_DESCRIPTION, LONG_DESCRIPTION_CONTENT_TYPE = _get_long_description_data()

setuptools.setup(
    name='vscod',
    version='0.1.0',
    description='Download VSCode binaries and extensions offline.',
    url='https://github.com/DivoK/vscod',
    author='Divo Kaplan',
    author_email='divokaplan@gmail.com',
    python_requires='>=3.7',
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=['loguru', 'aiohttp', 'aiofiles', 'cchardet', 'aiodns', 'click'],
    entry_points='''
        [console_scripts]
        vscod=vscod.scripts.vscod:cli
    ''',
    long_description=LONG_DESCRIPTION,
    long_description_content_type=LONG_DESCRIPTION_CONTENT_TYPE,
    keywords='vscode offline cli downloader tool',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Archiving :: Mirroring',
        'Topic :: Text Editors',
        'Topic :: Utilities',
    ],
)
