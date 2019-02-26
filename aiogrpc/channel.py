'''
Created on 2017/8/11

:author: hubo
'''
import grpc as _grpc
import aiogrpc.utils as _utils
import asyncio as _asyncio
from concurrent.futures import ThreadPoolExecutor as _ThreadPoolExecutor
import functools


class _UnaryUnaryMultiCallable(object):
    """Affords invoking a unary-unary RPC from client-side."""
    def __init__(self, _inner, loop, executor=None):
        self._inner = _inner
        self._loop = loop
        self._executor = executor
    
    async def __call__(self, request, timeout=None, metadata=None, credentials=None):
        """Synchronously invokes the underlying RPC.

    Args:
      request: The request value for the RPC.
      timeout: An optional duration of time in seconds to allow for the RPC.
      metadata: Optional :term:`metadata` to be transmitted to the
        service-side of the RPC.
      credentials: An optional CallCredentials for the RPC.

    Returns:
      The response value for the RPC.

    Raises:
      RpcError: Indicating that the RPC terminated with non-OK status. The
        raised RpcError will also be a Call for the RPC affording the RPC's
        metadata, status code, and details.
    """
        fut = self.future(request, timeout, metadata, credentials)
        try:
            return await fut
        finally:
            if not fut.done():
                fut.cancel()

    async def with_call(self, request, timeout=None, metadata=None, credentials=None):
        """Synchronously invokes the underlying RPC.

    Args:
      request: The request value for the RPC.
      timeout: An optional durating of time in seconds to allow for the RPC.
      metadata: Optional :term:`metadata` to be transmitted to the
        service-side of the RPC.
      credentials: An optional CallCredentials for the RPC.

    Returns:
      The response value for the RPC and a Call value for the RPC.

    Raises:
      RpcError: Indicating that the RPC terminated with non-OK status. The
        raised RpcError will also be a Call for the RPC affording the RPC's
        metadata, status code, and details.
    """
        fut = self.future(request, timeout, metadata, credentials)
        try:
            result = await fut
            return (result, fut)
        finally:
            if not fut.done():
                fut.cancel()


    def future(self, request, timeout=None, metadata=None, credentials=None):
        """Asynchronously invokes the underlying RPC.

    Args:
      request: The request value for the RPC.
      timeout: An optional duration of time in seconds to allow for the RPC.
      metadata: Optional :term:`metadata` to be transmitted to the
        service-side of the RPC.
      credentials: An optional CallCredentials for the RPC.

    Returns:
        An object that is both a Call for the RPC and a Future. In the event of
        RPC completion, the return Call-Future's result value will be the
        response message of the RPC. Should the event terminate with non-OK
        status, the returned Call-Future's exception value will be an RpcError.
    """
        return _utils.wrap_future_call(self._inner.future(request, timeout, metadata, credentials),
                                       self._loop, self._executor)


class _UnaryStreamMultiCallable(object):
    """Affords invoking a unary-stream RPC from client-side."""
    def __init__(self, _inner, loop, executor=None, standalone_pool=False):
        self._inner = _inner
        self._loop = loop
        self._executor = executor
        self._standalone_pool = standalone_pool
    
    def __call__(self, request, timeout=None, metadata=None, credentials=None,
                    *, standalone_pool = None):
        """Invokes the underlying RPC.

    Args:
      request: The request value for the RPC.
      timeout: An optional duration of time in seconds to allow for the RPC.
               If None, the timeout is considered infinite.
      metadata: An optional :term:`metadata` to be transmitted to the
        service-side of the RPC.
      credentials: An optional CallCredentials for the RPC.

    Returns:
        An object that is both a Call for the RPC and an ASYNC iterator of response
        values. Drawing response values from the returned Call-iterator may
        raise RpcError indicating termination of the RPC with non-OK status.
    """
        if standalone_pool is None:
            standalone_pool = self._standalone_pool
        if standalone_pool:
            stream_executor = _ThreadPoolExecutor(1)
        else:
            stream_executor = None
        return _utils.WrappedIterator(self._inner(request, timeout, metadata, credentials),
                                      self._loop,
                                      self._executor,
                                      stream_executor)
    
    def with_scope(self, request, timeout=None, metadata=None, credentials=None,
                        *, standalone_pool = None):
        """
        Return an ASYNC context manager to ensure the call is closed outside the scope::
        
            async with mystub.mymethod.with_scope(...) as iter:
                async for i in iter:
                    ...
        """
        return _utils.IteratorScope(self(request, timeout, metadata, credentials, standalone_pool=standalone_pool))


