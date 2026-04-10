grammar Shared;

game: GAME id L_PAREN paramList? R_PAREN L_CURLY gameBody R_CURLY;

gameBody: (field SEMI)* method+;

field: variable (EQUALS expression)?;

initializedField: variable EQUALS expression;

method: methodSignature block;

block: L_CURLY statement* R_CURLY;

statement: type id SEMI #varDeclStatement
	| type lvalue EQUALS expression SEMI #varDeclWithValueStatement
	| type lvalue SAMPLES expression SEMI #varDeclWithSampleStatement
	| lvalue EQUALS expression SEMI #assignmentStatement
	| lvalue SAMPLES expression SEMI #sampleStatement
	| type lvalue SAMPUNIQ L_SQUARE lvalue R_SQUARE type SEMI #uniqueSampleStatement
	| lvalue SAMPUNIQ L_SQUARE lvalue R_SQUARE type SEMI #uniqueSampleNoTypeStatement
	| expression L_PAREN argList? R_PAREN SEMI #functionCallStatement
	| RETURN expression SEMI #returnStatement
	| IF L_PAREN expression R_PAREN block (ELSE IF L_PAREN expression R_PAREN block )* (ELSE block )? #ifStatement
	| FOR L_PAREN INTTYPE id EQUALS expression TO expression R_PAREN block #numericForStatement
	| FOR L_PAREN type id IN expression R_PAREN block #genericForStatement
	;

lvalue:
	(id | parameterizedGame | THIS) (PERIOD id | L_SQUARE expression R_SQUARE)*;

methodModifier: DETERMINISTIC | INJECTIVE;

methodSignature: methodModifier* type id L_PAREN paramList? R_PAREN;

paramList: variable (COMMA variable)*;

expression:
	expression L_PAREN argList? R_PAREN #fnCallExp
	| expression L_SQUARE integerExpression COLON integerExpression R_SQUARE #sliceExp
	| NOT expression #notExp
	| VBAR expression VBAR #sizeExp

	| <assoc=right> expression CARET expression #exponentiationExp

	| expression TIMES expression #multiplyExp
	| expression DIVIDE expression #divideExp
	| SUBTRACT expression #minusExp
	| expression PLUS expression #addExp
	| expression SUBTRACT expression #subtractExp
	| expression EQUALSCOMPARE expression #equalsExp
	| expression NOTEQUALS expression #notEqualsExp
	| expression R_ANGLE expression # gtExp
	| expression L_ANGLE expression # ltExp
	| expression GEQ expression #geqExp
	| expression LEQ expression #leqExp
	| expression IN expression #inExp
	| expression SUBSETS expression #subsetsExp

	| expression AND expression #andExp
	| expression OR expression #orExp
	| expression UNION expression #unionExp
	| expression BACKSLASH expression #setMinusExp

	| lvalue # lvalueExp
	| L_SQUARE (expression (COMMA expression)*)? R_SQUARE #createTupleExp
	| L_CURLY (expression (COMMA expression)*)? R_CURLY #createSetExp
	| type #typeExp
	| ZEROS_CARET integerAtom #zerosExp
	| ONES_CARET integerAtom #onesExp
	| BINARYNUM #binaryNumExp
	| INT #intExp
	| bool #boolExp
	| NONE #noneExp
	| L_PAREN expression R_PAREN #parenExp
	;

argList: expression (COMMA expression)*;

variable: type id;

parameterizedGame: id L_PAREN argList? R_PAREN;

type: type QUESTION #optionalType
	| set #setType
	| BOOL #boolType
	| VOID #voidType
	| MAP L_ANGLE type COMMA type R_ANGLE #mapType
	| ARRAY L_ANGLE type COMMA integerExpression R_ANGLE #arrayType
	| FUNCTION L_ANGLE type COMMA type R_ANGLE #functionType
	| INTTYPE #intType
	| L_SQUARE type (COMMA type)+ R_SQUARE #productType
	| bitstring #bitStringType
	| modint #modIntType
	| groupelem #groupElemType
	| GROUP #groupType
	| lvalue # lvalueType
	;

integerExpression
	: integerExpression TIMES integerExpression
	| integerExpression DIVIDE integerExpression
	| integerExpression PLUS integerExpression
	| integerExpression SUBTRACT integerExpression
	| lvalue
	| INT
	| BINARYNUM
	| L_PAREN integerExpression R_PAREN
	;

integerAtom
	: lvalue
	| INT
	| L_PAREN integerExpression R_PAREN
	;

bitstring: BITSTRING L_ANGLE integerExpression R_ANGLE | BITSTRING;

modint: MODINT L_ANGLE integerExpression R_ANGLE;

groupelem: GROUPELEM L_ANGLE lvalue R_ANGLE;

set: SET L_ANGLE type R_ANGLE | SET;

bool: TRUE | FALSE;

moduleImport: IMPORT FILESTRING (AS ID)? SEMI;

id: ID | IN | GROUP | GROUPELEM;

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
SAMPUNIQ: '<-uniq';
SAMPLES: '<-';
AND: '&&';
BACKSLASH: '\\';
NOT: '!';
CARET: '^';
VBAR: '|';

SET: 'Set';
BOOL: 'Bool';
VOID: 'Void';
INTTYPE: 'Int';
VOID: 'Void';
MAP: 'Map';
RETURN: 'return';
IMPORT: 'import';
BITSTRING: 'BitString';
MODINT: 'ModInt';
GROUP: 'Group';
GROUPELEM: 'GroupElem';
ARRAY: 'Array';
FUNCTION: 'Function';
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
ELSE: 'else';
NONE: 'None';
THIS: 'this';
DETERMINISTIC: 'deterministic';
INJECTIVE: 'injective';

TRUE: 'true';
FALSE: 'false';

BINARYNUM: '0b'[01]+ ;
ZEROS_CARET: '0^' ;
ONES_CARET: '1^' ;
INT: [0-9]+ ;
ID: [a-zA-Z_$][a-zA-Z_0-9$]* ;
WS: [ \t\r\n]+ -> skip ;
LINE_COMMENT : '//' .*? ('\r'? '\n' | EOF) -> skip ;
BLOCK_COMMENT : '/*' .*? '*/' -> skip ;
FILESTRING: '\''[-0-9a-zA-Z_$/.=>< ]+'\'' ;
