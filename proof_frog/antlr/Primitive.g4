grammar Primitive;

import Shared;

program: PRIMITIVE ID L_PAREN paramList? R_PAREN L_CURLY primitiveBody R_CURLY EOF;

primitiveBody: ((initializedField|methodSignature) SEMI)+;