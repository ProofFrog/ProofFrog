grammar Proof;

import Shared;

program: moduleImport* (reduction|game)* proof EOF;

reduction: REDUCTION ID L_PAREN paramList? R_PAREN COMPOSE gameModule AGAINST gameAdversary L_CURLY gameBody R_CURLY;

proof: PROOF COLON (LET COLON lets)? (ASSUME COLON assumptions)? THEOREM COLON theorem  GAMES COLON gameList;

lets: (field SEMI)*;

assumptions: (gameModule SEMI)* (CALLS (LEQ|L_ANGLE) expression SEMI)? (gameModule SEMI)*;

theorem: gameModule SEMI;

gameList: (gameStep SEMI|induction)+;

gameStep: concreteGame COMPOSE gameModule AGAINST gameAdversary
	| (concreteGame|gameModule) AGAINST gameAdversary;

induction: INDUCTION L_PAREN ID FROM expression TO expression R_PAREN L_CURLY (gameStep SEMI)+ R_CURLY;

gameModule: ID L_PAREN argList? R_PAREN;
gameAdversary: gameModule PERIOD ADVERSARY;
concreteGame: gameModule PERIOD ID;

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