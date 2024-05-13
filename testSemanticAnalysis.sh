#!/bin/bash

skipped="/OTP.scheme$|CounterPRG.scheme|TriplingPRG.scheme$|OFB.scheme$"
RED='\033[0;31m'
NC='\033[0m' # No Color

for file in $(find ill-formed -type f); do
	echo $file | egrep "fixtures" > /dev/null
	isFixture=$?
	if [ $isFixture -ne 0 ]; then
		echo "Checking $file is ill-formed"
		python3 -m proof_frog check $file
		if [ $? -ne 2 ]; then
			echo "$file WAS NOT DETECTED AS ILL-FORMED"
			exit 1
		fi
		echo
	fi
done

for file in $(find examples -type f); do
	echo $file | egrep "proof|game" > /dev/null
	if [ $? -eq 0 ]; then
		continue
	fi
	echo $file | egrep $skipped > /dev/null
	if [ $? -eq 0 ]; then
		echo -e "${RED}FILE ${file} WAS SKIPPED${NC}"
		continue
	fi
	echo "Checking $file is well-formed"
	python3 -m proof_frog check $file
	if [ $? -ne 0 ]; then
		echo "$file WAS NOT DETECTED AS WELL-FORMED"
		exit 1
	fi
done
