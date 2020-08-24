'''
Created on 2017/8/14

:author: hubo
'''
from __future__ import print_function
from service_pb2_grpc import TestServiceServicer, add_TestServiceServicer_to_server
from service_pb2 import StandardReply, StandardReply, StreamRequest, StreamReply
from grpc import server, StatusCode
from concurrent import futures
import time

class TestServer(TestServiceServicer):
    def NormalMethod(self, request, context):
        context.set_code(StatusCode.OK)
        context.set_details('OK detail')
        return StandardReply(message=request.name)

    def StreamInputMethod(self, request_iterator, context):
        count = 0
        for r in request_iterator:
            count += 1
        return StreamReply(message='stream', count=count)

    def StreamMethod(self, request, context):
        for _ in range(0, request.count):
            yield StandardReply(message=request.name)

    def StreamStreamMethod(self, request_iterator, context):
        for r in request_iterator:
            yield StandardReply(message=r.name)

    def InfiniteStreamStreamMethod(self, request_iterator, context):
        for r in request_iterator:
            yield StandardReply(message=r.name)
        while True:
            time.sleep(1)
            yield StandardReply(message="xxx")

    def DelayedMethod(self, request, context):
        time.sleep(1)
        return StandardReply(message=request.name)

    def ExceptionMethod(self, request, context):
        context.set_code(StatusCode.PERMISSION_DENIED)
        context.set_details('Permission denied')
        raise ValueError("Testing raising exception from the server (A designed test case)")

    def DelayedStream(self, request, context):
        for i in range(0, request.count):
            time.sleep(1)
            yield StandardReply(message=request.name)


class QuitException(BaseException):
    pass


def signal_handler(sig_num, frame):
    raise QuitException


def create_server(listen_addrs=['127.0.0.1:9901']):
    s = server(futures.ThreadPoolExecutor(max_workers=128))
    add_TestServiceServicer_to_server(TestServer(), s)
    for listen_addr in listen_addrs:
        s.add_insecure_port(listen_addr)
    return s


def main(listen_addrs=['127.0.0.1:9901']):
    s = create_server(listen_addrs)
    print("Server created on", listen_addrs)
    s.start()
    print("Server started")
    import signal
    old1 = signal.signal(signal.SIGINT, signal_handler)
    old2 = signal.signal(signal.SIGTERM, signal_handler)
    import time
    # signal.pause is not valid in windows
    try:
        while True:
            time.sleep(3600 * 24)
    except QuitException:
        print("Quit server")
        shutdown_event = s.stop(5)
        shutdown_event.wait()
    finally:
        signal.signal(signal.SIGINT, old1)
        signal.signal(signal.SIGTERM, old2)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        main(sys.argv[1:])
    else:
        main()
