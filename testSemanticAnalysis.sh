#!/bin/bash

for file in examples/ill-formed/**/*; do
	echo "Checking $file is ill-formed"
	python3 -m proof_frog check $file 2> /dev/null
	if [ $? -ne 1 ]; then
		echo "$file WAS NOT DETECTED AS ILL-FORMED"
		exit 1
	fi
done
