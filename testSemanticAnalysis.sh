#!/bin/bash

rm errorOutput.txt

for file in $(find examples -type f); do
	echo $file | egrep "ill-formed" > /dev/null
	if [ $? -eq 0 ]; then
		echo "Checking $file is ill-formed"
		python3 -m proof_frog check $file 2>> errorOutput.txt
		if [ $? -ne 1 ]; then
			echo "$file WAS NOT DETECTED AS ILL-FORMED"
			exit 1
		fi
	else
		echo $file | egrep "proof|game" > /dev/null
		if [ $? -eq 0 ]; then
			continue
		fi
		echo "Checking $file is well-formed"
		python3 -m proof_frog check $file 2>> errorOutput.txt
		if [ $? -ne 0 ]; then
			echo "$file WAS NOT DETECTED AS WELL-FORMED"
			exit 1
		fi
	fi
done
