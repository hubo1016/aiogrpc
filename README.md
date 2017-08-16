# aiogrpc
[![Build Status](https://travis-ci.org/hubo1016/aiogrpc.svg?branch=master)](https://travis-ci.org/hubo1016/aiogrpc)
[![PyPI](https://img.shields.io/pypi/v/aiogrpc.svg)](https://pypi.python.org/pypi/aiogrpc)
asyncio wrapper for grpc.io. Currently, only client-side interfaces are supported.

# Interfaces
aiogrpc has exactly the same interface as grpc.io (https://grpc.io/grpc/python/grpc.html#module-grpc), except:

- All callbacks are called with call_soon_threadsafe() to run in the same thread with the event loop
- All futures are asyncio futures (i.e. awaitable)
- All blocking interfaces (__call__ for unary methods, code(), details(), ...) become coroutines
- Stream input/output are async iterators

# Usage

1. Compile your proto file with protoc to generate stub files

2. Use the stub files with aiogrpc.Channel, instead of grpc.Channel:
    ```python
    from aiogrpc import insecure_channel
    import asyncio
    from mystub import MyStub
    
    channel = insecure_channel('127.0.0.1:8080'))
    mystub = MyStub(channel)
    
    async test_call():
        return await mystub.mymethod(...)
    
    async test_call_stream():
        async for v in mystub.my_stream_method(...):
            ...
    ```

# Copyright Notice
All code are published under Apache 2.0 License
Some code and docstrings are modified from grpc.io (https://grpc.io/grpc/python/grpc.html#module-grpc)
