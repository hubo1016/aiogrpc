#!/bin/bash -xe
cd tests
python -m coverage run --branch --source=aiogrpc testclient.py "$@"
python -m coverage report
