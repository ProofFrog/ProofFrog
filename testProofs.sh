#!/bin/bash

RED='\033[0;31m'
NC='\033[0m' # No Color

rm proofOutput.txt
touch proofOutput.txt
succeeded=true
for proof in examples/**/**/**.proof; do
	echo "Running proof $proof"
	echo "========STARTING PROOF $proof========" >> proofOutput.txt
	python3 -m proof_frog prove $proof $1 >> proofOutput.txt
	if [ $? -ne 0 ]; then
		succeeded=false
		echo -e "${RED}FAILED PROOF $proof${NC}"
	fi
	echo "========FINISHING PROOF $proof========" >> proofOutput.txt
done
if [ $succeeded = true ]; then
	echo "All proofs succeeded"
fi
echo "Running Unit Tests"
pytest
if [ $? -ne 0 ] || [ $succeeded = false ]; then
	exit 1
fi
