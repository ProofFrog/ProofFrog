#!/bin/bash

rm -r src/parsing/*
touch src/parsing/__init__.py

for grammar in Game.g4 Primitive.g4 Proof.g4 Scheme.g4; do
	antlr4 -Dlanguage=Python3 -visitor -no-listener src/antlr/$grammar
done
mv src/antlr/*interp src/antlr/*.tokens src/antlr/*.py src/parsing
