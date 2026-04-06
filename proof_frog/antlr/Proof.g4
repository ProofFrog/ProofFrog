grammar Proof;

import Shared;

program: moduleImport* proofHelpers proof EOF;

proofHelpers: (reduction | game)*;

reduction: REDUCTION id L_PAREN paramList? R_PAREN COMPOSE parameterizedGame AGAINST gameAdversary L_CURLY gameBody R_CURLY;

proof: PROOF COLON (LET COLON lets)? (ASSUME COLON assumptions)? (LEMMA COLON lemmas)? THEOREM COLON theorem  GAMES COLON gameList;

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
LET: 'let';
CALLS: 'calls';
INDUCTION: 'induction';
LEMMA: 'lemma';
BY: 'by';
FROM: 'from';
