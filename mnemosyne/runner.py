# Copyright (C) 2012 Johnny Vestergaard <jkv@unixcluster.dk>
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

import gevent
import gevent.monkey

gevent.monkey.patch_all()

import os
import argparse
import logging
import sys

from configparser import ConfigParser
from normalizer.normalizer import Normalizer
from persistance import mnemodb
from feedpuller import feedpuller


logger = logging.getLogger()


def parse_config(config_file):
    if not os.path.isfile(config_file):
        sys.exit("Could not find configuration file: {0}".format(config_file))

    cfg_parser = ConfigParser()
    cfg_parser.read(config_file)

    log_file = None
    loggly_token = None

    if cfg_parser.getboolean('file_log', 'enabled'):
        log_file = cfg_parser.get('file_log', 'file')

    do_logging(log_file, loggly_token)

    config = {}

    if cfg_parser.getboolean('loggly_log', 'enabled'):
        config['loggly_token'] = cfg_parser.get('loggly_log', 'token')

    config['mongo_host'] = cfg_parser.get('mongodb', 'mongo_host')
    config['mongo_port'] = cfg_parser.getint('mongodb', 'mongo_port')
    config['mongo_db'] = cfg_parser.get('mongodb', 'database')
    try:
        config['mongo_indexttl'] = cfg_parser.getint('mongodb', 'mongo_indexttl')
    except ValueError:
        # if no value set or not an int, just set to False
        config['mongo_indexttl'] = False

    config['hpf_feeds'] = cfg_parser.get('hpfriends', 'channels').split(',')
    config['hpf_owner'] = cfg_parser.get('hpfriends', 'owner')
    config['hpf_ident'] = cfg_parser.get('hpfriends', 'ident')
    config['hpf_secret'] = cfg_parser.get('hpfriends', 'secret')
    config['hpf_port'] = cfg_parser.getint('hpfriends', 'hp_port')
    config['hpf_host'] = cfg_parser.get('hpfriends', 'hp_host')

    config['normalizer_ignore_rfc1918'] = cfg_parser.getboolean('normalizer', 'ignore_rfc1918')

    return config


def do_logging(file_log=None, loggly_token=None):
    logger.setLevel(logging.DEBUG)
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s[%(lineno)s][%(filename)s] - %(message)s'

    formatter = logging.Formatter(LOG_FORMAT)

    if file_log:
        file_log = logging.FileHandler(file_log)
        file_log.setLevel(logging.DEBUG)
        file_log.setFormatter(formatter)
        logger.addHandler(file_log)

    console_log = logging.StreamHandler()
    console_log.setLevel(logging.DEBUG)
    console_log.setFormatter(formatter)
    logger.addHandler(console_log)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Mnemosyne')
    parser.add_argument('--config', dest='config_file', default='mnemosyne.cfg')
    parser.add_argument('--reset', action='store_true', default=False)
    parser.add_argument('--stats', action='store_true', default=False)
    parser.add_argument('--no_normalizer', action='store_true', default=False,
                        help='Do not start the normalizer')
    parser.add_argument('--no_feedpuller', action='store_true', default=False,
                        help='Do not start the broker which takes care of storing hpfeed data.')

    args = parser.parse_args()
    c = parse_config(args.config_file)

    git_ref = "Unknown"
    if os.path.isfile('.git/refs/heads/master'):
        with open('.git/refs/heads/master', 'r') as f:
            git_ref = f.readline().rstrip()

    logger.info('Starting mnemosyne. (Git: {0})'.format(git_ref))

    greenlets = {}

    db = mnemodb.MnemoDB(host=c['mongo_host'], port=c['mongo_port'],
                         database_name=c['mongo_db'], indexttl=c['mongo_indexttl'])

    hpfriends_puller = None
    normalizer = None

    if args.reset:
        print('Renormalization (reset) of a large database can take several days.')
        answer = input('Write YES if you want to continue: ')
        if answer == 'YES':
            db.reset_normalized()
        else:
            print('Aborting')
            sys.exit(0)

    if not args.no_feedpuller:
        logger.info("Spawning hpfriends feed puller.")
        hpfriends_puller = feedpuller.FeedPuller(db, c['hpf_ident'], c['hpf_secret'],
                                                 c['hpf_port'], c['hpf_host'], c['hpf_feeds'])
        greenlets['hpfriends-puller'] = gevent.spawn(hpfriends_puller.start_listening)

    if not args.no_normalizer:
        # start menmo and inject persistence module
        normalizer = Normalizer(db, ignore_rfc1918=c['normalizer_ignore_rfc1918'])
        logger.info("Spawning normalizer")
        greenlets['normalizer'] = gevent.spawn(normalizer.start_processing)

    try:

        if args.stats:
            while True:
                counts = db.collection_count()
                log_string = 'Mongo collection count:'
                for key, value in counts.items():
                    if key == 'hpfeed':
                        value = '{0} ({1} in error state)'.format(value, db.get_hpfeed_error_count())
                    log_string += ' {0}: {1}, '.format(key, value)
                logging.info(log_string)
                gevent.sleep(1800)

        gevent.joinall(greenlets.values())
    except KeyboardInterrupt as err:
        if hpfriends_puller:
            logger.info('Stopping HPFriends puller')
            hpfriends_puller.stop()
        if normalizer:
            logger.info('Stopping Normalizer')
            normalizer.stop()

    # wait for greenlets to do a graceful stop
    gevent.joinall(greenlets.values())
