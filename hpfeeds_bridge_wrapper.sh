#!/bin/ksh
cd /opt/chnserver/mnemosyne
export VIRTUAL_ENV=/opt/chnserver/mnemosyne/venv
export PATH="$VIRTUAL_ENV/bin:$PATH"
export PYTHONPATH=/opt/chnserver/mnemosyne/mnemosyne:$PYTHONPATH
. venv/bin/activate
exec python3 hpfeeds_bridge.py --config mnemosyne.cfg
