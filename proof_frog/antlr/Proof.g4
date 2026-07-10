grammar Proof;

import Shared;

program: moduleImport* helpersBefore=proofHelpers proof helpersAfter=proofHelpers EOF;

proofHelpers: (reduction | game)*;

reduction: REDUCTION id L_PAREN paramList? R_PAREN COMPOSE parameterizedGame AGAINST gameAdversary L_CURLY gameBody R_CURLY;

proof: PROOF COLON (LET COLON lets)? (ASSUME COLON assumptions)? (REQUIRES COLON requirements)? (LEMMA COLON lemmas)? THEOREM COLON theorem (BOUND COLON boundExpression SEMI)? GAMES COLON gameList;

boundExpression
	: <assoc=right> boundExpression CARET boundExpression   #boundExponentiate
	| boundExpression TIMES boundExpression                 #boundMultiply
	| boundExpression DIVIDE boundExpression                #boundDivide
	| SUBTRACT boundExpression                              #boundNegate
	| boundExpression PLUS boundExpression                  #boundAdd
	| boundExpression SUBTRACT boundExpression              #boundSubtract
	| VBAR type VBAR                                        #boundCardinality
	| ADVANTAGE L_PAREN parameterizedGame (COMPOSE reductionRef)? R_PAREN #boundAdvantage
	| lvalue                                                #boundLvalue
	| INT                                                   #boundInt
	| L_PAREN boundExpression R_PAREN                       #boundParen
	;

reductionRef: id (L_PAREN argList? R_PAREN)?;

requirements: (requirement SEMI)*;
requirement: expression IS PRIME  # primeRequirement
           ;

lets: (letEntry SEMI)*;

letEntry: field                                    # letField
	| variable SAMPLES expression                  # letSample
	;

assumptions: (parameterizedGame SEMI)* (CALLS (LEQ|L_ANGLE) expression SEMI)?;

lemmas: lemmaEntry*;
lemmaEntry: parameterizedGame BY FILESTRING SEMI;

theorem: parameterizedGame SEMI;

gameList: gameStep SEMI (gameStep SEMI|induction|stepAssumption)*;

gameStep: concreteGame COMPOSE parameterizedGame AGAINST gameAdversary # reductionStep
	| (concreteGame|parameterizedGame) AGAINST gameAdversary # regularStep
	;

induction: INDUCTION L_PAREN id FROM integerExpression TO integerExpression R_PAREN L_CURLY gameList R_CURLY;

stepAssumption: ASSUME expression SEMI;

gameField: (concreteGame | parameterizedGame) PERIOD id;

concreteGame: parameterizedGame PERIOD id;
gameAdversary: parameterizedGame PERIOD ADVERSARY;


REDUCTION: 'Reduction';
AGAINST: 'against';
ADVERSARY: 'Adversary';
COMPOSE: 'compose';
PROOF: 'proof';
ASSUME: 'assume';
THEOREM: 'theorem';
GAMES: 'games';
BOUND: 'bound';
ADVANTAGE: 'advantage';
LET: 'let';
CALLS: 'calls';
INDUCTION: 'induction';
LEMMA: 'lemma';
BY: 'by';
FROM: 'from';
REQUIRES: 'requires';
IS: 'is';
PRIME: 'prime';
