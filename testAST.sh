#!/bin/bash

for primitive in examples/Primitives/*; do
	parsedOutput=$(mktemp)
	parsedOutput2=$(mktemp)
	trimmedPrimitive=$(mktemp)

	python3 src/main.py $primitive > $parsedOutput

	if [ $# -gt 1 ]; then
		echo "Original File:"
		cat $primitive
		echo "New File:"
		cat $parsedOutput
	fi

	cat $parsedOutput | tr -d "[:space:]" > $parsedOutput2
	cat $primitive | tr -d "[:space:]" > $trimmedPrimitive

	echo "Diff for $primitive"
	diff $parsedOutput2 $trimmedPrimitive
	rm $parsedOutput
	rm $parsedOutput2
	rm $trimmedPrimitive
done
