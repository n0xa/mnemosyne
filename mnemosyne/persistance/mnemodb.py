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

import logging
import string
import time
import json
from datetime import datetime

from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidStringData
from persistance.preagg_reports import ReportGenerator
from gevent import Greenlet


logger = logging.getLogger('__main__')


class MnemoDB(object):
    def __init__(self, host, port, database_name, indexttl=False):
        logger.info('Connecting to mongodb, using "{0}" as database.'.format(database_name))
        conn = MongoClient(host=host, port=port)
        self.rg = ReportGenerator(host=host, port=port, database_name=database_name)
        self.db = conn[database_name]
        self.create_index(indexttl)
        self.compact_database()

    def create_index(self, indexttl):
        self.db.hpfeed.create_index([('normalized', 1), ('last_error', 1)], unique=False, background=True)
        self.db.url.create_index('url', unique=True, background=True)
        self.db.url.create_index('extractions.hashes.md5', unique=False, background=True)
        self.db.url.create_index('extractions.hashes.sha1', unique=False, background=True)
        self.db.url.create_index('extractions.hashes.sha512', unique=False, background=True)
        self.db.file.create_index('hashes', unique=True, background=True)
        self.db.dork.create_index('content', unique=False, background=True)
        self.db.session.create_index('protocol', unique=False, background=True)
        self.db.session.create_index('source_ip', unique=False, background=True)
        self.db.session.create_index('source_port', unique=False, background=True)
        self.db.session.create_index('destination_port', unique=False, background=True)
        self.db.session.create_index('destination_ip', unique=False, background=True)
        self.db.session.create_index('source_port', unique=False, background=True)
        self.db.session.create_index('honeypot', unique=False, background=True)
        self.set_coll_indexttl('session', indexttl)
        self.set_coll_indexttl('hpfeed', indexttl)
        self.db.session.create_index('identifier', unique=False, background=True)
        self.db.daily_stats.create_index([('channel', 1), ('date', 1)])
        self.db.counts.create_index([('identifier', 1), ('date', 1)])
        self.db.counts.create_index('identifier', unique=False, background=True)
        self.db.metadata.create_index([('ip', 1), ('honeypot', 1)])
        self.db.metadata.create_index('ip', unique=False, background=True)

    def set_coll_indexttl(self, coll, indexttl):
        """Sets the Index TTL (expireAfterSeconds property) on the timestamp field
        of a collection.
        Inputs:
            coll (str): collection name
            indexttl (int): number, in seconds, of how long after timestamp field value
                before Mongo TTL worker removes the expired document
        Outputs: none
        """
        coll_info_timestamp = self.db[coll].index_information().get('timestamp_1')
        if coll_info_timestamp:
            coll_info_ttlsecs = coll_info_timestamp.get('expireAfterSeconds')
        else:
            coll_info_ttlsecs = None
        # if expireAfterSeconds not set on Index and indexttl != False
        if not coll_info_ttlsecs and indexttl:
            if coll_info_timestamp:
                self.db[coll].drop_index('timestamp_1')
            self.db[coll].create_index('timestamp', unique=False,
                                       background=True, expireAfterSeconds=indexttl)
        # if expireAfterSeconds IS set but indexttl == False (indicating it no longer should be)
        elif coll_info_ttlsecs and not indexttl:
            self.db[coll].drop_index('timestamp_1')
            self.db[coll].create_index('timestamp', unique=False, background=True)
        # if a user has changed the expireTTL value since last set
        elif coll_info_ttlsecs and indexttl and indexttl != coll_info_ttlsecs:
            self.db.command('collMod', coll,
                            index={'keyPattern': {'timestamp': 1},
                                   'background': True,
                                   'expireAfterSeconds': indexttl
                                   })
        # self.db.session.create_index('timestamp', unique=False, background=True)
        # self.db.hpfeed.create_index('timestamp', unique=False, background=True)

    def compact_database(self):
        # runs 'compact' on each collection in mongodb to free any available space back to OS
        # warning: 'compact' _IS_ a blocking operation
        collections = self.db.list_collection_names()
        for collection in collections:
            logger.info('Compacting collection %s', collection)
            self.db.command('compact', collection, force=True)

    def insert_normalized(self, ndata, hpfeed_id, identifier=None):
        assert isinstance(hpfeed_id, ObjectId)
        # ndata is a collection of dictionaries
        for item in ndata:
            # key = collection name, value = content
            for collection, document in item.items():
                if collection == 'url':
                    if 'extractions' in document:
                        self.db[collection].update_one({'url': document['url']},
                                                   {'$push': {'extractions': {'$each': document['extractions']},
                                                             'hpfeeds_ids': hpfeed_id}},
                                                   upsert=True)
                    else:
                        self.db[collection].update_one({'url': document['url']}, {'$push': {'hpfeeds_ids': hpfeed_id}},
                                                   upsert=True)
                elif collection == 'file':
                    self.db[collection].update_one({'hashes.sha512': document['hashes']['sha512']},
                                               {'$set': document, '$push': {'hpfeed_ids': hpfeed_id}},
                                               upsert=True)
                elif collection == 'session':
                    document['hpfeed_id'] = hpfeed_id
                    if identifier:
                        document['identifier'] = identifier
                    self.db[collection].insert_one(document)
                elif collection == 'dork':
                    self.db[collection].update_one({'content': document['content'], 'type': document['type']},
                                               {'$set': {'lasttime': document['timestamp']},
                                                '$inc': {'count': document['count']}},
                                               upsert=True)
                elif collection == 'metadata':
                    if 'ip' in document and 'honeypot' in document:
                        query = {
                            'ip': document['ip'],
                            'honeypot': document['honeypot']
                        }
                        values = dict((k, v) for k, v in document.items() if k not in ['ip', 'honeypot'])
                        self.db[collection].update(query, {'$set': values}, upsert=True)
                else:
                    raise Warning('{0} is not a know collection type.'.format(collection))
                    # if we end up here everything if ok - setting hpfeed entry to normalized
        self.db.hpfeed.update({'_id': hpfeed_id}, {'$set': {'normalized': True},
                                                   '$unset': {'last_error': 1, 'last_error_timestamp': 1}})

    def insert_hpfeed(self, ident, channel, payload):
        # thanks rep!
        # mongo can't handle non-utf-8 strings, therefore we must encode
        # raw binaries
        if [i for i in payload[:20] if i not in string.printable]:
            payload = str(payload).encode('hex')
        else:
            payload = str(payload)
            try:
                payload = json.loads(payload)
            except ValueError:
                logger.warning('insert_hpfeed: payload was not JSON, storing as a string (ident=%s, channel=%s)',
                               ident, channel)

        timestamp = datetime.utcnow()
        entry = {'channel': channel,
                 'ident': ident,
                 'payload': payload,
                 'timestamp': timestamp,
                 'normalized': False}
        try:
            self.db.hpfeed.insert(entry)
        except InvalidStringData as err:
            logger.error(
                'Failed to insert hpfeed data on {0} channel due to invalid string data. ({1})'.format(
                    entry['channel'], err))

        self.db.counts.update(
            {'identifier': ident, 'date': timestamp.strftime('%Y%m%d')},
            {"$inc": {"event_count": 1}},
            upsert=True
        )
        self.db.counts.update(
            {'identifier': channel, 'date': timestamp.strftime('%Y%m%d')},
            {"$inc": {"event_count": 1}},
            upsert=True
        )
        self.rg.hpfeeds(entry)

    def hpfeed_set_errors(self, items):
        """Marks hpfeeds entries in the datastore as having errored while normalizing.

        :param items: a list of hpfeed entries.
        """
        for item in items:
            self.db.hpfeed.update({'_id': item['_id']},
                                  {'$set':
                                   {'last_error': str(item['last_error']),
                                    'last_error_timestamp': item['last_error_timestamp']}
                                   })

    def get_hpfeed_data(self, get_before_id, max=250):
        """Fetches unnormalized hpfeed items from the datastore.

        :param max: maximum number of entries to return
        :param get_before_id: only return entries which are below the value of this ObjectId
        :return: a list of dictionaries
        """

        data = list(self.db.hpfeed.find({'_id': {'$lt': get_before_id}, 'normalized': False,
                                         'last_error': {'$exists': False}}, limit=max,
                                        sort=[('_id', -1)]))
        return data

    def reset_normalized(self):
        """Deletes all normalized data from the datastore."""

        logger.info('Initiating database reset - all normalized data will be deleted. (Starting timer)')
        start = time.time()
        for collection in self.db.list_collection_names():
            if collection not in ['system.indexes', 'hpfeed', 'hpfeeds']:
                logger.warning('Dropping collection: {0}.'.format(collection))
                self.db.drop_collection(collection)
        logger.info('All collections dropped. (Elapse: {0})'.format(time.time() - start))
        logger.info('Dropping indexes before bulk operation.')
        self.db.hpfeed.drop_indexes()
        logger.info('Indexes dropped(Elapse: {0}).'.format(time.time() - start))
        logger.info('Resetting normalization flags from hpfeeds collection.')
        self.db.hpfeed.update({}, {"$set": {'normalized': False},
                                   '$unset': {'last_error': 1, 'last_error_timestamp': 1}}, multi=True)
        logger.info('Done normalization flags from hpfeeds collection.(Elapse: {0}).'.format(time.time() - start))
        logger.info('Recreating indexes.')
        self.create_index()
        logger.info('Done recreating indexes (Elapse: {0})'.format(time.time() - start))

        logger.info('Full reset done in {0} seconds'.format(time.time() - start))

        # This is a one-off job to generate stats for hpfeeds which takes a while.
        Greenlet.spawn(self.rg.do_legacy_hpfeeds)

    def collection_count(self):
        result = {}
        for collection in self.db.list_collection_names():
            if collection not in ['system.indexes']:
                count = self.db[collection].count()
                result[collection] = count
        return result

    def get_hpfeed_error_count(self):
        count = self.db.hpfeed.find({'last_error': {'$exists': 1}}).count()
        return count
