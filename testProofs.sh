#!/bin/bash

proofs="examples/Proofs/SymEnc/OTUC=>OTS.proof
examples/Proofs/SymEnc/CPA$=>CPA.proof
examples/Proofs/SymEnc/GeneralDoubleOTUC.proof
examples/Proofs/SymEnc/OTUC=>DoubleOTUC.proof
examples/Book/2/2_13.proof
examples/Book/5/5_3.proof
examples/Book/5/5_5_LengthTriplingPRG.proof";

rm proofOutput.txt
touch proofOutput.txt
succeeded=true
for proof in $proofs; do
	echo "Running proof $proof"
	echo "========STARTING PROOF $proof========" >> proofOutput.txt
	python3 -m proof_frog prove $proof >> proofOutput.txt
	if [ $? -ne 0 ]; then
		succeeded=false
		echo "FAILED PROOF $proof"
	fi
	echo "========FINISHING PROOF $proof========" >> proofOutput.txt
done
if [ $succeeded = true ]; then
	echo "All proofs succeeded"
fi
