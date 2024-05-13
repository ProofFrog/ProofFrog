grammar Proof;

import Shared;

program: moduleImport* proofHelpers proof EOF;

proofHelpers: (reduction | game)*;

reduction: REDUCTION ID L_PAREN paramList? R_PAREN COMPOSE parameterizedGame AGAINST gameAdversary L_CURLY gameBody R_CURLY;

proof: PROOF COLON (LET COLON lets)? (ASSUME COLON assumptions)? THEOREM COLON theorem  GAMES COLON gameList;

lets: (field SEMI)*;

assumptions: (parameterizedGame SEMI)* (CALLS (LEQ|L_ANGLE) expression SEMI)?;

theorem: parameterizedGame SEMI;

gameList: gameStep SEMI (gameStep SEMI|induction|stepAssumption)*;

gameStep: concreteGame COMPOSE parameterizedGame AGAINST gameAdversary # reductionStep
	| (concreteGame|parameterizedGame) AGAINST gameAdversary # regularStep
	;

induction: INDUCTION L_PAREN ID FROM integerExpression TO integerExpression R_PAREN L_CURLY gameList R_CURLY;

stepAssumption: ASSUME expression SEMI;

gameField: (concreteGame | parameterizedGame) PERIOD ID;

concreteGame: parameterizedGame PERIOD ID;
gameAdversary: parameterizedGame PERIOD ADVERSARY;


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
