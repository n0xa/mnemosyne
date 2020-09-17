FROM ubuntu:18.04

LABEL maintainer Team STINGAR <team-stingar@duke.edu>
LABEL name "mnemosyne"
LABEL version "1.9"
LABEL release "1"
LABEL summary "Community Honey Network mnemosyne server"
LABEL description "mnemosyne is a normalizer for honeypot data and writes to mongodb"
LABEL authoritative-source-url "https://github.com/CommunityHoneyNetwork/mnemosyne/commits/master"
LABEL changelog-url "https://github.com/CommunityHoneyNetwork/mnemosyne/commits/master"

ENV DEBIAN_FRONTEND "noninteractive"
# hadolint ignore=DL3008,DL3005

RUN apt-get update && apt-get upgrade -y && apt-get install -y gcc git sqlite mongodb python3-dev python3-pip

COPY requirements.txt /opt/requirements.txt
RUN pip3 install -r /opt/requirements.txt
RUN pip3 install git+https://github.com/CommunityHoneyNetwork/hpfeeds3.git

COPY . /opt/
RUN chmod 0755 /opt/entrypoint.sh

ENTRYPOINT ["/opt/entrypoint.sh"]
