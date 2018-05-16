# aiogrpc

[![Build Status](https://travis-ci.org/hubo1016/aiogrpc.svg?branch=master)](https://travis-ci.org/hubo1016/aiogrpc)
[![PyPI](https://img.shields.io/pypi/v/aiogrpc.svg)](https://pypi.python.org/pypi/aiogrpc)

asyncio wrapper for grpc.io. Currently, only client-side interfaces are supported.

# Interfaces
aiogrpc has exactly the same interface as grpc.io (https://grpc.io/grpc/python/grpc.html#module-grpc), except:

- All callbacks are called with `call_soon_threadsafe()` to run in the same thread with the event loop
- All futures are asyncio futures (i.e. awaitable)
- All blocking interfaces (`__call__` for unary methods, `code()`, `details()`, ...) become coroutines
- Stream input/output are async iterators
- `close()` method returns a asyncio future (use `await channel.close()`) (*since v1.4*)

# Usage

1. Compile your proto file with protoc to generate stub files

2. Use the stub files with aiogrpc.Channel, instead of grpc.Channel:
    ```python
    from aiogrpc import insecure_channel
    import asyncio
    from mystub import MyStub
    
    channel = insecure_channel('ipv4:///127.0.0.1:8080')
    mystub = MyStub(channel)
    
    async def test_call():
        return await mystub.mymethod(...)
    
    async def test_call_stream():
        async for v in mystub.my_stream_method(...):
            ...
    ```

# Balancing

Same as the original grpc.io, balancing (fail over) between multiple servers are supported:

1. Use multiple IPv4 or IPv6 addresses for balancing - use target like: `"ipv4:///1.2.3.4:9999,1.2.3.5:9999,1.2.3.6:9999"`
   or `"ipv6:///[1::2]:9999,[1::3]:9999,[1::4]:9999"`

2. Specify **ONE** DNS name which resolves to multiple addresses. GRPC will balance between the resolved addresses, and try
   to update the resolving result in interval. Example: `"dns:///myserver:9999"`
   
Notice that you cannot mix up IPv4, IPv6 and DNS addresses; only addresses with the same type
can be balanced. Also, when using DNS target, only one DNS name can be specified.

The default load balancing strategy is `"pick_first"` (fail-over). Set `"grpc.lb_policy_name"` option to `"round_robin"` for
round-robin load balancing: `channel = insecure_channel('ipv4:///1.2.3.4:9999,1.2.3.5:9999,1.2.3.6:9999', [('grpc.lb_policy_name', 'round_robin')])`

# Copyright Notice
All code are published under Apache 2.0 License

Some code and docstrings are modified from grpc.io (https://grpc.io/grpc/python/grpc.html#module-grpc)
