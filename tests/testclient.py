'''
Created on 2017/8/15

:author: hubo
'''
import unittest
import asyncio
import functools
import aiogrpc
from service_pb2 import StandardRequest, StreamRequest
from service_pb2_grpc import TestServiceStub
from server import create_server

def asynctest(f):
    @functools.wraps(f)
    def _test(self):
        return self.loop.run_until_complete(f(self))
    return _test

class Test(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.channel = aiogrpc.insecure_channel('ipv4:///127.0.0.1:9901', loop=self.loop)
        self.stub = TestServiceStub(self.channel)

    def tearDown(self):
        self.loop.run_until_complete(self.channel.close())
        del self.channel
        del self.stub

    @asynctest
    async def testAsyncCtxManager(self):
        async with aiogrpc.insecure_channel('ipv4:///127.0.0.1:9901', loop=self.loop) as _channel:
            await aiogrpc.channel_ready_future(_channel)

    @asynctest
    async def testConnect(self):
        await aiogrpc.channel_ready_future(self.channel)

    @asynctest
    async def testUnaryUnary(self):
        result = await self.stub.NormalMethod(StandardRequest(name='test1'))
        self.assertEqual(result.message, 'test1')
        result, call = await self.stub.NormalMethod.with_call(StandardRequest(name='test2'))
        self.assertEqual(result.message, 'test2')
        self.assertEqual(await call.code(), aiogrpc.StatusCode.OK)
        self.assertEqual(await call.details(), 'OK detail')
        self.assertEqual(call.is_active(), False)
        fut = self.stub.NormalMethod.future(StandardRequest(name='test3'))
        self.assertEqual(fut.is_active(), True)
        self.assertEqual(fut.done(), False)
        self.assertEqual(await fut.code(), aiogrpc.StatusCode.OK)
        self.assertEqual((await fut).message, 'test3')
        self.assertEqual(fut.is_active(), False)
        self.assertEqual(fut.done(), True)

    @asynctest
    async def testCancel(self):
        fut = self.stub.DelayedMethod.future(StandardRequest(name='test1'))
        self.assertEqual(fut.is_active(), True)
        fut.cancel()
        self.assertEqual(await fut.code(), aiogrpc.StatusCode.CANCELLED)
        self.assertEqual(fut.is_active(), False)

    @asynctest
    async def testUnaryStream(self):
        r = self.stub.StreamMethod(StreamRequest(name='test1', count=4))
        count = 0
        async for v in r:
            self.assertEqual(v.message, 'test1')
            count += 1
        self.assertEqual(count, 4)
        self.assertEqual(r.is_active(), False)
        self.assertEqual(await r.code(), aiogrpc.StatusCode.OK)
        async with self.stub.StreamMethod.with_scope(StreamRequest(name='test1', count=4)) as r:
            count = 0
            async for v in r:
                self.assertEqual(v.message, 'test1')
                count += 1
                if count >= 2:
                    break
        self.assertEqual(await r.code(), aiogrpc.StatusCode.CANCELLED)
        self.assertEqual(r.is_active(), False)
        r = self.stub.StreamMethod(StreamRequest(name='test1', count=4), standalone_pool=True)
        count = 0
        async for v in r:
            self.assertEqual(v.message, 'test1')
            count += 1
        self.assertEqual(count, 4)
        self.assertEqual(r.is_active(), False)
        self.assertEqual(await r.code(), aiogrpc.StatusCode.OK)
        async with self.stub.StreamMethod.with_scope(StreamRequest(name='test1', count=4), standalone_pool=True) as r:
            count = 0
            async for v in r:
                self.assertEqual(v.message, 'test1')
                count += 1
                if count >= 2:
                    break
        self.assertEqual(await r.code(), aiogrpc.StatusCode.CANCELLED)
        self.assertEqual(r.is_active(), False)

    @asynctest
    async def testStreamUnary(self):
        async def test_input():
            yield StandardRequest(name='test1')
            yield StandardRequest(name='test2')
            yield StandardRequest(name='test3')
        result = await self.stub.StreamInputMethod(test_input())
        self.assertEqual(result.count, 3)
        result, call = await self.stub.StreamInputMethod.with_call(test_input())
        self.assertEqual(result.count, 3)
        self.assertEqual(await call.code(), aiogrpc.StatusCode.OK)
        self.assertEqual(call.is_active(), False)
        fut = self.stub.StreamInputMethod.future(test_input())
        self.assertEqual(fut.is_active(), True)
        self.assertEqual(fut.done(), False)
        self.assertEqual(await fut.code(), aiogrpc.StatusCode.OK)
        self.assertEqual((await fut).count, 3)
        self.assertEqual(fut.is_active(), False)
        self.assertEqual(fut.done(), True)
        async def test_input2():
            yield StandardRequest(name='test1')
            yield StandardRequest(name='test2')
            raise ValueError('Testing raising exception from client side (A designed test case)')
        with self.assertRaises(aiogrpc.RpcError):
            result = await self.stub.StreamInputMethod(test_input2())

    @asynctest
    async def testException(self):
        with self.assertRaises(aiogrpc.RpcError):
            await self.stub.ExceptionMethod(StandardRequest(name='test1'))
        fut = self.stub.ExceptionMethod.future(StandardRequest(name='test1'))
        self.assertEqual(await fut.code(), aiogrpc.StatusCode.PERMISSION_DENIED)
        self.assertEqual(fut.done(), True)
        self.assertIsInstance(fut.exception(), aiogrpc.RpcError)
        with self.assertRaises(aiogrpc.RpcError):
            await fut

    @asynctest
    async def testStreamStream(self):
        async def test_input(q):
            while True:
                r = await q.get()
                if r is None:
                    break
                else:
                    yield r
        q = asyncio.Queue()
        result = self.stub.StreamStreamMethod(test_input(q))
        await q.put(StandardRequest(name='test1'))
        self.assertEqual((await result.__anext__()).message, 'test1')
        await q.put(StandardRequest(name='test2'))
        self.assertEqual((await result.__anext__()).message, 'test2')
        await q.put(StandardRequest(name='test3'))
        self.assertEqual((await result.__anext__()).message, 'test3')
        await q.put(None)
        with self.assertRaises(StopAsyncIteration):
            await result.__anext__()
        self.assertEqual(result.is_active(), False)
        self.assertEqual(await result.code(), aiogrpc.StatusCode.OK)
        q = asyncio.Queue()
        async with self.stub.StreamStreamMethod.with_scope(test_input(q)) as result:
            await q.put(StandardRequest(name='test1'))
            self.assertEqual((await result.__anext__()).message, 'test1')
            await q.put(StandardRequest(name='test2'))
            self.assertEqual((await result.__anext__()).message, 'test2')
            await q.put(StandardRequest(name='test3'))
            self.assertEqual((await result.__anext__()).message, 'test3')
        with self.assertRaises(StopAsyncIteration):
            await result.__anext__()
        self.assertEqual(await result.code(), aiogrpc.StatusCode.CANCELLED)
        self.assertEqual(result.is_active(), False)
        q = asyncio.Queue()
        result = self.stub.StreamStreamMethod(test_input(q))
        await q.put(None)
        with self.assertRaises(StopAsyncIteration):
            await result.__anext__()

    @asynctest
    async def testInfiniteStreamCancel(self):
        async def test_input():
            yield StandardRequest(name=f'test1')
        q = asyncio.Queue()
        result = self.stub.InfiniteStreamStreamMethod(test_input())

        results = []
        async def read_task(result):
            async for x in result:
                results.append(x.message)

        loop = asyncio.get_event_loop()
        task = loop.create_task(read_task(result))
        await asyncio.sleep(0.2)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        self.assertEqual(results, ["test1"])

    @unittest.skip("broken")
    @asynctest
    async def testBalancing(self):
        s1 = create_server(['127.0.0.1:9902'])
        s2 = create_server(['127.0.0.1:9903'])
        self.channel = aiogrpc.insecure_channel('ipv4:///127.0.0.1:9902,127.0.0.1:9903', loop=self.loop)
        self.stub = TestServiceStub(self.channel)
        s1.start()
        try:
            result = await self.stub.NormalMethod(StandardRequest(name='test1'))
            self.assertEqual(result.message, 'test1')
        finally:
            s1.stop(None)
        s2.start()
        try:
            result = await self.stub.NormalMethod(StandardRequest(name='test1'))
            self.assertEqual(result.message, 'test1')
        finally:
            s1.stop(None)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    s = create_server(['127.0.0.1:9901'])
    s.start()
    try:
        unittest.main()
    finally:
        waiter = s.stop(None)
        waiter.wait()
