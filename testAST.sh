#!/bin/bash

verbose=true

function runTest {

	fileName=$1

	parsedOutput=$(mktemp)
	parsedOutput2=$(mktemp)
	trimmedOriginal=$(mktemp)

	python3 -m proof_frog parse $fileName > $parsedOutput

	cat $parsedOutput | tr -d "[:space:]" > $parsedOutput2
	cat $fileName | egrep -v '//' | tr -d "[:space:]" > $trimmedOriginal

	echo "Diff for $fileName"
	diff $parsedOutput2 $trimmedOriginal

	if [ $? -ne 0 -a $verbose == true ]; then
		echo "Original File:"
		cat $fileName
		echo "New File:"
		cat $parsedOutput
	fi
	rm $parsedOutput
	rm $parsedOutput2
	rm $trimmedOriginal
}

for primitive in examples/Primitives/*; do
	runTest $primitive
done

for scheme in examples/Schemes/**/*; do
	runTest $scheme
done

for game in examples/Games/**/*; do
	runTest $game
done

for proof in examples/Proofs/**/*.proof; do
	runTest $proof
done
