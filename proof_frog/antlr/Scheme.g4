grammar Scheme;

import Shared;

program: moduleImport* scheme EOF;

scheme: SCHEME ID L_PAREN paramList? R_PAREN EXTENDS ID L_CURLY schemeBody R_CURLY;

schemeBody: (REQUIRES expression SEMI)* (field SEMI | method)+;

REQUIRES: 'requires';
SCHEME: 'Scheme';
EXTENDS: 'extends';
