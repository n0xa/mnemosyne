#!/bin/bash

trap "exit 130" SIGINT
trap "exit 137" SIGKILL
trap "exit 143" SIGTERM

set -o errexit
set -o nounset
set -o pipefail


main () {
  python3 /opt/scripts/build_config.py --template "/opt/templates/mnemosyne.cfg.template" --config "/opt/mnemosyne.cfg"
  cd /opt/mnemosyne
  python3 /opt/mnemosyne/runner.py --config /opt/mnemosyne.cfg
}

main "$@"