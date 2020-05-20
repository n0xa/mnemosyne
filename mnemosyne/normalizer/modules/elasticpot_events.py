from normalizer.modules.basenormalizer import BaseNormalizer


class ElasticpotEvents(BaseNormalizer):
    channels = ('elasticpot.events',)

    def normalize(self, data, channel, submission_timestamp, ignore_rfc1918=True):
        o_data = self.parse_record_data(data)

        if ignore_rfc1918 and self.is_RFC1918_addr(o_data['peerIP']):
            return []

        session = {
            'timestamp': submission_timestamp,
            'source_ip': o_data['src_ip'],
            'source_port': o_data['src_port'],
            'destination_ip': o_data['dst_ip'],
            'destination_port': o_data['dst_port'],
            'honeypot': 'elasticpot',
            'protocol': 'elasticsearch'
        }

        relations = [{'session': session}, ]

        return relations
