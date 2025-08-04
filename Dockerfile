FROM ubuntu:24.04

LABEL maintainer="Team Stingar <team-stingar@duke.edu>"
LABEL name="mnemosyne"
LABEL version="1.9.1"
LABEL release="1"
LABEL summary="Community Honey Network mnemosyne server"
LABEL description="mnemosyne is a normalizer for honeypot data and writes to mongodb"
LABEL authoritative-source-url="https://github.com/n0xa/mnemosyne/commits/master"
LABEL changelog-url="https://github.com/n0xa/mnemosyne/commits/master"

ENV DEBIAN_FRONTEND "noninteractive"

# hadolint ignore=DL3008,DL3005
RUN apt-get update \
  && apt-get upgrade -y \
  && apt-get install --no-install-recommends -y gcc git sqlite3 python3-dev python3-pip python3-venv python3-magic \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY mnemosyne/requirements.txt /opt/requirements.txt
# Copy local hpfeeds3 first for our PyMongo fixes
COPY hpfeeds3 /tmp/hpfeeds3
RUN pip install --upgrade pip setuptools wheel \
  && pip install -r /opt/requirements.txt \
  && pip install /tmp/hpfeeds3

COPY mnemosyne /opt/
RUN chmod 0755 /opt/entrypoint.sh

ENTRYPOINT ["/opt/entrypoint.sh"]
