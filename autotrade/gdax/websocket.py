import json
import asyncio
import logging
import sys

import websockets.client

import autotrade

URL = 'wss://ws-feed.gdax.com'
LOGGER = logging.getLogger(__name__)


class WebsocketConnection:
    def __init__(self, product, timeout, url=URL):
        self.url = url
        self.product = product
        self.timeout = timeout
        self.connection = None

    @property
    def websocket(self):
        try:
            return self.connection.websocket
        except AttributeError:
            return None

    async def __aenter__(self):
        data = dict(type='subscribe', channels=[dict(name='ticker', product_ids=[self.product])])
        LOGGER.info('Creating connection to %s %s', self.url, data)
        await self.close()  # Close the previous connection.
        self.connection = websockets.connect(self.url, loop=autotrade.engine)

        try:
            await self.connection.__aenter__()
        except Exception as ex:
            LOGGER.error(ex)
        finally:
            await self.send(json.dumps(data))
            return self

    async def __aexit__(self, *args):
        try:
            return await self.connection.__aexit__(*args)
        except AttributeError:
            pass

    async def connect(self):
        return await self.__aenter__()

    async def close(self):
        return await self.__aexit__(*sys.exc_info())

    async def send(self, *args, **kwargs):
        while True:
            try:
                return await asyncio.wait_for(self.websocket.send(*args, **kwargs), self.timeout, loop=autotrade.engine)
            except asyncio.TimeoutError:
                LOGGER.error('%s.send() timeout', self.__class__.__name__)
            except websockets.exceptions.ConnectionClosed as ex:
                LOGGER.error(ex)
                await asyncio.sleep(self.timeout)
            except (AttributeError, websockets.exceptions.ConnectionClosed):
                await asyncio.sleep(self.timeout)
            await self.connect()  # Re-initialize the connection.

    async def recv(self):
        while True:
            try:
                return await asyncio.wait_for(self.websocket.recv(), self.timeout, loop=autotrade.engine)
            except asyncio.TimeoutError:
                LOGGER.error('%s.recv() timeout', self.__class__.__name__)
            except websockets.exceptions.ConnectionClosed as ex:
                LOGGER.error(ex)
                await asyncio.sleep(self.timeout)
            except AttributeError:
                await asyncio.sleep(self.timeout)
            await self.connect()  # Re-initialize the connection.