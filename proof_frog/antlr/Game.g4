grammar Game;

import Shared;

program: moduleImport* game game advantageClause? gameExport EOF;

advantageClause: ADVANTAGE (LEQ | L_ANGLE) expression SEMI;

gameExport: EXPORT AS id SEMI;

ADVANTAGE: 'advantage';
