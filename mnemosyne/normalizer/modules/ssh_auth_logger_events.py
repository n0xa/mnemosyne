from normalizer.modules.basenormalizer import BaseNormalizer
import logging


class SSHAuthLogger(BaseNormalizer):
    channels = ('ssh-auth-logger.events',)

    def normalize(self, data, channel, submission_timestamp, ignore_rfc1918=True):
        o_data = self.parse_record_data(data)

        if ignore_rfc1918 and self.is_RFC1918_addr(o_data['src_ip']):
            return []

        session = {
            'timestamp': submission_timestamp,
            'source_ip': o_data['src'],
            'source_port': o_data['spt'],
            'destination_port': o_data['dpt'],
            'honeypot': 'ssh-auth-logger',
            'protocol': 'ssh',
            'session_ssh': {'version': o_data['client_version']}
        }

        if o_data.get('password'):
            session['auth_attempts']= {'login': o_data['duser'], 'password': o_data['password']}
        elif o_data.get('fingerprint'):
            session['auth_attempts']= {'login': o_data['duser'], 'fingerprint': o_data['fingerprint'], 'keytype': o_data['keytype']}

        relations = [{'session': session}, ]

        return relations
