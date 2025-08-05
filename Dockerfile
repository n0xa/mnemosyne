FROM ubuntu:24.04

LABEL maintainer="n0xa"
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

COPY requirements.txt /opt/requirements.txt
# Install hpfeeds3 from GitHub to get add_user module
RUN pip install --upgrade pip setuptools wheel \
  && pip install -r /opt/requirements.txt \
  && pip install git+https://github.com/n0xa/hpfeeds3.git

COPY mnemosyne /opt/mnemosyne
COPY scripts /opt/scripts
COPY templates /opt/templates
COPY entrypoint.sh /opt/
RUN chmod 0755 /opt/entrypoint.sh

ENTRYPOINT ["/opt/entrypoint.sh"]
