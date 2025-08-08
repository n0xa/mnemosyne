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

from datetime import datetime
import logging
import asyncio
import gevent
from hpfeeds.asyncio import ClientSession as HpfeedsConnection

logger = logging.getLogger('__main__')


class FeedPuller(object):
    def __init__(self, database, ident, secret, port, host, feeds):

        self.database = database

        self.ident = ident
        self.secret = secret
        self.port = port
        self.host = host
        self.feeds = feeds
        self.last_received = datetime.now()
        self.hpc = None
        self.enabled = True

    def start_listening(self):
        gevent.spawn_later(15, self._activity_checker)
        # Start the async event loop in a gevent greenlet
        gevent.spawn(self._run_async_listener)

    def _run_async_listener(self):
        """Run the asyncio event loop for hpfeeds connection"""
        try:
            # Create new event loop for this greenlet
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the async listener
            loop.run_until_complete(self._async_listener())
        except Exception as ex:
            logger.exception('Exception in async listener: {0}'.format(ex))
        finally:
            try:
                loop.close()
            except:
                pass

    async def _async_listener(self):
        """Async method to handle hpfeeds connection and message processing"""
        while self.enabled:
            try:
                self.hpc = HpfeedsConnection(self.host, self.port, self.ident, self.secret)
                
                # Wait for connection and subscribe to feeds
                async with self.hpc as client:
                    for feed in self.feeds:
                        client.subscribe(feed)
                    
                    logger.info(f"Connected to HPFeeds broker, subscribed to {len(self.feeds)} channels")
                    
                    # Process messages
                    async for ident, chan, payload in client:
                        if not self.enabled:
                            break
                            
                        self.last_received = datetime.now()
                        if not any(x in chan for x in (';', '"', '{', '}')):
                            try:
                                # Handle both string and bytes payload
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
                    
            # Throttle reconnection attempts
            await asyncio.sleep(5)

    def stop(self):
        logger.info("FeedPuller stopped.")
        self.enabled = False

    def _activity_checker(self):
        while self.enabled:
            difference = datetime.now() - self.last_received
            if difference.seconds > 120:
                logger.warning('No activity for 120 seconds - async client will auto-reconnect')
            gevent.sleep(120)
