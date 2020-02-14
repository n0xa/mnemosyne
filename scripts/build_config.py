import os
import uuid
import argparse
import configparser
from hpfeeds.add_user import create_user


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    OWNER = os.environ.get("OWNER", "chn")
    IDENT = os.environ.get("IDENT", "mnemosyne")
    SECRET = os.environ.get("SECRET", "")
    HPFEEDS_HOST = os.environ.get("HPFEEDS_HOST", "hpfeeds3")
    HPFEEDS_PORT = os.environ.get("HPFEEDS_PORT", "10000")
    CHANNELS = os.environ.get("CHANNELS", "")
    MONGODB_HOST = os.environ.get("MONGODB_HOST", "mongodb")
    MONGODB_PORT = os.environ.get("MONGODB_PORT", "27017")
    MONGODB_TTL = os.environ.get("MONGODB_TTL", "")
    RFC1918 = os.environ.get("RFC1918", "True")

    config = configparser.ConfigParser()
    config.read(args.template)

    if SECRET:
        secret = args.secret
    else:
        secret = str(uuid.uuid4()).replace("-", "")

    config['hpfriends']['ident'] = IDENT
    config['hpfriends']['secret'] = secret
    config['hpfriends']['hp_host'] = HPFEEDS_HOST
    config['hpfriends']['hp_port'] = HPFEEDS_PORT
    config['hpfriends']['channels'] = CHANNELS

    config['mongodb']['mongo_host'] = MONGODB_HOST
    config['mongodb']['mongo_port'] = MONGODB_PORT
    config['mongodb']['mongo_indexttl'] = MONGODB_TTL

    config['normalizer']['ignore_rfc1918'] = RFC1918

    create_user(host=MONGODB_HOST, port=int(MONGODB_PORT), owner=OWNER,
                ident=IDENT, secret=secret, publish="", subscribe=CHANNELS)

    with open(args.config, 'w') as configfile:
        config.write(configfile)
    return 0


if __name__ == "__main__":
    main()
