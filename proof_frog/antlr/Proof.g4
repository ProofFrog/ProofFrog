grammar Proof;

import Shared;

program: moduleImport* proofHelpers proof EOF;

proofHelpers: (reduction | game)*;

reduction: REDUCTION ID L_PAREN paramList? R_PAREN COMPOSE parameterizedGame AGAINST gameAdversary L_CURLY gameBody R_CURLY;

proof: PROOF COLON (LET COLON lets)? (ASSUME COLON assumptions)? THEOREM COLON theorem  GAMES COLON gameList;

lets: (field SEMI)*;

assumptions: (parameterizedGame SEMI)* (CALLS (LEQ|L_ANGLE) expression SEMI)?;

theorem: parameterizedGame SEMI;

gameList: (gameStep SEMI|induction)+;

gameStep: concreteGame COMPOSE parameterizedGame AGAINST gameAdversary # reductionStep
	| (concreteGame|parameterizedGame) AGAINST gameAdversary # regularStep
	;

induction: INDUCTION L_PAREN ID FROM integerExpression TO integerExpression R_PAREN L_CURLY (gameStep SEMI)+ R_CURLY;

varOrField: id (PERIOD id)*;

parameterizedGame: ID L_PAREN argList? R_PAREN;
gameAdversary: parameterizedGame PERIOD ADVERSARY;
concreteGame: parameterizedGame PERIOD ID;

REDUCTION: 'Reduction';
AGAINST: 'against';
ADVERSARY: 'Adversary';
COMPOSE: 'compose';
PROOF: 'proof';
ASSUME: 'assume';
THEOREM: 'theorem';
GAMES: 'games';
LET: 'let';
CALLS: 'calls';
INDUCTION: 'induction';
FROM: 'from';
