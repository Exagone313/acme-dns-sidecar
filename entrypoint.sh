#!/bin/bash
set -e
. ~/virtualenv/bin/activate
exec python -m acme_dns_sidecar "$@"
