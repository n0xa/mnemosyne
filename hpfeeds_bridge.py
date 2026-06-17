#!/usr/bin/env python3
"""
hpfeeds_bridge.py -- OpenBSD native deployment workaround.

gevent.monkey.patch_all() in mnemosyne runner.py replaces asyncio selector
with GeventSelector, which does not work on OpenBSD. This script runs as a
separate process (no gevent) and inserts raw hpfeeds events into the
mnemosyne MongoDB hpfeed collection. Mnemosyne normalizer picks them up from
there.

Run alongside mnemosyne started with --no_feedpuller.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime

from configparser import ConfigParser
import pymongo

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
log = logging.getLogger('hpfeeds-bridge')

sys.path.insert(0, '/opt/chnserver/hpfeeds3')
from hpfeeds.asyncio import ClientSession

INACTIVITY = 120


def parse_config(config_file):
    cfg = ConfigParser()
    cfg.read(config_file)
    return {
        'hpf_host': cfg.get('hpfriends', 'hp_host'),
        'hpf_port': cfg.getint('hpfriends', 'hp_port'),
        'hpf_ident': cfg.get('hpfriends', 'ident'),
        'hpf_secret': cfg.get('hpfriends', 'secret'),
        'hpf_feeds': [c.strip() for c in cfg.get('hpfriends', 'channels').split(',')],
        'mongo_host': cfg.get('mongodb', 'mongo_host'),
        'mongo_port': cfg.getint('mongodb', 'mongo_port'),
        'mongo_db': cfg.get('mongodb', 'database'),
    }


async def run(cfg):
    mongo = pymongo.MongoClient(host=cfg['mongo_host'], port=cfg['mongo_port'])
    db = mongo[cfg['mongo_db']]

    while True:
        try:
            async with ClientSession(
                cfg['hpf_host'], cfg['hpf_port'],
                cfg['hpf_ident'], cfg['hpf_secret']
            ) as hpc:
                for feed in cfg['hpf_feeds']:
                    hpc.subscribe(feed)
                log.info('Connected, subscribed to %d channels', len(cfg['hpf_feeds']))

                while True:
                    try:
                        ident, chan, payload = await asyncio.wait_for(
                            hpc.__anext__(), timeout=INACTIVITY
                        )
                    except asyncio.TimeoutError:
                        log.warning('No activity for %ds, reconnecting', INACTIVITY)
                        break
                    except StopAsyncIteration:
                        log.warning('Broker closed connection, reconnecting')
                        break

                    if any(x in chan for x in (';', '"', '{', '}')):
                        continue
                    try:
                        payload_str = payload.decode('utf-8') if isinstance(payload, bytes) else payload
                        try:
                            payload_data = json.loads(payload_str)
                        except (json.JSONDecodeError, ValueError):
                            payload_data = payload_str
                        db.hpfeed.insert_one({
                            'ident': ident,
                            'channel': chan,
                            'payload': payload_data,
                            'timestamp': datetime.utcnow(),
                            'normalized': False,
                        })
                    except UnicodeDecodeError:
                        log.warning('Cannot decode payload from %s:%s', ident, chan)
                    except Exception as e:
                        log.error('DB insert error: %s', e)

        except Exception as e:
            log.error('Connection error: %s: %s', type(e).__name__, e)

        log.info('Reconnecting in 5s...')
        await asyncio.sleep(5)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='/opt/chnserver/mnemosyne/mnemosyne.cfg')
    args = parser.parse_args()
    cfg = parse_config(args.config)
    asyncio.run(run(cfg))
