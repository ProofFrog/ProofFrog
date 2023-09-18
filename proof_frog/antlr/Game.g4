grammar Game;

import Shared;

program: moduleImport* game game gameExport EOF;

gameExport: EXPORT AS ID SEMI;
