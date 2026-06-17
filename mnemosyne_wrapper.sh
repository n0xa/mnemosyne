#!/bin/ksh
# Wrapper script to properly activate venv and run mnemosyne.
# On OpenBSD, run with --no_feedpuller because gevent+asyncio GeventSelector
# breaks hpfeeds TCP connections. hpfeeds_bridge.py runs separately instead.
cd /opt/chnserver/mnemosyne
export VIRTUAL_ENV=/opt/chnserver/mnemosyne/venv
export PATH="$VIRTUAL_ENV/bin:$PATH"
export PYTHONPATH=/opt/chnserver/mnemosyne/mnemosyne:$PYTHONPATH
. venv/bin/activate
exec python mnemosyne/runner.py --config mnemosyne.cfg --no_feedpuller
