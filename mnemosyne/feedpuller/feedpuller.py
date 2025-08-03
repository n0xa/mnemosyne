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
import gevent
from hpfeeds.blocking import ClientSession as HpfeedsConnection

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
        while self.enabled:
            try:
                self.hpc = HpfeedsConnection(self.host, self.port, self.ident, self.secret)
                
                # Subscribe to feeds
                for feed in self.feeds:
                    self.hpc.subscribe(feed)
                
                # Process messages
                for ident, chan, payload in self.hpc:
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
                print(ex)
                logger.exception('Exception caught: {0}'.format(ex))
                if self.hpc:
                    self.hpc.close()
            # throttle
            gevent.sleep(5)

    def stop(self):
        logger.info("FeedPuller stopped.")
        self.enabled = False
        if self.hpc:
            self.hpc.close()
        self.enabled = False

    def _activity_checker(self):
        while self.enabled:
            if self.hpc is not None and self.hpc.connected:
                difference = datetime.now() - self.last_received
                if difference.seconds > 120:
                    logger.warning('No activity for 120 seconds, forcing reconnect')
                    self.hpc.stop()
            gevent.sleep(120)
