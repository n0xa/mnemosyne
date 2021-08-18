FROM ubuntu:18.04

LABEL maintainer="Team Stingar <team-stingar@duke.edu>"
LABEL name="mnemosyne"
LABEL version="1.9.1"
LABEL release="1"
LABEL summary="Community Honey Network mnemosyne server"
LABEL description="mnemosyne is a normalizer for honeypot data and writes to mongodb"
LABEL authoritative-source-url="https://github.com/CommunityHoneyNetwork/mnemosyne/commits/master"
LABEL changelog-url="https://github.com/CommunityHoneyNetwork/mnemosyne/commits/master"

ENV DEBIAN_FRONTEND "noninteractive"

# hadolint ignore=DL3008,DL3005
RUN apt-get update \
  && apt-get upgrade -y \
  && apt-get install --no-install-recommends -y gcc git sqlite mongodb python3-dev python3-pip python3-magic \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /opt/requirements.txt
RUN python3 -m pip install --upgrade pip setuptools wheel \
  && python3 -m pip install -r /opt/requirements.txt \
  && python3 -m pip install git+https://github.com/hpfeeds/hpfeeds.git \
  && python3 -m pip install git+https://github.com/CommunityHoneyNetwork/chnutils.git@1.9.3-dev

COPY . /opt/
RUN chmod 0755 /opt/entrypoint.sh

ENTRYPOINT ["/opt/entrypoint.sh"]