class _StreamUnaryMultiCallable(object):
    """Affords invoking a stream-unary RPC from client-side."""
    def __init__(self, _inner, loop, executor=None):
        self._inner = _inner
        self._loop = loop
        self._executor = executor
        
    async def __call__(self,
                 request_iterator,
                 timeout=None,
                 metadata=None,
                 credentials=None):
        """Synchronously invokes the underlying RPC.

    Args:
      request_iterator: An ASYNC iterator that yields request values for the RPC.
      timeout: An optional duration of time in seconds to allow for the RPC.
               If None, the timeout is considered infinite.
      metadata: Optional :term:`metadata` to be transmitted to the
        service-side of the RPC.
      credentials: An optional CallCredentials for the RPC.

    Returns:
      The response value for the RPC.

    Raises:
      RpcError: Indicating that the RPC terminated with non-OK status. The
        raised RpcError will also implement grpc.Call, affording methods
        such as metadata, code, and details.
    """
        fut = self.future(request_iterator, timeout, metadata, credentials)
        try:
            return await fut
        finally:
            if not fut.done():
                fut.cancel()

    async def with_call(self,
                  request_iterator,
                  timeout=None,
                  metadata=None,
                  credentials=None):
        """Synchronously invokes the underlying RPC on the client.

    Args:
      request_iterator: An ASYNC iterator that yields request values for the RPC.
      timeout: An optional duration of time in seconds to allow for the RPC.
               If None, the timeout is considered infinite.
      metadata: Optional :term:`metadata` to be transmitted to the
        service-side of the RPC.
      credentials: An optional CallCredentials for the RPC.

    Returns:
      The response value for the RPC and a Call object for the RPC.

    Raises:
      RpcError: Indicating that the RPC terminated with non-OK status. The
        raised RpcError will also be a Call for the RPC affording the RPC's
        metadata, status code, and details.
    """
        fut = self.future(request_iterator, timeout, metadata, credentials)
        try:
            result = await fut
            return (result, fut)
        finally:
            if not fut.done():
                fut.cancel()

    def future(self,
               request_iterator,
               timeout=None,
               metadata=None,
               credentials=None):
        """Asynchronously invokes the underlying RPC on the client.

    Args:
      request_iterator: An ASYNC iterator that yields request values for the RPC.
      timeout: An optional duration of time in seconds to allow for the RPC.
               If None, the timeout is considered infinite.
      metadata: Optional :term:`metadata` to be transmitted to the
        service-side of the RPC.
      credentials: An optional CallCredentials for the RPC.

    Returns:
        An object that is both a Call for the RPC and a Future. In the event of
        RPC completion, the return Call-Future's result value will be the
        response message of the RPC. Should the event terminate with non-OK
        status, the returned Call-Future's exception value will be an RpcError.
    """
        return _utils.wrap_future_call(
                    self._inner.future(
                        _utils.WrappedAsyncIterator(request_iterator, self._loop),
                        timeout,
                        metadata,
                        credentials
                    ),
                    self._loop,
                    self._executor)


class _StreamStreamMultiCallable(object):
    """Affords invoking a stream-stream RPC on client-side."""

    def __init__(self, _inner, loop, executor=None, standalone_pool=False):
        self._inner = _inner
        self._loop = loop
        self._executor = executor
        self._standalone_pool = standalone_pool

    def __call__(self,
                 request_iterator,
                 timeout=None,
                 metadata=None,
                 credentials=None,
                 *, standalone_pool = None):
        """Invokes the underlying RPC on the client.

    Args:
      request_iterator: An iterator that yields request values for the RPC.
      timeout: An optional duration of time in seconds to allow for the RPC.
               if not specified the timeout is considered infinite.
      metadata: Optional :term:`metadata` to be transmitted to the
        service-side of the RPC.
      credentials: An optional CallCredentials for the RPC.

    Returns:
        An object that is both a Call for the RPC and an iterator of response
        values. Drawing response values from the returned Call-iterator may
        raise RpcError indicating termination of the RPC with non-OK status.
    """
        if standalone_pool is None:
            standalone_pool = self._standalone_pool
        if standalone_pool:
            stream_executor = _ThreadPoolExecutor(1)
        else:
            stream_executor = None
        input_iterator = _utils.WrappedAsyncIterator(request_iterator,
                                                    self._loop)
        grpc_iterator = self._inner(
                        input_iterator,
                        timeout,
                        metadata,
                        credentials
                    )
        r = _utils.WrappedIterator(
                    grpc_iterator,
                    self._loop,
                    self._executor,
                    stream_executor)
        # Make sure the input iterator exits, or the thread may block indefinitely
        def _end_callback():
            input_iterator.cancel(False)
        grpc_iterator.add_callback(_end_callback)
        return r


    def with_scope(self, request_iterator, timeout=None, metadata=None, credentials=None,
                   *, standalone_pool = None):
        """
        Return an ASYNC context manager to ensure the call is closed outside the scope::
        
            async with mystub.mymethod.with_scope(...) as iter:
                async for i in iter:
                    ...
        """
        return _utils.IteratorScope(self(request_iterator, timeout, metadata, credentials,
                                         standalone_pool=standalone_pool))


