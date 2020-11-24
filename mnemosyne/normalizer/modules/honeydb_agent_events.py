from normalizer.modules.basenormalizer import BaseNormalizer
import logging

logger = logging.getLogger('__main__')


class HoneydbAgentEvents(BaseNormalizer):
    channels = ('honeydb-agent.events',)

    def normalize(self, data, channel, submission_timestamp, ignore_rfc1918=True):
        o_data = self.parse_record_data(data)

        if ignore_rfc1918 and self.is_RFC1918_addr(o_data['peerIP']):
            logger.warning('Ignoring RFC1918 address per configuration: {}'.format(o_data['peerIP']))
            return []
        try:
            session = {
                'timestamp': submission_timestamp,
                'source_ip': o_data['remote_host'],
                'source_port': o_data['remote_port'],
                'destination_ip': o_data['local_host'],
                'destination_port': o_data['local_port'],
                'honeypot': 'honeydb-agent',
                'protocol': o_data['service']
            }
        except Exception as e:
            logger.error('Error constructing sesssion in Analyzer {}: {}'.format(self.__name__, e))
        relations = [{'session': session}, ]

        return relations
