'''
Created on 2017/8/14

:author: hubo
'''

import asyncio
import functools
import queue

def wrap_callback(callback, loop):
    @functools.wraps(callback)
    def _callback(*args, **kwargs):
        loop.call_soon_threadsafe(functools.partial(callback, *args, **kwargs))
    return _callback


def wrap_in_executor(func, loop, executor=None):
    @functools.wraps(func)
    async def _func(*args, **kwargs):
        return await loop.run_in_executor(executor, functools.partial(func, *args, **kwargs))
    return _func


def wrap_future(grpc_fut, loop):
    fut_ = loop.create_future()
    def _set_state(grpc_fut, fut_):
        assert grpc_fut.done()
        if fut_.cancelled():
            return
        assert not fut_.done()
        if grpc_fut.cancelled():
            fut_.cancel()
        else:
            exception = grpc_fut.exception()
            if exception is not None:
                fut_.set_exception(exception)
            else:
                result = grpc_fut.result()
                fut_.set_result(result)

    def _call_check_cancel(fut_):
        if fut_.cancelled():
            grpc_fut.cancel()

    def _call_set_state(grpc_fut):
        loop.call_soon_threadsafe(_set_state, grpc_fut, fut_)

    fut_.add_done_callback(_call_check_cancel)
    grpc_fut.add_done_callback(_call_set_state)
    return fut_


def copy_members(source, dest, member_list, wrapper=None):
    for m in member_list:
        f = getattr(source, m, None)
        if f is None:
            continue
        if wrapper is not None:
            f = wrapper(f)
        setattr(dest, m, f)


def wrap_future_call(grpc_fut, loop, executor=None):
    fut_ = wrap_future(grpc_fut, loop)
    # Copy extra members
    copy_members(grpc_fut, fut_,
                 ['is_active',
                  'time_remaining'])
    @functools.wraps(grpc_fut.add_callback)
    def _add_callback(callback):
        grpc_fut.add_callback(wrap_callback(callback, loop))
    fut_.add_callback = _add_callback
    copy_members(grpc_fut, fut_,
                 ['initial_metadata',
                  'trailing_metadata',
                  'code',
                  'details'],
                 functools.partial(wrap_in_executor, loop=loop, executor=executor))
    return fut_


class WrappedIterator(object):
    """
    Wrap an grpc_iterator to an async iterator
    """
    def __init__(self, grpc_iterator, loop, executor=None, stream_executor=None):
        self._iterator = grpc_iterator
        self._loop = loop
        self._executor = executor
        if stream_executor is None:
            self._shared_executor = True
            stream_executor = executor
        else:
            self._shared_executor = False
            self._stream_executor = stream_executor
        self._next_future = None
        copy_members(grpc_iterator, self,
                     ['is_active',
                      'time_remaining',
                      'cancel'])
        @functools.wraps(grpc_iterator.add_callback)
        def _add_callback(callback):
            grpc_iterator.add_callback(wrap_callback(callback, loop))
        self.add_callback = _add_callback
        copy_members(grpc_iterator, self,
                     ['initial_metadata',
                      'trailing_metadata',
                      'code',
                      'details'],
                     functools.partial(wrap_in_executor, loop=loop, executor=executor))        
        
    async def __aiter__(self):
        return self
    
    def _next(self):
        try:
            return next(self._iterator)
        except StopIteration:
            raise StopAsyncIteration
    
    async def __anext__(self):
        if self._next_future is None:
            self._next_future = self._loop.run_in_executor(self._stream_executor, self._next)
        try:
            return await asyncio.shield(self._next_future)
        finally:
            if self._next_future and self._next_future.done():
                self._next_future = None
    
    def __del__(self):
        if self._iterator is not None:
            self._iterator.cancel()
            self._iterator.close()
            self._iterator = None
        if self._next_future is not None:
            self._next_future.cancel()
            self._next_future = None
        if not self._shared_executor:
            self._stream_executor.shutdown()

    async def aclose(self):
        self.__del__()


class IteratorScope(object):
    def __init__(self, _iter):
        self._iter = _iter

    async def __aenter__(self):
        return self._iter
    
    async def __aexit__(self, exc_val, exc_typ, exc_tb):
        await self._iter.aclose()


class WrappedAsyncIterator(object):
    """
    Wrap an async iterator to an iterator for grpc input
    """
    def __init__(self, async_iter, loop):
        self._async_iter = async_iter
        self._loop = loop
        self._q = queue.Queue()

    def __iter__(self):
        return self

    async def _next(self):
        try:
            self._q.put((await self._async_iter.__anext__(), False))
        except StopAsyncIteration:
            self._q.put(None, True)
        except Exception as exc:
            self._q.put(exc, True)
        
    def __next__(self):
        if self._async_iter is None:
            raise StopIteration
        try:
            r, is_exc = self._q.get_nowait()
        except queue.Empty:
            self._loop.call_soon_threadsafe(functools.partial(asyncio.ensure_future, self._next(), loop=self._loop))
            r, is_exc = self._q.get()
        if is_exc:
            if r is None:
                self._async_iter = None
                raise StopIteration
            else:
                raise r
        else:
            return r
    
    def close(self):
        self._loop.call_soon_threadsafe(functools.partial(asyncio.ensure_future, self._async_iter.aclose(), loop=self._loop))
        self._async_iter = None