class Channel(_grpc.Channel):
    """An asyncio proxy of grpc.Channel."""

    def __init__(self, _channel, loop=None, executor=None, standalone_pool_for_streaming=False):
        """Constructor.

        Args:
          _channel: wrapped grpc.Channel
          loop: asyncio event loop
          executor: a thread pool, or None to use the default pool of the loop
          standalone_pool_for_streaming: create a new thread pool (with 1 thread) for each streaming
                                         method
        """
        self._channel = _channel
        if loop is None:
            loop = _asyncio.get_event_loop()
        self._loop = loop
        self._executor = executor
        self._standalone_pool = standalone_pool_for_streaming
        self._subscribe_map = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    def subscribe(self, callback, try_to_connect=None):
        if callback in self._subscribe_map:
            wrapped_callback = self._subscribe_map[callback]
        else:
            wrapped_callback = _utils.wrap_callback(callback, self._loop)
        self._channel.subscribe(wrapped_callback, try_to_connect)
        self._subscribe_map[callback] = wrapped_callback

    def unsubscribe(self, callback):
        if callback in self._subscribe_map:
            self._channel.unsubscribe(self._subscribe_map[callback])
            del self._subscribe_map[callback]

    def unary_unary(self,
                    method,
                    request_serializer=None,
                    response_deserializer=None):
        return _UnaryUnaryMultiCallable(
                    self._channel.unary_unary(method, request_serializer, response_deserializer),
                    self._loop,
                    self._executor)

    def unary_stream(self,
                     method,
                     request_serializer=None,
                     response_deserializer=None):
        return _UnaryStreamMultiCallable(
            self._channel.unary_stream(method, request_serializer, response_deserializer),
            self._loop,
            self._executor,
            self._standalone_pool)

    def stream_unary(self,
                     method,
                     request_serializer=None,
                     response_deserializer=None):
        return _StreamUnaryMultiCallable(
            self._channel.stream_unary(method, request_serializer, response_deserializer),
            self._loop,
            self._executor)

    def stream_stream(self,
                      method,
                      request_serializer=None,
                      response_deserializer=None):
        return _StreamStreamMultiCallable(
            self._channel.stream_stream(method, request_serializer, response_deserializer),
            self._loop,
            self._executor,
            self._standalone_pool)

    def close(self):
        """
        This method returns a future, so you should use `await channel.close()`, but call
        `channel.close()` also close it (but did not wait for the closing)
        """
        return self._loop.run_in_executor(self._executor, self._channel.close)


def channel_ready_future(channel):
    """Creates a Future that tracks when a Channel is ready.

  Cancelling the Future does not affect the channel's state machine.
  It merely decouples the Future from channel state machine.

  Args:
    channel: A Channel object.

  Returns:
    A Future object that matures when the channel connectivity is
    ChannelConnectivity.READY.
  """
    fut = channel._loop.create_future()
    def _set_result(state):
        if not fut.done() and state is _grpc.ChannelConnectivity.READY:
            fut.set_result(None)
    fut.add_done_callback(lambda f: channel.unsubscribe(_set_result))
    channel.subscribe(_set_result, try_to_connect=True)
    return fut


def insecure_channel(target, options=None, *, loop=None, executor=None,
                    standalone_pool_for_streaming=False):
    """Creates an insecure Channel to a server.

  Args:
    target: The server address
    options: An optional list of key-value pairs (channel args in gRPC runtime)
    to configure the channel.

  Returns:
    A Channel object.
  """
    return Channel(_grpc.insecure_channel(target, options), loop, executor, standalone_pool_for_streaming)


def secure_channel(target, credentials, options=None, *, loop=None, executor=None,
                   standalone_pool_for_streaming=False):
    """Creates a secure Channel to a server.

  Args:
    target: The server address.
    credentials: A ChannelCredentials instance.
    options: An optional list of key-value pairs (channel args in gRPC runtime)
    to configure the channel.

  Returns:
    A Channel object.
  """
    return Channel(_grpc.secure_channel(target, credentials, options),
                   loop, executor, standalone_pool_for_streaming)
