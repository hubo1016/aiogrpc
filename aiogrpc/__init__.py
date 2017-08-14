from grpc import ChannelConnectivity, StatusCode, RpcError, RpcContext,\
                ChannelCredentials, CallCredentials, ssl_channel_credentials,\
                metadata_call_credentials,access_token_call_credentials,\
                composite_call_credentials,composite_channel_credentials
import asyncio as _asyncio
import functools as _functools
from grpc import insecure_channel as _insecure_channel
from grpc import secure_channel as _secure_channel
from .channel import Channel


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
        if not fut.done() and state is ChannelConnectivity.READY:
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
    return Channel(_insecure_channel(target, options), loop, executor, standalone_pool_for_streaming)


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
    return Channel(_secure_channel(target, credentials, options),
                   loop, executor, standalone_pool_for_streaming)

