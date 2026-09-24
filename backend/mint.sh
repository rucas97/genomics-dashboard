#!/bin/bash
# Convenience wrapper around mint_license.py
# Usage: ./mint.sh customer@lab.org standard 365 <fingerprint>

if [ $# -lt 4 ]; then
    echo "Usage: $0 <email> <tier> <days> <fingerprint>"
    echo "Tiers: trial, standard, enterprise"
    exit 1
fi

# Load private key from .env.mint
if [ ! -f .env.mint ]; then
    echo "Error: .env.mint not found. Copy .env.mint.example to .env.mint and paste your private key."
    exit 1
fi

source .env.mint

if [ -z "$LICENSE_PRIVATE_KEY" ]; then
    echo "Error: LICENSE_PRIVATE_KEY not set in .env.mint"
    exit 1
fi

python mint_license.py \
    --email "$1" \
    --tier "$2" \
    --days "$3" \
    --fingerprint "$4" \
    --private-key "$LICENSE_PRIVATE_KEY" \
    --pretty
