grammar Shared;

game: GAME ID L_PAREN paramList? R_PAREN L_CURLY gameBody R_CURLY;

gameBody: (field SEMI)* method+
	| (field SEMI)* method* gamePhase+;

gamePhase: PHASE L_CURLY (method)+ ORACLES COLON L_SQUARE id (COMMA id)* R_SQUARE SEMI R_CURLY;

gameExport: EXPORT L_PAREN ID COMMA ID R_PAREN AS ID SEMI;

field: variable (EQUALS expression)?;

initializedField: variable EQUALS expression;

method: methodSignature methodBody;

block: statement*;

statement: type id SEMI #varDeclStatement
	| type lvalue EQUALS expression SEMI #varDeclWithValueStatement
	| type lvalue SAMPLES expression SEMI #varDeclWithSampleStatement
	| lvalue EQUALS expression SEMI #assignmentStatement
	| lvalue SAMPLES expression SEMI #sampleStatement
	| expression L_PAREN argList? R_PAREN SEMI #functionCallStatement
	| RETURN expression SEMI #returnStatement
	| IF L_PAREN expression R_PAREN L_CURLY block R_CURLY (ELSE IF L_PAREN expression R_PAREN L_CURLY block R_CURLY)* (ELSE L_CURLY block R_CURLY)? #ifStatement
	| FOR L_PAREN INTTYPE id EQUALS expression TO expression R_PAREN L_CURLY block R_CURLY #numericForStatement
	| FOR L_PAREN type id IN expression R_PAREN L_CURLY block R_CURLY #genericForStatement
	;

lvalue:
	id (PERIOD id | L_SQUARE integerExpression R_SQUARE)*;

methodSignature: type id L_PAREN paramList? R_PAREN;

paramList: variable (COMMA variable)*;

expression: expression EQUALSCOMPARE expression #equalsExp
	| expression NOTEQUALS expression #notEqualsExp
	| expression R_ANGLE expression # gtExp
	| expression L_ANGLE expression # ltExp
	| expression GEQ expression #geqExp
	| expression LEQ expression #leqExp
	| expression AND expression #andExp
	| expression SUBSETS expression #subsetsExp
	| expression IN expression #inExp
	| expression OR expression #orExp
	| expression UNION expression #unionExp
	| expression BACKSLASH expression #setMinusExp
	| expression PLUS expression #addExp
	| expression SUBTRACT expression #subtractExp
	| expression TIMES expression #multiplyExp
	| expression DIVIDE expression #divideExp

	| lvalue # lvalueExp
	| VBAR expression VBAR #sizeExp
	| expression L_PAREN argList? R_PAREN #fnCallExp
	| expression L_SQUARE integerExpression COLON integerExpression R_SQUARE #sliceExp
	| L_SQUARE (expression (COMMA expression)*)? R_SQUARE #createTupleExp
	| L_CURLY (expression (COMMA expression)*)? R_CURLY #createSetExp
	| type #typeExp
	| BINARYNUM #binaryNumExp
	| INT #intExp
	| NOT expression #notExp
	| L_PAREN expression R_PAREN #parenExp
	;

argList: expression (COMMA expression)*;

variable: type id;

type: type QUESTION #optionalType
	| set #setType
	| BOOL #boolType
	| MAP L_ANGLE type COMMA type R_ANGLE #mapType
	| ARRAY L_ANGLE type COMMA integerExpression R_ANGLE #arrayType
	| INTTYPE #intType
	| type (TIMES type)+ #productType
	| id (PERIOD id)* #userType
	| bitstring #bitStringType
	;

integerExpression: lvalue
	| BINARYNUM
	| INT
	| integerExpression PLUS integerExpression
	| integerExpression TIMES integerExpression
	| integerExpression SUBTRACT integerExpression
	| integerExpression DIVIDE integerExpression;

bitstring: BITSTRING | BITSTRING L_ANGLE integerExpression R_ANGLE;

set: SET L_ANGLE type R_ANGLE | SET;

moduleImport: IMPORT FILESTRING (AS ID)? SEMI;

methodBody: L_CURLY (statement)+ R_CURLY;

id: ID | IN;

L_CURLY: '{';
R_CURLY: '}';
L_SQUARE: '[';
R_SQUARE: ']';
L_PAREN: '(';
R_PAREN: ')';
L_ANGLE: '<';
R_ANGLE: '>';
SEMI: ';';
COLON: ':';
COMMA: ',';
PERIOD: '.';
TIMES: '*';
EQUALS: '=';
PLUS: '+';
SUBTRACT: '-';
DIVIDE: '/';
QUESTION: '?';
EQUALSCOMPARE: '==';
NOTEQUALS: '!=';
GEQ: '>=';
LEQ: '<=';
OR: '||';
SAMPLES: '<-';
AND: '&&';
BACKSLASH: '\\';
NOT: '!';
VBAR: '|';

SET: 'Set';
BOOL: 'Bool';
INTTYPE: 'Int';
MAP: 'Map';
RETURN: 'return';
IMPORT: 'import';
BITSTRING: 'BitString';
ARRAY: 'Array';
PRIMITIVE: 'Primitive';
SUBSETS: 'subsets';
IF: 'if';
FOR: 'for';
TO: 'to';
IN: 'in';
UNION: 'union';
GAME: 'Game';
EXPORT: 'export';
AS: 'as';
PHASE: 'Phase';
ORACLES: 'oracles';
ELSE: 'else';

BINARYNUM: '0b'[01]+ ;
INT: [0-9]+ ;
ID: [a-zA-Z_$][a-zA-Z_0-9$]* ;
WS: [ \t\r\n]+ -> skip ;
LINE_COMMENT : '//' .*? '\r'? '\n' -> skip ;
FILESTRING: '\''[0-9a-zA-Z_$/.=>< ]+'\'' ;
