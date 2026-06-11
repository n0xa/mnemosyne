# Copyright (C) 2013 Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import logging
import asyncio
import gevent
from hpfeeds.asyncio import ClientSession as HpfeedsConnection

logger = logging.getLogger('__main__')

INACTIVITY_TIMEOUT = 120


class FeedPuller(object):
    def __init__(self, database, ident, secret, port, host, feeds):

        self.database = database

        self.ident = ident
        self.secret = secret
        self.port = port
        self.host = host
        self.feeds = feeds
        self.hpc = None
        self.enabled = True

    def start_listening(self):
        gevent.spawn(self._run_async_listener)

    def _run_async_listener(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_listener())
        except Exception as ex:
            logger.exception('Exception in async listener: {0}'.format(ex))
        finally:
            try:
                loop.close()
            except Exception:
                pass

    async def _async_listener(self):
        while self.enabled:
            try:
                self.hpc = HpfeedsConnection(self.host, self.port, self.ident, self.secret)

                async with self.hpc as client:
                    for feed in self.feeds:
                        client.subscribe(feed)

                    logger.info(f"Connected to HPFeeds broker, subscribed to {len(self.feeds)} channels")

                    while self.enabled:
                        try:
                            ident, chan, payload = await asyncio.wait_for(
                                client.__anext__(), timeout=INACTIVITY_TIMEOUT
                            )
                        except asyncio.TimeoutError:
                            logger.warning(f'No activity for {INACTIVITY_TIMEOUT}s, reconnecting')
                            break
                        except StopAsyncIteration:
                            logger.warning('HPFeeds connection closed by broker, reconnecting')
                            break

                        if not any(x in chan for x in (';', '"', '{', '}')):
                            try:
                                if isinstance(payload, bytes):
                                    payload_str = payload.decode("utf-8")
                                else:
                                    payload_str = payload
                                self.database.insert_hpfeed(ident, chan, payload_str)
                            except UnicodeDecodeError:
                                logger.warning(f"Failed to decode payload from {ident}:{chan}")

            except Exception as ex:
                logger.exception('Exception caught in async listener: {0}'.format(ex))
                if not self.enabled:
                    break

            await asyncio.sleep(5)

    def stop(self):
        logger.info("FeedPuller stopped.")
        self.enabled = False
