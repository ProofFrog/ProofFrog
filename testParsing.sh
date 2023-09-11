#!/bin/bash

function filter() {
	$1 | egrep -v "Could not get latest version number, attempting to fall back to latest downloaded version...|Found version '4.13.0', this version may be out of date"
}

hopFiles=examples
antlrFiles=proof_frog/antlr/

for primitive in $hopFiles/Primitives/*; do
	echo "Parsing Primitive $primitive"

	filter "antlr4-parse $antlrFiles/Primitive.g4 program $primitive"
done

for scheme in $hopFiles/Schemes/**/*.scheme; do
	echo "Parsing Scheme $scheme"
	filter "antlr4-parse $antlrFiles/Scheme.g4 program $scheme"
done

for game in $hopFiles/Games/**/*.game; do
	echo "Parsing Game $game"
	filter "antlr4-parse $antlrFiles/Game.g4 program $game"
done

for proof in $hopFiles/Proofs/**/*; do
	echo "Parsing Proof $proof"
	filter "antlr4-parse $antlrFiles/Proof.g4 program $proof"
done
