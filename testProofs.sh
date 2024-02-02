#!/bin/bash

RED='\033[0;31m'
NC='\033[0m' # No Color

proofs="examples/Proofs/SymEnc/OTUC=>OTS.proof
examples/Proofs/SymEnc/CPA$=>CPA.proof
examples/Proofs/SymEnc/GeneralDoubleOTUC.proof
examples/Proofs/SymEnc/OTUC=>DoubleOTUC.proof
examples/Book/2/2_13.proof
examples/Book/5/5_3.proof
examples/Book/5/5_5_TriplingPRGSecure.proof
examples/Proofs/PubEnc/OTS=>CPA.proof
examples/Proofs/PubEnc/Hybrid.proof
examples/Proofs/SymEnc/EncryptThenMACCCA.proof";

rm proofOutput.txt
touch proofOutput.txt
succeeded=true
for proof in $proofs; do
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
