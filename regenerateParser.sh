#!/bin/bash
source ~/.bash_aliases
shopt -s expand_aliases

rm -r proof_frog/parsing/*
touch proof_frog/parsing/__init__.py

for grammar in Game.g4 Primitive.g4 Proof.g4 Scheme.g4; do
	antlr4 -Dlanguage=Python3 -visitor -no-listener proof_frog/antlr/$grammar
done
mv proof_frog/antlr/*interp proof_frog/antlr/*.tokens proof_frog/antlr/*.py proof_frog/parsing
