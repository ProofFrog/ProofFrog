grammar Scheme;

import Shared;

program: moduleImport* scheme EOF;

scheme: SCHEME id L_PAREN paramList? R_PAREN EXTENDS id L_CURLY schemeBody R_CURLY;

schemeBody: (REQUIRES expression SEMI)* (field SEMI | method)+;

REQUIRES: 'requires';
SCHEME: 'Scheme';
EXTENDS: 'extends';
