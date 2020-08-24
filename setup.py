#!/usr/bin/env python

from setuptools import setup

version = "1.8"

try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except (IOError, ImportError):
    long_description = ""


setup(
    name="aiogrpc",
    version=version,
    author="Hu Bo",
    author_email="hubo1016@126.com",
    long_description=long_description,
    description="asyncio wrapper for grpc.io",
    license="Apache",
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Framework :: AsyncIO',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development',
        'Framework :: AsyncIO',
    ],
    url="https://github.com/hubo1016/aiogrpc",
    platforms=['any'],
    packages=[
        'aiogrpc',
    ],
    python_requires='>=3.6',
    install_requires=[
        'grpcio>=1.12.0'
    ]
)
