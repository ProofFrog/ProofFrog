#!/bin/bash

RED='\033[0;31m'
NC='\033[0m' # No Color

for proof in examples/**/**/**.proof; do
	echo "Running proof $proof"
	python3 -m proof_frog check $proof
done
