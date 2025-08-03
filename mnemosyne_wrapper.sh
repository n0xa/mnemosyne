#!/bin/ksh
# Wrapper script to properly activate venv and run mnemosyne

cd /opt/chnserver/mnemosyne
export VIRTUAL_ENV="/opt/chnserver/mnemosyne/venv"
export PATH="$VIRTUAL_ENV/bin:$PATH"
export PYTHONPATH="/opt/chnserver/mnemosyne/mnemosyne:$PYTHONPATH"

# Activate the virtual environment
. venv/bin/activate

# Run mnemosyne
exec python mnemosyne/runner.py --config mnemosyne.cfg
