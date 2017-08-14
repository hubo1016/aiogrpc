#!/usr/bin/env python

from setuptools import setup

version = "0.1"

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
        'Development Status :: 4 - Beta',
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
        'janus>=0.3.0',
        'grpcio>=1.4.0'
    ]
)