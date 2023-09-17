# Generated from proof_frog/antlr/Proof.g4 by ANTLR 4.13.1
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

def serializedATN():
    return [
        4,1,67,642,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,2,33,
        7,33,1,0,5,0,70,8,0,10,0,12,0,73,9,0,1,0,1,0,5,0,77,8,0,10,0,12,
        0,80,9,0,1,0,1,0,1,0,1,1,1,1,1,1,1,1,3,1,89,8,1,1,1,1,1,1,1,1,1,
        1,1,1,1,1,1,1,1,1,1,1,2,1,2,1,2,1,2,1,2,3,2,105,8,2,1,2,1,2,1,2,
        3,2,110,8,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,3,1,3,1,3,5,3,122,8,3,
        10,3,12,3,125,9,3,1,4,1,4,1,4,5,4,130,8,4,10,4,12,4,133,9,4,1,4,
        1,4,1,4,1,4,1,4,3,4,140,8,4,1,4,1,4,1,4,5,4,145,8,4,10,4,12,4,148,
        9,4,1,5,1,5,1,5,1,6,1,6,1,6,1,6,4,6,157,8,6,11,6,12,6,158,1,7,1,
        7,1,7,1,7,1,7,1,7,1,7,1,7,3,7,169,8,7,1,7,1,7,1,7,3,7,174,8,7,1,
        8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,4,8,188,8,8,11,8,12,
        8,189,1,8,1,8,1,9,1,9,1,9,3,9,197,8,9,1,9,1,9,1,10,1,10,1,10,1,10,
        1,11,1,11,1,11,1,11,1,12,1,12,1,12,1,12,3,12,213,8,12,1,12,1,12,
        1,12,1,12,1,12,1,13,1,13,1,13,5,13,223,8,13,10,13,12,13,226,9,13,
        1,13,4,13,229,8,13,11,13,12,13,230,1,13,1,13,1,13,5,13,236,8,13,
        10,13,12,13,239,9,13,1,13,5,13,242,8,13,10,13,12,13,245,9,13,1,13,
        4,13,248,8,13,11,13,12,13,249,3,13,252,8,13,1,14,1,14,1,14,4,14,
        257,8,14,11,14,12,14,258,1,14,1,14,1,14,1,14,1,14,1,14,5,14,267,
        8,14,10,14,12,14,270,9,14,1,14,1,14,1,14,1,14,1,15,1,15,1,15,1,15,
        1,15,1,15,1,15,1,15,1,15,1,15,1,16,1,16,1,16,3,16,289,8,16,1,17,
        1,17,1,17,1,17,1,18,1,18,1,18,1,19,5,19,299,8,19,10,19,12,19,302,
        9,19,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,
        1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,
        1,20,1,20,1,20,1,20,3,20,333,8,20,1,20,1,20,1,20,1,20,1,20,1,20,
        1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,
        1,20,1,20,1,20,1,20,5,20,358,8,20,10,20,12,20,361,9,20,1,20,1,20,
        1,20,1,20,1,20,3,20,368,8,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,
        1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,
        1,20,1,20,1,20,1,20,3,20,394,8,20,1,21,1,21,1,21,1,21,1,21,1,21,
        1,21,5,21,403,8,21,10,21,12,21,406,9,21,1,22,1,22,1,22,1,22,3,22,
        412,8,22,1,22,1,22,1,23,1,23,1,23,5,23,419,8,23,10,23,12,23,422,
        9,23,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,5,24,434,
        8,24,10,24,12,24,437,9,24,3,24,439,8,24,1,24,1,24,1,24,1,24,1,24,
        5,24,446,8,24,10,24,12,24,449,9,24,3,24,451,8,24,1,24,1,24,1,24,
        1,24,1,24,1,24,1,24,1,24,1,24,1,24,3,24,463,8,24,1,24,1,24,1,24,
        1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,
        1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,
        1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,
        1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,3,24,516,8,24,1,24,
        1,24,1,24,1,24,1,24,1,24,1,24,1,24,5,24,526,8,24,10,24,12,24,529,
        9,24,1,25,1,25,1,25,5,25,534,8,25,10,25,12,25,537,9,25,1,26,1,26,
        1,26,1,27,1,27,1,27,1,27,1,27,1,27,1,27,1,27,1,27,1,27,1,27,1,27,
        1,27,1,27,1,27,1,27,1,27,1,27,1,27,1,27,1,27,5,27,563,8,27,10,27,
        12,27,566,9,27,1,27,3,27,569,8,27,1,27,1,27,1,27,1,27,1,27,4,27,
        576,8,27,11,27,12,27,577,5,27,580,8,27,10,27,12,27,583,9,27,1,28,
        1,28,1,28,1,28,3,28,589,8,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,
        1,28,1,28,1,28,1,28,1,28,5,28,603,8,28,10,28,12,28,606,9,28,1,29,
        1,29,1,29,1,29,1,29,1,29,3,29,614,8,29,1,30,1,30,1,30,1,30,1,30,
        1,30,3,30,622,8,30,1,31,1,31,1,31,1,31,3,31,628,8,31,1,31,1,31,1,
        32,1,32,4,32,634,8,32,11,32,12,32,635,1,32,1,32,1,33,1,33,1,33,0,
        3,48,54,56,34,0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,
        38,40,42,44,46,48,50,52,54,56,58,60,62,64,66,0,2,2,0,19,19,34,34,
        2,0,54,54,64,64,702,0,71,1,0,0,0,2,84,1,0,0,0,4,99,1,0,0,0,6,123,
        1,0,0,0,8,131,1,0,0,0,10,149,1,0,0,0,12,156,1,0,0,0,14,173,1,0,0,
        0,16,175,1,0,0,0,18,193,1,0,0,0,20,200,1,0,0,0,22,204,1,0,0,0,24,
        208,1,0,0,0,26,251,1,0,0,0,28,253,1,0,0,0,30,275,1,0,0,0,32,285,
        1,0,0,0,34,290,1,0,0,0,36,294,1,0,0,0,38,300,1,0,0,0,40,393,1,0,
        0,0,42,395,1,0,0,0,44,407,1,0,0,0,46,415,1,0,0,0,48,462,1,0,0,0,
        50,530,1,0,0,0,52,538,1,0,0,0,54,568,1,0,0,0,56,588,1,0,0,0,58,613,
        1,0,0,0,60,621,1,0,0,0,62,623,1,0,0,0,64,631,1,0,0,0,66,639,1,0,
        0,0,68,70,3,62,31,0,69,68,1,0,0,0,70,73,1,0,0,0,71,69,1,0,0,0,71,
        72,1,0,0,0,72,78,1,0,0,0,73,71,1,0,0,0,74,77,3,2,1,0,75,77,3,24,
        12,0,76,74,1,0,0,0,76,75,1,0,0,0,77,80,1,0,0,0,78,76,1,0,0,0,78,
        79,1,0,0,0,79,81,1,0,0,0,80,78,1,0,0,0,81,82,3,4,2,0,82,83,5,0,0,
        1,83,1,1,0,0,0,84,85,5,1,0,0,85,86,5,64,0,0,86,88,5,17,0,0,87,89,
        3,46,23,0,88,87,1,0,0,0,88,89,1,0,0,0,89,90,1,0,0,0,90,91,5,18,0,
        0,91,92,5,4,0,0,92,93,3,18,9,0,93,94,5,2,0,0,94,95,3,20,10,0,95,
        96,5,13,0,0,96,97,3,26,13,0,97,98,5,14,0,0,98,3,1,0,0,0,99,100,5,
        5,0,0,100,104,5,22,0,0,101,102,5,9,0,0,102,103,5,22,0,0,103,105,
        3,6,3,0,104,101,1,0,0,0,104,105,1,0,0,0,105,109,1,0,0,0,106,107,
        5,6,0,0,107,108,5,22,0,0,108,110,3,8,4,0,109,106,1,0,0,0,109,110,
        1,0,0,0,110,111,1,0,0,0,111,112,5,7,0,0,112,113,5,22,0,0,113,114,
        3,10,5,0,114,115,5,8,0,0,115,116,5,22,0,0,116,117,3,12,6,0,117,5,
        1,0,0,0,118,119,3,32,16,0,119,120,5,21,0,0,120,122,1,0,0,0,121,118,
        1,0,0,0,122,125,1,0,0,0,123,121,1,0,0,0,123,124,1,0,0,0,124,7,1,
        0,0,0,125,123,1,0,0,0,126,127,3,18,9,0,127,128,5,21,0,0,128,130,
        1,0,0,0,129,126,1,0,0,0,130,133,1,0,0,0,131,129,1,0,0,0,131,132,
        1,0,0,0,132,139,1,0,0,0,133,131,1,0,0,0,134,135,5,10,0,0,135,136,
        7,0,0,0,136,137,3,48,24,0,137,138,5,21,0,0,138,140,1,0,0,0,139,134,
        1,0,0,0,139,140,1,0,0,0,140,146,1,0,0,0,141,142,3,18,9,0,142,143,
        5,21,0,0,143,145,1,0,0,0,144,141,1,0,0,0,145,148,1,0,0,0,146,144,
        1,0,0,0,146,147,1,0,0,0,147,9,1,0,0,0,148,146,1,0,0,0,149,150,3,
        18,9,0,150,151,5,21,0,0,151,11,1,0,0,0,152,153,3,14,7,0,153,154,
        5,21,0,0,154,157,1,0,0,0,155,157,3,16,8,0,156,152,1,0,0,0,156,155,
        1,0,0,0,157,158,1,0,0,0,158,156,1,0,0,0,158,159,1,0,0,0,159,13,1,
        0,0,0,160,161,3,22,11,0,161,162,5,4,0,0,162,163,3,18,9,0,163,164,
        5,2,0,0,164,165,3,20,10,0,165,174,1,0,0,0,166,169,3,22,11,0,167,
        169,3,18,9,0,168,166,1,0,0,0,168,167,1,0,0,0,169,170,1,0,0,0,170,
        171,5,2,0,0,171,172,3,20,10,0,172,174,1,0,0,0,173,160,1,0,0,0,173,
        168,1,0,0,0,174,15,1,0,0,0,175,176,5,11,0,0,176,177,5,17,0,0,177,
        178,5,64,0,0,178,179,5,12,0,0,179,180,3,48,24,0,180,181,5,53,0,0,
        181,182,3,48,24,0,182,183,5,18,0,0,183,187,5,13,0,0,184,185,3,14,
        7,0,185,186,5,21,0,0,186,188,1,0,0,0,187,184,1,0,0,0,188,189,1,0,
        0,0,189,187,1,0,0,0,189,190,1,0,0,0,190,191,1,0,0,0,191,192,5,14,
        0,0,192,17,1,0,0,0,193,194,5,64,0,0,194,196,5,17,0,0,195,197,3,50,
        25,0,196,195,1,0,0,0,196,197,1,0,0,0,197,198,1,0,0,0,198,199,5,18,
        0,0,199,19,1,0,0,0,200,201,3,18,9,0,201,202,5,24,0,0,202,203,5,3,
        0,0,203,21,1,0,0,0,204,205,3,18,9,0,205,206,5,24,0,0,206,207,5,64,
        0,0,207,23,1,0,0,0,208,209,5,56,0,0,209,210,5,64,0,0,210,212,5,17,
        0,0,211,213,3,46,23,0,212,211,1,0,0,0,212,213,1,0,0,0,213,214,1,
        0,0,0,214,215,5,18,0,0,215,216,5,13,0,0,216,217,3,26,13,0,217,218,
        5,14,0,0,218,25,1,0,0,0,219,220,3,32,16,0,220,221,5,21,0,0,221,223,
        1,0,0,0,222,219,1,0,0,0,223,226,1,0,0,0,224,222,1,0,0,0,224,225,
        1,0,0,0,225,228,1,0,0,0,226,224,1,0,0,0,227,229,3,36,18,0,228,227,
        1,0,0,0,229,230,1,0,0,0,230,228,1,0,0,0,230,231,1,0,0,0,231,252,
        1,0,0,0,232,233,3,32,16,0,233,234,5,21,0,0,234,236,1,0,0,0,235,232,
        1,0,0,0,236,239,1,0,0,0,237,235,1,0,0,0,237,238,1,0,0,0,238,243,
        1,0,0,0,239,237,1,0,0,0,240,242,3,36,18,0,241,240,1,0,0,0,242,245,
        1,0,0,0,243,241,1,0,0,0,243,244,1,0,0,0,244,247,1,0,0,0,245,243,
        1,0,0,0,246,248,3,28,14,0,247,246,1,0,0,0,248,249,1,0,0,0,249,247,
        1,0,0,0,249,250,1,0,0,0,250,252,1,0,0,0,251,224,1,0,0,0,251,237,
        1,0,0,0,252,27,1,0,0,0,253,254,5,59,0,0,254,256,5,13,0,0,255,257,
        3,36,18,0,256,255,1,0,0,0,257,258,1,0,0,0,258,256,1,0,0,0,258,259,
        1,0,0,0,259,260,1,0,0,0,260,261,5,60,0,0,261,262,5,22,0,0,262,263,
        5,15,0,0,263,268,3,66,33,0,264,265,5,23,0,0,265,267,3,66,33,0,266,
        264,1,0,0,0,267,270,1,0,0,0,268,266,1,0,0,0,268,269,1,0,0,0,269,
        271,1,0,0,0,270,268,1,0,0,0,271,272,5,16,0,0,272,273,5,21,0,0,273,
        274,5,14,0,0,274,29,1,0,0,0,275,276,5,57,0,0,276,277,5,17,0,0,277,
        278,5,64,0,0,278,279,5,23,0,0,279,280,5,64,0,0,280,281,5,18,0,0,
        281,282,5,58,0,0,282,283,5,64,0,0,283,284,5,21,0,0,284,31,1,0,0,
        0,285,288,3,52,26,0,286,287,5,26,0,0,287,289,3,48,24,0,288,286,1,
        0,0,0,288,289,1,0,0,0,289,33,1,0,0,0,290,291,3,52,26,0,291,292,5,
        26,0,0,292,293,3,48,24,0,293,35,1,0,0,0,294,295,3,44,22,0,295,296,
        3,64,32,0,296,37,1,0,0,0,297,299,3,40,20,0,298,297,1,0,0,0,299,302,
        1,0,0,0,300,298,1,0,0,0,300,301,1,0,0,0,301,39,1,0,0,0,302,300,1,
        0,0,0,303,304,3,54,27,0,304,305,3,66,33,0,305,306,5,21,0,0,306,394,
        1,0,0,0,307,308,3,54,27,0,308,309,3,42,21,0,309,310,5,26,0,0,310,
        311,3,48,24,0,311,312,5,21,0,0,312,394,1,0,0,0,313,314,3,54,27,0,
        314,315,3,42,21,0,315,316,5,36,0,0,316,317,3,48,24,0,317,318,5,21,
        0,0,318,394,1,0,0,0,319,320,3,42,21,0,320,321,5,26,0,0,321,322,3,
        48,24,0,322,323,5,21,0,0,323,394,1,0,0,0,324,325,3,42,21,0,325,326,
        5,36,0,0,326,327,3,48,24,0,327,328,5,21,0,0,328,394,1,0,0,0,329,
        330,3,48,24,0,330,332,5,17,0,0,331,333,3,50,25,0,332,331,1,0,0,0,
        332,333,1,0,0,0,333,334,1,0,0,0,334,335,5,18,0,0,335,336,5,21,0,
        0,336,394,1,0,0,0,337,338,5,45,0,0,338,339,3,48,24,0,339,340,5,21,
        0,0,340,394,1,0,0,0,341,342,5,51,0,0,342,343,5,17,0,0,343,344,3,
        48,24,0,344,345,5,18,0,0,345,346,5,13,0,0,346,347,3,38,19,0,347,
        359,5,14,0,0,348,349,5,61,0,0,349,350,5,51,0,0,350,351,5,17,0,0,
        351,352,3,48,24,0,352,353,5,18,0,0,353,354,5,13,0,0,354,355,3,38,
        19,0,355,356,5,14,0,0,356,358,1,0,0,0,357,348,1,0,0,0,358,361,1,
        0,0,0,359,357,1,0,0,0,359,360,1,0,0,0,360,367,1,0,0,0,361,359,1,
        0,0,0,362,363,5,61,0,0,363,364,5,13,0,0,364,365,3,38,19,0,365,366,
        5,14,0,0,366,368,1,0,0,0,367,362,1,0,0,0,367,368,1,0,0,0,368,394,
        1,0,0,0,369,370,5,52,0,0,370,371,5,17,0,0,371,372,5,43,0,0,372,373,
        3,66,33,0,373,374,5,26,0,0,374,375,3,48,24,0,375,376,5,53,0,0,376,
        377,3,48,24,0,377,378,5,18,0,0,378,379,5,13,0,0,379,380,3,38,19,
        0,380,381,5,14,0,0,381,394,1,0,0,0,382,383,5,52,0,0,383,384,5,17,
        0,0,384,385,3,54,27,0,385,386,3,66,33,0,386,387,5,54,0,0,387,388,
        3,48,24,0,388,389,5,18,0,0,389,390,5,13,0,0,390,391,3,38,19,0,391,
        392,5,14,0,0,392,394,1,0,0,0,393,303,1,0,0,0,393,307,1,0,0,0,393,
        313,1,0,0,0,393,319,1,0,0,0,393,324,1,0,0,0,393,329,1,0,0,0,393,
        337,1,0,0,0,393,341,1,0,0,0,393,369,1,0,0,0,393,382,1,0,0,0,394,
        41,1,0,0,0,395,404,3,66,33,0,396,397,5,24,0,0,397,403,3,66,33,0,
        398,399,5,15,0,0,399,400,3,56,28,0,400,401,5,16,0,0,401,403,1,0,
        0,0,402,396,1,0,0,0,402,398,1,0,0,0,403,406,1,0,0,0,404,402,1,0,
        0,0,404,405,1,0,0,0,405,43,1,0,0,0,406,404,1,0,0,0,407,408,3,54,
        27,0,408,409,3,66,33,0,409,411,5,17,0,0,410,412,3,46,23,0,411,410,
        1,0,0,0,411,412,1,0,0,0,412,413,1,0,0,0,413,414,5,18,0,0,414,45,
        1,0,0,0,415,420,3,52,26,0,416,417,5,23,0,0,417,419,3,52,26,0,418,
        416,1,0,0,0,419,422,1,0,0,0,420,418,1,0,0,0,420,421,1,0,0,0,421,
        47,1,0,0,0,422,420,1,0,0,0,423,424,6,24,-1,0,424,463,3,42,21,0,425,
        426,5,40,0,0,426,427,3,48,24,0,427,428,5,40,0,0,428,463,1,0,0,0,
        429,438,5,15,0,0,430,435,3,48,24,0,431,432,5,23,0,0,432,434,3,48,
        24,0,433,431,1,0,0,0,434,437,1,0,0,0,435,433,1,0,0,0,435,436,1,0,
        0,0,436,439,1,0,0,0,437,435,1,0,0,0,438,430,1,0,0,0,438,439,1,0,
        0,0,439,440,1,0,0,0,440,463,5,16,0,0,441,450,5,13,0,0,442,447,3,
        48,24,0,443,444,5,23,0,0,444,446,3,48,24,0,445,443,1,0,0,0,446,449,
        1,0,0,0,447,445,1,0,0,0,447,448,1,0,0,0,448,451,1,0,0,0,449,447,
        1,0,0,0,450,442,1,0,0,0,450,451,1,0,0,0,451,452,1,0,0,0,452,463,
        5,14,0,0,453,463,3,54,27,0,454,463,5,62,0,0,455,463,5,63,0,0,456,
        457,5,39,0,0,457,463,3,48,24,2,458,459,5,17,0,0,459,460,3,48,24,
        0,460,461,5,18,0,0,461,463,1,0,0,0,462,423,1,0,0,0,462,425,1,0,0,
        0,462,429,1,0,0,0,462,441,1,0,0,0,462,453,1,0,0,0,462,454,1,0,0,
        0,462,455,1,0,0,0,462,456,1,0,0,0,462,458,1,0,0,0,463,527,1,0,0,
        0,464,465,10,27,0,0,465,466,5,31,0,0,466,526,3,48,24,28,467,468,
        10,26,0,0,468,469,5,32,0,0,469,526,3,48,24,27,470,471,10,25,0,0,
        471,472,5,20,0,0,472,526,3,48,24,26,473,474,10,24,0,0,474,475,5,
        19,0,0,475,526,3,48,24,25,476,477,10,23,0,0,477,478,5,33,0,0,478,
        526,3,48,24,24,479,480,10,22,0,0,480,481,5,34,0,0,481,526,3,48,24,
        23,482,483,10,21,0,0,483,484,5,37,0,0,484,526,3,48,24,22,485,486,
        10,20,0,0,486,487,5,50,0,0,487,526,3,48,24,21,488,489,10,19,0,0,
        489,490,5,54,0,0,490,526,3,48,24,20,491,492,10,18,0,0,492,493,5,
        35,0,0,493,526,3,48,24,19,494,495,10,17,0,0,495,496,5,55,0,0,496,
        526,3,48,24,18,497,498,10,16,0,0,498,499,5,38,0,0,499,526,3,48,24,
        17,500,501,10,15,0,0,501,502,5,27,0,0,502,526,3,48,24,16,503,504,
        10,14,0,0,504,505,5,28,0,0,505,526,3,48,24,15,506,507,10,13,0,0,
        507,508,5,25,0,0,508,526,3,48,24,14,509,510,10,12,0,0,510,511,5,
        29,0,0,511,526,3,48,24,13,512,513,10,9,0,0,513,515,5,17,0,0,514,
        516,3,50,25,0,515,514,1,0,0,0,515,516,1,0,0,0,516,517,1,0,0,0,517,
        526,5,18,0,0,518,519,10,8,0,0,519,520,5,15,0,0,520,521,3,56,28,0,
        521,522,5,22,0,0,522,523,3,56,28,0,523,524,5,16,0,0,524,526,1,0,
        0,0,525,464,1,0,0,0,525,467,1,0,0,0,525,470,1,0,0,0,525,473,1,0,
        0,0,525,476,1,0,0,0,525,479,1,0,0,0,525,482,1,0,0,0,525,485,1,0,
        0,0,525,488,1,0,0,0,525,491,1,0,0,0,525,494,1,0,0,0,525,497,1,0,
        0,0,525,500,1,0,0,0,525,503,1,0,0,0,525,506,1,0,0,0,525,509,1,0,
        0,0,525,512,1,0,0,0,525,518,1,0,0,0,526,529,1,0,0,0,527,525,1,0,
        0,0,527,528,1,0,0,0,528,49,1,0,0,0,529,527,1,0,0,0,530,535,3,48,
        24,0,531,532,5,23,0,0,532,534,3,48,24,0,533,531,1,0,0,0,534,537,
        1,0,0,0,535,533,1,0,0,0,535,536,1,0,0,0,536,51,1,0,0,0,537,535,1,
        0,0,0,538,539,3,54,27,0,539,540,3,66,33,0,540,53,1,0,0,0,541,542,
        6,27,-1,0,542,569,3,60,30,0,543,569,5,42,0,0,544,545,5,44,0,0,545,
        546,5,19,0,0,546,547,3,54,27,0,547,548,5,23,0,0,548,549,3,54,27,
        0,549,550,5,20,0,0,550,569,1,0,0,0,551,552,5,48,0,0,552,553,5,19,
        0,0,553,554,3,54,27,0,554,555,5,23,0,0,555,556,3,56,28,0,556,557,
        5,20,0,0,557,569,1,0,0,0,558,569,5,43,0,0,559,564,3,66,33,0,560,
        561,5,24,0,0,561,563,3,66,33,0,562,560,1,0,0,0,563,566,1,0,0,0,564,
        562,1,0,0,0,564,565,1,0,0,0,565,569,1,0,0,0,566,564,1,0,0,0,567,
        569,3,58,29,0,568,541,1,0,0,0,568,543,1,0,0,0,568,544,1,0,0,0,568,
        551,1,0,0,0,568,558,1,0,0,0,568,559,1,0,0,0,568,567,1,0,0,0,569,
        581,1,0,0,0,570,571,10,9,0,0,571,580,5,30,0,0,572,575,10,3,0,0,573,
        574,5,25,0,0,574,576,3,54,27,0,575,573,1,0,0,0,576,577,1,0,0,0,577,
        575,1,0,0,0,577,578,1,0,0,0,578,580,1,0,0,0,579,570,1,0,0,0,579,
        572,1,0,0,0,580,583,1,0,0,0,581,579,1,0,0,0,581,582,1,0,0,0,582,
        55,1,0,0,0,583,581,1,0,0,0,584,585,6,28,-1,0,585,589,3,42,21,0,586,
        589,5,62,0,0,587,589,5,63,0,0,588,584,1,0,0,0,588,586,1,0,0,0,588,
        587,1,0,0,0,589,604,1,0,0,0,590,591,10,4,0,0,591,592,5,27,0,0,592,
        603,3,56,28,5,593,594,10,3,0,0,594,595,5,25,0,0,595,603,3,56,28,
        4,596,597,10,2,0,0,597,598,5,28,0,0,598,603,3,56,28,3,599,600,10,
        1,0,0,600,601,5,29,0,0,601,603,3,56,28,2,602,590,1,0,0,0,602,593,
        1,0,0,0,602,596,1,0,0,0,602,599,1,0,0,0,603,606,1,0,0,0,604,602,
        1,0,0,0,604,605,1,0,0,0,605,57,1,0,0,0,606,604,1,0,0,0,607,614,5,
        47,0,0,608,609,5,47,0,0,609,610,5,19,0,0,610,611,3,56,28,0,611,612,
        5,20,0,0,612,614,1,0,0,0,613,607,1,0,0,0,613,608,1,0,0,0,614,59,
        1,0,0,0,615,616,5,41,0,0,616,617,5,19,0,0,617,618,3,54,27,0,618,
        619,5,20,0,0,619,622,1,0,0,0,620,622,5,41,0,0,621,615,1,0,0,0,621,
        620,1,0,0,0,622,61,1,0,0,0,623,624,5,46,0,0,624,627,5,67,0,0,625,
        626,5,58,0,0,626,628,5,64,0,0,627,625,1,0,0,0,627,628,1,0,0,0,628,
        629,1,0,0,0,629,630,5,21,0,0,630,63,1,0,0,0,631,633,5,13,0,0,632,
        634,3,40,20,0,633,632,1,0,0,0,634,635,1,0,0,0,635,633,1,0,0,0,635,
        636,1,0,0,0,636,637,1,0,0,0,637,638,5,14,0,0,638,65,1,0,0,0,639,
        640,7,1,0,0,640,67,1,0,0,0,56,71,76,78,88,104,109,123,131,139,146,
        156,158,168,173,189,196,212,224,230,237,243,249,251,258,268,288,
        300,332,359,367,393,402,404,411,420,435,438,447,450,462,515,525,
        527,535,564,568,577,579,581,588,602,604,613,621,627,635
    ]

class ProofParser ( Parser ):

    grammarFileName = "Proof.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'Reduction'", "'against'", "'Adversary'", 
                     "'compose'", "'proof'", "'assume'", "'theorem'", "'games'", 
                     "'let'", "'calls'", "'induction'", "'from'", "'{'", 
                     "'}'", "'['", "']'", "'('", "')'", "'<'", "'>'", "';'", 
                     "':'", "','", "'.'", "'*'", "'='", "'+'", "'-'", "'/'", 
                     "'?'", "'=='", "'!='", "'>='", "'<='", "'||'", "'<-'", 
                     "'&&'", "'\\'", "'!'", "'|'", "'Set'", "'Bool'", "'Int'", 
                     "'Map'", "'return'", "'import'", "'BitString'", "'Array'", 
                     "'Primitive'", "'subsets'", "'if'", "'for'", "'to'", 
                     "'in'", "'union'", "'Game'", "'export'", "'as'", "'Phase'", 
                     "'oracles'", "'else'" ]

    symbolicNames = [ "<INVALID>", "REDUCTION", "AGAINST", "ADVERSARY", 
                      "COMPOSE", "PROOF", "ASSUME", "THEOREM", "GAMES", 
                      "LET", "CALLS", "INDUCTION", "FROM", "L_CURLY", "R_CURLY", 
                      "L_SQUARE", "R_SQUARE", "L_PAREN", "R_PAREN", "L_ANGLE", 
                      "R_ANGLE", "SEMI", "COLON", "COMMA", "PERIOD", "TIMES", 
                      "EQUALS", "PLUS", "SUBTRACT", "DIVIDE", "QUESTION", 
                      "EQUALSCOMPARE", "NOTEQUALS", "GEQ", "LEQ", "OR", 
                      "SAMPLES", "AND", "BACKSLASH", "NOT", "VBAR", "SET", 
                      "BOOL", "INTTYPE", "MAP", "RETURN", "IMPORT", "BITSTRING", 
                      "ARRAY", "PRIMITIVE", "SUBSETS", "IF", "FOR", "TO", 
                      "IN", "UNION", "GAME", "EXPORT", "AS", "PHASE", "ORACLES", 
                      "ELSE", "BINARYNUM", "INT", "ID", "WS", "LINE_COMMENT", 
                      "FILESTRING" ]

    RULE_program = 0
    RULE_reduction = 1
    RULE_proof = 2
    RULE_lets = 3
    RULE_assumptions = 4
    RULE_theorem = 5
    RULE_gameList = 6
    RULE_gameStep = 7
    RULE_induction = 8
    RULE_gameModule = 9
    RULE_gameAdversary = 10
    RULE_concreteGame = 11
    RULE_game = 12
    RULE_gameBody = 13
    RULE_gamePhase = 14
    RULE_gameExport = 15
    RULE_field = 16
    RULE_initializedField = 17
    RULE_method = 18
    RULE_block = 19
    RULE_statement = 20
    RULE_lvalue = 21
    RULE_methodSignature = 22
    RULE_paramList = 23
    RULE_expression = 24
    RULE_argList = 25
    RULE_variable = 26
    RULE_type = 27
    RULE_integerExpression = 28
    RULE_bitstring = 29
    RULE_set = 30
    RULE_moduleImport = 31
    RULE_methodBody = 32
    RULE_id = 33

    ruleNames =  [ "program", "reduction", "proof", "lets", "assumptions", 
                   "theorem", "gameList", "gameStep", "induction", "gameModule", 
                   "gameAdversary", "concreteGame", "game", "gameBody", 
                   "gamePhase", "gameExport", "field", "initializedField", 
                   "method", "block", "statement", "lvalue", "methodSignature", 
                   "paramList", "expression", "argList", "variable", "type", 
                   "integerExpression", "bitstring", "set", "moduleImport", 
                   "methodBody", "id" ]

    EOF = Token.EOF
    REDUCTION=1
    AGAINST=2
    ADVERSARY=3
    COMPOSE=4
    PROOF=5
    ASSUME=6
    THEOREM=7
    GAMES=8
    LET=9
    CALLS=10
    INDUCTION=11
    FROM=12
    L_CURLY=13
    R_CURLY=14
    L_SQUARE=15
    R_SQUARE=16
    L_PAREN=17
    R_PAREN=18
    L_ANGLE=19
    R_ANGLE=20
    SEMI=21
    COLON=22
    COMMA=23
    PERIOD=24
    TIMES=25
    EQUALS=26
    PLUS=27
    SUBTRACT=28
    DIVIDE=29
    QUESTION=30
    EQUALSCOMPARE=31
    NOTEQUALS=32
    GEQ=33
    LEQ=34
    OR=35
    SAMPLES=36
    AND=37
    BACKSLASH=38
    NOT=39
    VBAR=40
    SET=41
    BOOL=42
    INTTYPE=43
    MAP=44
    RETURN=45
    IMPORT=46
    BITSTRING=47
    ARRAY=48
    PRIMITIVE=49
    SUBSETS=50
    IF=51
    FOR=52
    TO=53
    IN=54
    UNION=55
    GAME=56
    EXPORT=57
    AS=58
    PHASE=59
    ORACLES=60
    ELSE=61
    BINARYNUM=62
    INT=63
    ID=64
    WS=65
    LINE_COMMENT=66
    FILESTRING=67

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.1")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class ProgramContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def proof(self):
            return self.getTypedRuleContext(ProofParser.ProofContext,0)


        def EOF(self):
            return self.getToken(ProofParser.EOF, 0)

        def moduleImport(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ModuleImportContext)
            else:
                return self.getTypedRuleContext(ProofParser.ModuleImportContext,i)


        def reduction(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ReductionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ReductionContext,i)


        def game(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.GameContext)
            else:
                return self.getTypedRuleContext(ProofParser.GameContext,i)


        def getRuleIndex(self):
            return ProofParser.RULE_program

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitProgram" ):
                return visitor.visitProgram(self)
            else:
                return visitor.visitChildren(self)




    def program(self):

        localctx = ProofParser.ProgramContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_program)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 71
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==46:
                self.state = 68
                self.moduleImport()
                self.state = 73
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 78
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==1 or _la==56:
                self.state = 76
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [1]:
                    self.state = 74
                    self.reduction()
                    pass
                elif token in [56]:
                    self.state = 75
                    self.game()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 80
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 81
            self.proof()
            self.state = 82
            self.match(ProofParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ReductionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def REDUCTION(self):
            return self.getToken(ProofParser.REDUCTION, 0)

        def ID(self):
            return self.getToken(ProofParser.ID, 0)

        def L_PAREN(self):
            return self.getToken(ProofParser.L_PAREN, 0)

        def R_PAREN(self):
            return self.getToken(ProofParser.R_PAREN, 0)

        def COMPOSE(self):
            return self.getToken(ProofParser.COMPOSE, 0)

        def gameModule(self):
            return self.getTypedRuleContext(ProofParser.GameModuleContext,0)


        def AGAINST(self):
            return self.getToken(ProofParser.AGAINST, 0)

        def gameAdversary(self):
            return self.getTypedRuleContext(ProofParser.GameAdversaryContext,0)


        def L_CURLY(self):
            return self.getToken(ProofParser.L_CURLY, 0)

        def gameBody(self):
            return self.getTypedRuleContext(ProofParser.GameBodyContext,0)


        def R_CURLY(self):
            return self.getToken(ProofParser.R_CURLY, 0)

        def paramList(self):
            return self.getTypedRuleContext(ProofParser.ParamListContext,0)


        def getRuleIndex(self):
            return ProofParser.RULE_reduction

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitReduction" ):
                return visitor.visitReduction(self)
            else:
                return visitor.visitChildren(self)




    def reduction(self):

        localctx = ProofParser.ReductionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_reduction)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 84
            self.match(ProofParser.REDUCTION)
            self.state = 85
            self.match(ProofParser.ID)
            self.state = 86
            self.match(ProofParser.L_PAREN)
            self.state = 88
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 41)) & ~0x3f) == 0 and ((1 << (_la - 41)) & 8397007) != 0):
                self.state = 87
                self.paramList()


            self.state = 90
            self.match(ProofParser.R_PAREN)
            self.state = 91
            self.match(ProofParser.COMPOSE)
            self.state = 92
            self.gameModule()
            self.state = 93
            self.match(ProofParser.AGAINST)
            self.state = 94
            self.gameAdversary()
            self.state = 95
            self.match(ProofParser.L_CURLY)
            self.state = 96
            self.gameBody()
            self.state = 97
            self.match(ProofParser.R_CURLY)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ProofContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def PROOF(self):
            return self.getToken(ProofParser.PROOF, 0)

        def COLON(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.COLON)
            else:
                return self.getToken(ProofParser.COLON, i)

        def THEOREM(self):
            return self.getToken(ProofParser.THEOREM, 0)

        def theorem(self):
            return self.getTypedRuleContext(ProofParser.TheoremContext,0)


        def GAMES(self):
            return self.getToken(ProofParser.GAMES, 0)

        def gameList(self):
            return self.getTypedRuleContext(ProofParser.GameListContext,0)


        def LET(self):
            return self.getToken(ProofParser.LET, 0)

        def lets(self):
            return self.getTypedRuleContext(ProofParser.LetsContext,0)


        def ASSUME(self):
            return self.getToken(ProofParser.ASSUME, 0)

        def assumptions(self):
            return self.getTypedRuleContext(ProofParser.AssumptionsContext,0)


        def getRuleIndex(self):
            return ProofParser.RULE_proof

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitProof" ):
                return visitor.visitProof(self)
            else:
                return visitor.visitChildren(self)




    def proof(self):

        localctx = ProofParser.ProofContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_proof)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 99
            self.match(ProofParser.PROOF)
            self.state = 100
            self.match(ProofParser.COLON)
            self.state = 104
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==9:
                self.state = 101
                self.match(ProofParser.LET)
                self.state = 102
                self.match(ProofParser.COLON)
                self.state = 103
                self.lets()


            self.state = 109
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==6:
                self.state = 106
                self.match(ProofParser.ASSUME)
                self.state = 107
                self.match(ProofParser.COLON)
                self.state = 108
                self.assumptions()


            self.state = 111
            self.match(ProofParser.THEOREM)
            self.state = 112
            self.match(ProofParser.COLON)
            self.state = 113
            self.theorem()
            self.state = 114
            self.match(ProofParser.GAMES)
            self.state = 115
            self.match(ProofParser.COLON)
            self.state = 116
            self.gameList()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LetsContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def field(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.FieldContext)
            else:
                return self.getTypedRuleContext(ProofParser.FieldContext,i)


        def SEMI(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.SEMI)
            else:
                return self.getToken(ProofParser.SEMI, i)

        def getRuleIndex(self):
            return ProofParser.RULE_lets

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLets" ):
                return visitor.visitLets(self)
            else:
                return visitor.visitChildren(self)




    def lets(self):

        localctx = ProofParser.LetsContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_lets)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 123
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while ((((_la - 41)) & ~0x3f) == 0 and ((1 << (_la - 41)) & 8397007) != 0):
                self.state = 118
                self.field()
                self.state = 119
                self.match(ProofParser.SEMI)
                self.state = 125
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AssumptionsContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def gameModule(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.GameModuleContext)
            else:
                return self.getTypedRuleContext(ProofParser.GameModuleContext,i)


        def SEMI(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.SEMI)
            else:
                return self.getToken(ProofParser.SEMI, i)

        def CALLS(self):
            return self.getToken(ProofParser.CALLS, 0)

        def expression(self):
            return self.getTypedRuleContext(ProofParser.ExpressionContext,0)


        def LEQ(self):
            return self.getToken(ProofParser.LEQ, 0)

        def L_ANGLE(self):
            return self.getToken(ProofParser.L_ANGLE, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_assumptions

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssumptions" ):
                return visitor.visitAssumptions(self)
            else:
                return visitor.visitChildren(self)




    def assumptions(self):

        localctx = ProofParser.AssumptionsContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_assumptions)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 131
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,7,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 126
                    self.gameModule()
                    self.state = 127
                    self.match(ProofParser.SEMI) 
                self.state = 133
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,7,self._ctx)

            self.state = 139
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==10:
                self.state = 134
                self.match(ProofParser.CALLS)
                self.state = 135
                _la = self._input.LA(1)
                if not(_la==19 or _la==34):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 136
                self.expression(0)
                self.state = 137
                self.match(ProofParser.SEMI)


            self.state = 146
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==64:
                self.state = 141
                self.gameModule()
                self.state = 142
                self.match(ProofParser.SEMI)
                self.state = 148
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TheoremContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def gameModule(self):
            return self.getTypedRuleContext(ProofParser.GameModuleContext,0)


        def SEMI(self):
            return self.getToken(ProofParser.SEMI, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_theorem

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTheorem" ):
                return visitor.visitTheorem(self)
            else:
                return visitor.visitChildren(self)




    def theorem(self):

        localctx = ProofParser.TheoremContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_theorem)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 149
            self.gameModule()
            self.state = 150
            self.match(ProofParser.SEMI)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class GameListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def gameStep(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.GameStepContext)
            else:
                return self.getTypedRuleContext(ProofParser.GameStepContext,i)


        def SEMI(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.SEMI)
            else:
                return self.getToken(ProofParser.SEMI, i)

        def induction(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.InductionContext)
            else:
                return self.getTypedRuleContext(ProofParser.InductionContext,i)


        def getRuleIndex(self):
            return ProofParser.RULE_gameList

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGameList" ):
                return visitor.visitGameList(self)
            else:
                return visitor.visitChildren(self)




    def gameList(self):

        localctx = ProofParser.GameListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_gameList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 156 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 156
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [64]:
                    self.state = 152
                    self.gameStep()
                    self.state = 153
                    self.match(ProofParser.SEMI)
                    pass
                elif token in [11]:
                    self.state = 155
                    self.induction()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 158 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==11 or _la==64):
                    break

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class GameStepContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def concreteGame(self):
            return self.getTypedRuleContext(ProofParser.ConcreteGameContext,0)


        def COMPOSE(self):
            return self.getToken(ProofParser.COMPOSE, 0)

        def gameModule(self):
            return self.getTypedRuleContext(ProofParser.GameModuleContext,0)


        def AGAINST(self):
            return self.getToken(ProofParser.AGAINST, 0)

        def gameAdversary(self):
            return self.getTypedRuleContext(ProofParser.GameAdversaryContext,0)


        def getRuleIndex(self):
            return ProofParser.RULE_gameStep

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGameStep" ):
                return visitor.visitGameStep(self)
            else:
                return visitor.visitChildren(self)




    def gameStep(self):

        localctx = ProofParser.GameStepContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_gameStep)
        try:
            self.state = 173
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,13,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 160
                self.concreteGame()
                self.state = 161
                self.match(ProofParser.COMPOSE)
                self.state = 162
                self.gameModule()
                self.state = 163
                self.match(ProofParser.AGAINST)
                self.state = 164
                self.gameAdversary()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 168
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input,12,self._ctx)
                if la_ == 1:
                    self.state = 166
                    self.concreteGame()
                    pass

                elif la_ == 2:
                    self.state = 167
                    self.gameModule()
                    pass


                self.state = 170
                self.match(ProofParser.AGAINST)
                self.state = 171
                self.gameAdversary()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class InductionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def INDUCTION(self):
            return self.getToken(ProofParser.INDUCTION, 0)

        def L_PAREN(self):
            return self.getToken(ProofParser.L_PAREN, 0)

        def ID(self):
            return self.getToken(ProofParser.ID, 0)

        def FROM(self):
            return self.getToken(ProofParser.FROM, 0)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)


        def TO(self):
            return self.getToken(ProofParser.TO, 0)

        def R_PAREN(self):
            return self.getToken(ProofParser.R_PAREN, 0)

        def L_CURLY(self):
            return self.getToken(ProofParser.L_CURLY, 0)

        def R_CURLY(self):
            return self.getToken(ProofParser.R_CURLY, 0)

        def gameStep(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.GameStepContext)
            else:
                return self.getTypedRuleContext(ProofParser.GameStepContext,i)


        def SEMI(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.SEMI)
            else:
                return self.getToken(ProofParser.SEMI, i)

        def getRuleIndex(self):
            return ProofParser.RULE_induction

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitInduction" ):
                return visitor.visitInduction(self)
            else:
                return visitor.visitChildren(self)




    def induction(self):

        localctx = ProofParser.InductionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_induction)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 175
            self.match(ProofParser.INDUCTION)
            self.state = 176
            self.match(ProofParser.L_PAREN)
            self.state = 177
            self.match(ProofParser.ID)
            self.state = 178
            self.match(ProofParser.FROM)
            self.state = 179
            self.expression(0)
            self.state = 180
            self.match(ProofParser.TO)
            self.state = 181
            self.expression(0)
            self.state = 182
            self.match(ProofParser.R_PAREN)
            self.state = 183
            self.match(ProofParser.L_CURLY)
            self.state = 187 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 184
                self.gameStep()
                self.state = 185
                self.match(ProofParser.SEMI)
                self.state = 189 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==64):
                    break

            self.state = 191
            self.match(ProofParser.R_CURLY)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class GameModuleContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(ProofParser.ID, 0)

        def L_PAREN(self):
            return self.getToken(ProofParser.L_PAREN, 0)

        def R_PAREN(self):
            return self.getToken(ProofParser.R_PAREN, 0)

        def argList(self):
            return self.getTypedRuleContext(ProofParser.ArgListContext,0)


        def getRuleIndex(self):
            return ProofParser.RULE_gameModule

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGameModule" ):
                return visitor.visitGameModule(self)
            else:
                return visitor.visitChildren(self)




    def gameModule(self):

        localctx = ProofParser.GameModuleContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_gameModule)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 193
            self.match(ProofParser.ID)
            self.state = 194
            self.match(ProofParser.L_PAREN)
            self.state = 196
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 13)) & ~0x3f) == 0 and ((1 << (_la - 13)) & 3942904464670741) != 0):
                self.state = 195
                self.argList()


            self.state = 198
            self.match(ProofParser.R_PAREN)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class GameAdversaryContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def gameModule(self):
            return self.getTypedRuleContext(ProofParser.GameModuleContext,0)


        def PERIOD(self):
            return self.getToken(ProofParser.PERIOD, 0)

        def ADVERSARY(self):
            return self.getToken(ProofParser.ADVERSARY, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_gameAdversary

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGameAdversary" ):
                return visitor.visitGameAdversary(self)
            else:
                return visitor.visitChildren(self)




    def gameAdversary(self):

        localctx = ProofParser.GameAdversaryContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_gameAdversary)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 200
            self.gameModule()
            self.state = 201
            self.match(ProofParser.PERIOD)
            self.state = 202
            self.match(ProofParser.ADVERSARY)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ConcreteGameContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def gameModule(self):
            return self.getTypedRuleContext(ProofParser.GameModuleContext,0)


        def PERIOD(self):
            return self.getToken(ProofParser.PERIOD, 0)

        def ID(self):
            return self.getToken(ProofParser.ID, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_concreteGame

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConcreteGame" ):
                return visitor.visitConcreteGame(self)
            else:
                return visitor.visitChildren(self)




    def concreteGame(self):

        localctx = ProofParser.ConcreteGameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_concreteGame)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 204
            self.gameModule()
            self.state = 205
            self.match(ProofParser.PERIOD)
            self.state = 206
            self.match(ProofParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class GameContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def GAME(self):
            return self.getToken(ProofParser.GAME, 0)

        def ID(self):
            return self.getToken(ProofParser.ID, 0)

        def L_PAREN(self):
            return self.getToken(ProofParser.L_PAREN, 0)

        def R_PAREN(self):
            return self.getToken(ProofParser.R_PAREN, 0)

        def L_CURLY(self):
            return self.getToken(ProofParser.L_CURLY, 0)

        def gameBody(self):
            return self.getTypedRuleContext(ProofParser.GameBodyContext,0)


        def R_CURLY(self):
            return self.getToken(ProofParser.R_CURLY, 0)

        def paramList(self):
            return self.getTypedRuleContext(ProofParser.ParamListContext,0)


        def getRuleIndex(self):
            return ProofParser.RULE_game

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGame" ):
                return visitor.visitGame(self)
            else:
                return visitor.visitChildren(self)




    def game(self):

        localctx = ProofParser.GameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_game)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 208
            self.match(ProofParser.GAME)
            self.state = 209
            self.match(ProofParser.ID)
            self.state = 210
            self.match(ProofParser.L_PAREN)
            self.state = 212
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 41)) & ~0x3f) == 0 and ((1 << (_la - 41)) & 8397007) != 0):
                self.state = 211
                self.paramList()


            self.state = 214
            self.match(ProofParser.R_PAREN)
            self.state = 215
            self.match(ProofParser.L_CURLY)
            self.state = 216
            self.gameBody()
            self.state = 217
            self.match(ProofParser.R_CURLY)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class GameBodyContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def field(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.FieldContext)
            else:
                return self.getTypedRuleContext(ProofParser.FieldContext,i)


        def SEMI(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.SEMI)
            else:
                return self.getToken(ProofParser.SEMI, i)

        def method(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.MethodContext)
            else:
                return self.getTypedRuleContext(ProofParser.MethodContext,i)


        def gamePhase(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.GamePhaseContext)
            else:
                return self.getTypedRuleContext(ProofParser.GamePhaseContext,i)


        def getRuleIndex(self):
            return ProofParser.RULE_gameBody

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGameBody" ):
                return visitor.visitGameBody(self)
            else:
                return visitor.visitChildren(self)




    def gameBody(self):

        localctx = ProofParser.GameBodyContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_gameBody)
        self._la = 0 # Token type
        try:
            self.state = 251
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,22,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 224
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,17,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 219
                        self.field()
                        self.state = 220
                        self.match(ProofParser.SEMI) 
                    self.state = 226
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,17,self._ctx)

                self.state = 228 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 227
                    self.method()
                    self.state = 230 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (((((_la - 41)) & ~0x3f) == 0 and ((1 << (_la - 41)) & 8397007) != 0)):
                        break

                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 237
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,19,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 232
                        self.field()
                        self.state = 233
                        self.match(ProofParser.SEMI) 
                    self.state = 239
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,19,self._ctx)

                self.state = 243
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while ((((_la - 41)) & ~0x3f) == 0 and ((1 << (_la - 41)) & 8397007) != 0):
                    self.state = 240
                    self.method()
                    self.state = 245
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 247 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 246
                    self.gamePhase()
                    self.state = 249 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==59):
                        break

                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class GamePhaseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def PHASE(self):
            return self.getToken(ProofParser.PHASE, 0)

        def L_CURLY(self):
            return self.getToken(ProofParser.L_CURLY, 0)

        def ORACLES(self):
            return self.getToken(ProofParser.ORACLES, 0)

        def COLON(self):
            return self.getToken(ProofParser.COLON, 0)

        def L_SQUARE(self):
            return self.getToken(ProofParser.L_SQUARE, 0)

        def id_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.IdContext)
            else:
                return self.getTypedRuleContext(ProofParser.IdContext,i)


        def R_SQUARE(self):
            return self.getToken(ProofParser.R_SQUARE, 0)

        def SEMI(self):
            return self.getToken(ProofParser.SEMI, 0)

        def R_CURLY(self):
            return self.getToken(ProofParser.R_CURLY, 0)

        def method(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.MethodContext)
            else:
                return self.getTypedRuleContext(ProofParser.MethodContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.COMMA)
            else:
                return self.getToken(ProofParser.COMMA, i)

        def getRuleIndex(self):
            return ProofParser.RULE_gamePhase

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGamePhase" ):
                return visitor.visitGamePhase(self)
            else:
                return visitor.visitChildren(self)




    def gamePhase(self):

        localctx = ProofParser.GamePhaseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_gamePhase)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 253
            self.match(ProofParser.PHASE)
            self.state = 254
            self.match(ProofParser.L_CURLY)
            self.state = 256 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 255
                self.method()
                self.state = 258 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (((((_la - 41)) & ~0x3f) == 0 and ((1 << (_la - 41)) & 8397007) != 0)):
                    break

            self.state = 260
            self.match(ProofParser.ORACLES)
            self.state = 261
            self.match(ProofParser.COLON)
            self.state = 262
            self.match(ProofParser.L_SQUARE)
            self.state = 263
            self.id_()
            self.state = 268
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==23:
                self.state = 264
                self.match(ProofParser.COMMA)
                self.state = 265
                self.id_()
                self.state = 270
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 271
            self.match(ProofParser.R_SQUARE)
            self.state = 272
            self.match(ProofParser.SEMI)
            self.state = 273
            self.match(ProofParser.R_CURLY)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class GameExportContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def EXPORT(self):
            return self.getToken(ProofParser.EXPORT, 0)

        def L_PAREN(self):
            return self.getToken(ProofParser.L_PAREN, 0)

        def ID(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.ID)
            else:
                return self.getToken(ProofParser.ID, i)

        def COMMA(self):
            return self.getToken(ProofParser.COMMA, 0)

        def R_PAREN(self):
            return self.getToken(ProofParser.R_PAREN, 0)

        def AS(self):
            return self.getToken(ProofParser.AS, 0)

        def SEMI(self):
            return self.getToken(ProofParser.SEMI, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_gameExport

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGameExport" ):
                return visitor.visitGameExport(self)
            else:
                return visitor.visitChildren(self)




    def gameExport(self):

        localctx = ProofParser.GameExportContext(self, self._ctx, self.state)
        self.enterRule(localctx, 30, self.RULE_gameExport)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 275
            self.match(ProofParser.EXPORT)
            self.state = 276
            self.match(ProofParser.L_PAREN)
            self.state = 277
            self.match(ProofParser.ID)
            self.state = 278
            self.match(ProofParser.COMMA)
            self.state = 279
            self.match(ProofParser.ID)
            self.state = 280
            self.match(ProofParser.R_PAREN)
            self.state = 281
            self.match(ProofParser.AS)
            self.state = 282
            self.match(ProofParser.ID)
            self.state = 283
            self.match(ProofParser.SEMI)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FieldContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def variable(self):
            return self.getTypedRuleContext(ProofParser.VariableContext,0)


        def EQUALS(self):
            return self.getToken(ProofParser.EQUALS, 0)

        def expression(self):
            return self.getTypedRuleContext(ProofParser.ExpressionContext,0)


        def getRuleIndex(self):
            return ProofParser.RULE_field

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitField" ):
                return visitor.visitField(self)
            else:
                return visitor.visitChildren(self)




    def field(self):

        localctx = ProofParser.FieldContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_field)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 285
            self.variable()
            self.state = 288
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==26:
                self.state = 286
                self.match(ProofParser.EQUALS)
                self.state = 287
                self.expression(0)


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class InitializedFieldContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def variable(self):
            return self.getTypedRuleContext(ProofParser.VariableContext,0)


        def EQUALS(self):
            return self.getToken(ProofParser.EQUALS, 0)

        def expression(self):
            return self.getTypedRuleContext(ProofParser.ExpressionContext,0)


        def getRuleIndex(self):
            return ProofParser.RULE_initializedField

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitInitializedField" ):
                return visitor.visitInitializedField(self)
            else:
                return visitor.visitChildren(self)




    def initializedField(self):

        localctx = ProofParser.InitializedFieldContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_initializedField)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 290
            self.variable()
            self.state = 291
            self.match(ProofParser.EQUALS)
            self.state = 292
            self.expression(0)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class MethodContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def methodSignature(self):
            return self.getTypedRuleContext(ProofParser.MethodSignatureContext,0)


        def methodBody(self):
            return self.getTypedRuleContext(ProofParser.MethodBodyContext,0)


        def getRuleIndex(self):
            return ProofParser.RULE_method

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMethod" ):
                return visitor.visitMethod(self)
            else:
                return visitor.visitChildren(self)




    def method(self):

        localctx = ProofParser.MethodContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_method)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 294
            self.methodSignature()
            self.state = 295
            self.methodBody()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class BlockContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def statement(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.StatementContext)
            else:
                return self.getTypedRuleContext(ProofParser.StatementContext,i)


        def getRuleIndex(self):
            return ProofParser.RULE_block

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBlock" ):
                return visitor.visitBlock(self)
            else:
                return visitor.visitChildren(self)




    def block(self):

        localctx = ProofParser.BlockContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_block)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 300
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while ((((_la - 13)) & ~0x3f) == 0 and ((1 << (_la - 13)) & 3943733393358869) != 0):
                self.state = 297
                self.statement()
                self.state = 302
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class StatementContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return ProofParser.RULE_statement

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)



    class VarDeclWithSampleStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(ProofParser.TypeContext,0)

        def lvalue(self):
            return self.getTypedRuleContext(ProofParser.LvalueContext,0)

        def SAMPLES(self):
            return self.getToken(ProofParser.SAMPLES, 0)
        def expression(self):
            return self.getTypedRuleContext(ProofParser.ExpressionContext,0)

        def SEMI(self):
            return self.getToken(ProofParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVarDeclWithSampleStatement" ):
                return visitor.visitVarDeclWithSampleStatement(self)
            else:
                return visitor.visitChildren(self)


    class VarDeclStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(ProofParser.TypeContext,0)

        def id_(self):
            return self.getTypedRuleContext(ProofParser.IdContext,0)

        def SEMI(self):
            return self.getToken(ProofParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVarDeclStatement" ):
                return visitor.visitVarDeclStatement(self)
            else:
                return visitor.visitChildren(self)


    class GenericForStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def FOR(self):
            return self.getToken(ProofParser.FOR, 0)
        def L_PAREN(self):
            return self.getToken(ProofParser.L_PAREN, 0)
        def type_(self):
            return self.getTypedRuleContext(ProofParser.TypeContext,0)

        def id_(self):
            return self.getTypedRuleContext(ProofParser.IdContext,0)

        def IN(self):
            return self.getToken(ProofParser.IN, 0)
        def expression(self):
            return self.getTypedRuleContext(ProofParser.ExpressionContext,0)

        def R_PAREN(self):
            return self.getToken(ProofParser.R_PAREN, 0)
        def L_CURLY(self):
            return self.getToken(ProofParser.L_CURLY, 0)
        def block(self):
            return self.getTypedRuleContext(ProofParser.BlockContext,0)

        def R_CURLY(self):
            return self.getToken(ProofParser.R_CURLY, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGenericForStatement" ):
                return visitor.visitGenericForStatement(self)
            else:
                return visitor.visitChildren(self)


    class VarDeclWithValueStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(ProofParser.TypeContext,0)

        def lvalue(self):
            return self.getTypedRuleContext(ProofParser.LvalueContext,0)

        def EQUALS(self):
            return self.getToken(ProofParser.EQUALS, 0)
        def expression(self):
            return self.getTypedRuleContext(ProofParser.ExpressionContext,0)

        def SEMI(self):
            return self.getToken(ProofParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVarDeclWithValueStatement" ):
                return visitor.visitVarDeclWithValueStatement(self)
            else:
                return visitor.visitChildren(self)


    class AssignmentStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def lvalue(self):
            return self.getTypedRuleContext(ProofParser.LvalueContext,0)

        def EQUALS(self):
            return self.getToken(ProofParser.EQUALS, 0)
        def expression(self):
            return self.getTypedRuleContext(ProofParser.ExpressionContext,0)

        def SEMI(self):
            return self.getToken(ProofParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssignmentStatement" ):
                return visitor.visitAssignmentStatement(self)
            else:
                return visitor.visitChildren(self)


    class NumericForStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def FOR(self):
            return self.getToken(ProofParser.FOR, 0)
        def L_PAREN(self):
            return self.getToken(ProofParser.L_PAREN, 0)
        def INTTYPE(self):
            return self.getToken(ProofParser.INTTYPE, 0)
        def id_(self):
            return self.getTypedRuleContext(ProofParser.IdContext,0)

        def EQUALS(self):
            return self.getToken(ProofParser.EQUALS, 0)
        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def TO(self):
            return self.getToken(ProofParser.TO, 0)
        def R_PAREN(self):
            return self.getToken(ProofParser.R_PAREN, 0)
        def L_CURLY(self):
            return self.getToken(ProofParser.L_CURLY, 0)
        def block(self):
            return self.getTypedRuleContext(ProofParser.BlockContext,0)

        def R_CURLY(self):
            return self.getToken(ProofParser.R_CURLY, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNumericForStatement" ):
                return visitor.visitNumericForStatement(self)
            else:
                return visitor.visitChildren(self)


    class FunctionCallStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self):
            return self.getTypedRuleContext(ProofParser.ExpressionContext,0)

        def L_PAREN(self):
            return self.getToken(ProofParser.L_PAREN, 0)
        def R_PAREN(self):
            return self.getToken(ProofParser.R_PAREN, 0)
        def SEMI(self):
            return self.getToken(ProofParser.SEMI, 0)
        def argList(self):
            return self.getTypedRuleContext(ProofParser.ArgListContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFunctionCallStatement" ):
                return visitor.visitFunctionCallStatement(self)
            else:
                return visitor.visitChildren(self)


    class ReturnStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def RETURN(self):
            return self.getToken(ProofParser.RETURN, 0)
        def expression(self):
            return self.getTypedRuleContext(ProofParser.ExpressionContext,0)

        def SEMI(self):
            return self.getToken(ProofParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitReturnStatement" ):
                return visitor.visitReturnStatement(self)
            else:
                return visitor.visitChildren(self)


    class IfStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def IF(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.IF)
            else:
                return self.getToken(ProofParser.IF, i)
        def L_PAREN(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.L_PAREN)
            else:
                return self.getToken(ProofParser.L_PAREN, i)
        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def R_PAREN(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.R_PAREN)
            else:
                return self.getToken(ProofParser.R_PAREN, i)
        def L_CURLY(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.L_CURLY)
            else:
                return self.getToken(ProofParser.L_CURLY, i)
        def block(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.BlockContext)
            else:
                return self.getTypedRuleContext(ProofParser.BlockContext,i)

        def R_CURLY(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.R_CURLY)
            else:
                return self.getToken(ProofParser.R_CURLY, i)
        def ELSE(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.ELSE)
            else:
                return self.getToken(ProofParser.ELSE, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIfStatement" ):
                return visitor.visitIfStatement(self)
            else:
                return visitor.visitChildren(self)


    class SampleStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def lvalue(self):
            return self.getTypedRuleContext(ProofParser.LvalueContext,0)

        def SAMPLES(self):
            return self.getToken(ProofParser.SAMPLES, 0)
        def expression(self):
            return self.getTypedRuleContext(ProofParser.ExpressionContext,0)

        def SEMI(self):
            return self.getToken(ProofParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSampleStatement" ):
                return visitor.visitSampleStatement(self)
            else:
                return visitor.visitChildren(self)



    def statement(self):

        localctx = ProofParser.StatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_statement)
        self._la = 0 # Token type
        try:
            self.state = 393
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,30,self._ctx)
            if la_ == 1:
                localctx = ProofParser.VarDeclStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 303
                self.type_(0)
                self.state = 304
                self.id_()
                self.state = 305
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 2:
                localctx = ProofParser.VarDeclWithValueStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 307
                self.type_(0)
                self.state = 308
                self.lvalue()
                self.state = 309
                self.match(ProofParser.EQUALS)
                self.state = 310
                self.expression(0)
                self.state = 311
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 3:
                localctx = ProofParser.VarDeclWithSampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 313
                self.type_(0)
                self.state = 314
                self.lvalue()
                self.state = 315
                self.match(ProofParser.SAMPLES)
                self.state = 316
                self.expression(0)
                self.state = 317
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 4:
                localctx = ProofParser.AssignmentStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 319
                self.lvalue()
                self.state = 320
                self.match(ProofParser.EQUALS)
                self.state = 321
                self.expression(0)
                self.state = 322
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 5:
                localctx = ProofParser.SampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 5)
                self.state = 324
                self.lvalue()
                self.state = 325
                self.match(ProofParser.SAMPLES)
                self.state = 326
                self.expression(0)
                self.state = 327
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 6:
                localctx = ProofParser.FunctionCallStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 6)
                self.state = 329
                self.expression(0)
                self.state = 330
                self.match(ProofParser.L_PAREN)
                self.state = 332
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if ((((_la - 13)) & ~0x3f) == 0 and ((1 << (_la - 13)) & 3942904464670741) != 0):
                    self.state = 331
                    self.argList()


                self.state = 334
                self.match(ProofParser.R_PAREN)
                self.state = 335
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 7:
                localctx = ProofParser.ReturnStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 7)
                self.state = 337
                self.match(ProofParser.RETURN)
                self.state = 338
                self.expression(0)
                self.state = 339
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 8:
                localctx = ProofParser.IfStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 8)
                self.state = 341
                self.match(ProofParser.IF)
                self.state = 342
                self.match(ProofParser.L_PAREN)
                self.state = 343
                self.expression(0)
                self.state = 344
                self.match(ProofParser.R_PAREN)
                self.state = 345
                self.match(ProofParser.L_CURLY)
                self.state = 346
                self.block()
                self.state = 347
                self.match(ProofParser.R_CURLY)
                self.state = 359
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,28,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 348
                        self.match(ProofParser.ELSE)
                        self.state = 349
                        self.match(ProofParser.IF)
                        self.state = 350
                        self.match(ProofParser.L_PAREN)
                        self.state = 351
                        self.expression(0)
                        self.state = 352
                        self.match(ProofParser.R_PAREN)
                        self.state = 353
                        self.match(ProofParser.L_CURLY)
                        self.state = 354
                        self.block()
                        self.state = 355
                        self.match(ProofParser.R_CURLY) 
                    self.state = 361
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,28,self._ctx)

                self.state = 367
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==61:
                    self.state = 362
                    self.match(ProofParser.ELSE)
                    self.state = 363
                    self.match(ProofParser.L_CURLY)
                    self.state = 364
                    self.block()
                    self.state = 365
                    self.match(ProofParser.R_CURLY)


                pass

            elif la_ == 9:
                localctx = ProofParser.NumericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 9)
                self.state = 369
                self.match(ProofParser.FOR)
                self.state = 370
                self.match(ProofParser.L_PAREN)
                self.state = 371
                self.match(ProofParser.INTTYPE)
                self.state = 372
                self.id_()
                self.state = 373
                self.match(ProofParser.EQUALS)
                self.state = 374
                self.expression(0)
                self.state = 375
                self.match(ProofParser.TO)
                self.state = 376
                self.expression(0)
                self.state = 377
                self.match(ProofParser.R_PAREN)
                self.state = 378
                self.match(ProofParser.L_CURLY)
                self.state = 379
                self.block()
                self.state = 380
                self.match(ProofParser.R_CURLY)
                pass

            elif la_ == 10:
                localctx = ProofParser.GenericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 10)
                self.state = 382
                self.match(ProofParser.FOR)
                self.state = 383
                self.match(ProofParser.L_PAREN)
                self.state = 384
                self.type_(0)
                self.state = 385
                self.id_()
                self.state = 386
                self.match(ProofParser.IN)
                self.state = 387
                self.expression(0)
                self.state = 388
                self.match(ProofParser.R_PAREN)
                self.state = 389
                self.match(ProofParser.L_CURLY)
                self.state = 390
                self.block()
                self.state = 391
                self.match(ProofParser.R_CURLY)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LvalueContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def id_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.IdContext)
            else:
                return self.getTypedRuleContext(ProofParser.IdContext,i)


        def PERIOD(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.PERIOD)
            else:
                return self.getToken(ProofParser.PERIOD, i)

        def L_SQUARE(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.L_SQUARE)
            else:
                return self.getToken(ProofParser.L_SQUARE, i)

        def integerExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.IntegerExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.IntegerExpressionContext,i)


        def R_SQUARE(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.R_SQUARE)
            else:
                return self.getToken(ProofParser.R_SQUARE, i)

        def getRuleIndex(self):
            return ProofParser.RULE_lvalue

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLvalue" ):
                return visitor.visitLvalue(self)
            else:
                return visitor.visitChildren(self)




    def lvalue(self):

        localctx = ProofParser.LvalueContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_lvalue)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 395
            self.id_()
            self.state = 404
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,32,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 402
                    self._errHandler.sync(self)
                    token = self._input.LA(1)
                    if token in [24]:
                        self.state = 396
                        self.match(ProofParser.PERIOD)
                        self.state = 397
                        self.id_()
                        pass
                    elif token in [15]:
                        self.state = 398
                        self.match(ProofParser.L_SQUARE)
                        self.state = 399
                        self.integerExpression(0)
                        self.state = 400
                        self.match(ProofParser.R_SQUARE)
                        pass
                    else:
                        raise NoViableAltException(self)
             
                self.state = 406
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,32,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class MethodSignatureContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def type_(self):
            return self.getTypedRuleContext(ProofParser.TypeContext,0)


        def id_(self):
            return self.getTypedRuleContext(ProofParser.IdContext,0)


        def L_PAREN(self):
            return self.getToken(ProofParser.L_PAREN, 0)

        def R_PAREN(self):
            return self.getToken(ProofParser.R_PAREN, 0)

        def paramList(self):
            return self.getTypedRuleContext(ProofParser.ParamListContext,0)


        def getRuleIndex(self):
            return ProofParser.RULE_methodSignature

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMethodSignature" ):
                return visitor.visitMethodSignature(self)
            else:
                return visitor.visitChildren(self)




    def methodSignature(self):

        localctx = ProofParser.MethodSignatureContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_methodSignature)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 407
            self.type_(0)
            self.state = 408
            self.id_()
            self.state = 409
            self.match(ProofParser.L_PAREN)
            self.state = 411
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 41)) & ~0x3f) == 0 and ((1 << (_la - 41)) & 8397007) != 0):
                self.state = 410
                self.paramList()


            self.state = 413
            self.match(ProofParser.R_PAREN)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ParamListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def variable(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.VariableContext)
            else:
                return self.getTypedRuleContext(ProofParser.VariableContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.COMMA)
            else:
                return self.getToken(ProofParser.COMMA, i)

        def getRuleIndex(self):
            return ProofParser.RULE_paramList

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitParamList" ):
                return visitor.visitParamList(self)
            else:
                return visitor.visitChildren(self)




    def paramList(self):

        localctx = ProofParser.ParamListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 46, self.RULE_paramList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 415
            self.variable()
            self.state = 420
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==23:
                self.state = 416
                self.match(ProofParser.COMMA)
                self.state = 417
                self.variable()
                self.state = 422
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return ProofParser.RULE_expression

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)


    class CreateSetExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def L_CURLY(self):
            return self.getToken(ProofParser.L_CURLY, 0)
        def R_CURLY(self):
            return self.getToken(ProofParser.R_CURLY, 0)
        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.COMMA)
            else:
                return self.getToken(ProofParser.COMMA, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCreateSetExp" ):
                return visitor.visitCreateSetExp(self)
            else:
                return visitor.visitChildren(self)


    class InExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def IN(self):
            return self.getToken(ProofParser.IN, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitInExp" ):
                return visitor.visitInExp(self)
            else:
                return visitor.visitChildren(self)


    class AndExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def AND(self):
            return self.getToken(ProofParser.AND, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAndExp" ):
                return visitor.visitAndExp(self)
            else:
                return visitor.visitChildren(self)


    class FnCallExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self):
            return self.getTypedRuleContext(ProofParser.ExpressionContext,0)

        def L_PAREN(self):
            return self.getToken(ProofParser.L_PAREN, 0)
        def R_PAREN(self):
            return self.getToken(ProofParser.R_PAREN, 0)
        def argList(self):
            return self.getTypedRuleContext(ProofParser.ArgListContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFnCallExp" ):
                return visitor.visitFnCallExp(self)
            else:
                return visitor.visitChildren(self)


    class LvalueExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def lvalue(self):
            return self.getTypedRuleContext(ProofParser.LvalueContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLvalueExp" ):
                return visitor.visitLvalueExp(self)
            else:
                return visitor.visitChildren(self)


    class NotEqualsExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def NOTEQUALS(self):
            return self.getToken(ProofParser.NOTEQUALS, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNotEqualsExp" ):
                return visitor.visitNotEqualsExp(self)
            else:
                return visitor.visitChildren(self)


    class AddExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def PLUS(self):
            return self.getToken(ProofParser.PLUS, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAddExp" ):
                return visitor.visitAddExp(self)
            else:
                return visitor.visitChildren(self)


    class GeqExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def GEQ(self):
            return self.getToken(ProofParser.GEQ, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGeqExp" ):
                return visitor.visitGeqExp(self)
            else:
                return visitor.visitChildren(self)


    class NotExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def NOT(self):
            return self.getToken(ProofParser.NOT, 0)
        def expression(self):
            return self.getTypedRuleContext(ProofParser.ExpressionContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNotExp" ):
                return visitor.visitNotExp(self)
            else:
                return visitor.visitChildren(self)


    class GtExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def R_ANGLE(self):
            return self.getToken(ProofParser.R_ANGLE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGtExp" ):
                return visitor.visitGtExp(self)
            else:
                return visitor.visitChildren(self)


    class LtExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def L_ANGLE(self):
            return self.getToken(ProofParser.L_ANGLE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLtExp" ):
                return visitor.visitLtExp(self)
            else:
                return visitor.visitChildren(self)


    class SubtractExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def SUBTRACT(self):
            return self.getToken(ProofParser.SUBTRACT, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSubtractExp" ):
                return visitor.visitSubtractExp(self)
            else:
                return visitor.visitChildren(self)


    class EqualsExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def EQUALSCOMPARE(self):
            return self.getToken(ProofParser.EQUALSCOMPARE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitEqualsExp" ):
                return visitor.visitEqualsExp(self)
            else:
                return visitor.visitChildren(self)


    class MultiplyExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def TIMES(self):
            return self.getToken(ProofParser.TIMES, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMultiplyExp" ):
                return visitor.visitMultiplyExp(self)
            else:
                return visitor.visitChildren(self)


    class SubsetsExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def SUBSETS(self):
            return self.getToken(ProofParser.SUBSETS, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSubsetsExp" ):
                return visitor.visitSubsetsExp(self)
            else:
                return visitor.visitChildren(self)


    class UnionExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def UNION(self):
            return self.getToken(ProofParser.UNION, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitUnionExp" ):
                return visitor.visitUnionExp(self)
            else:
                return visitor.visitChildren(self)


    class IntExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def INT(self):
            return self.getToken(ProofParser.INT, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIntExp" ):
                return visitor.visitIntExp(self)
            else:
                return visitor.visitChildren(self)


    class SizeExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def VBAR(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.VBAR)
            else:
                return self.getToken(ProofParser.VBAR, i)
        def expression(self):
            return self.getTypedRuleContext(ProofParser.ExpressionContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSizeExp" ):
                return visitor.visitSizeExp(self)
            else:
                return visitor.visitChildren(self)


    class TypeExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(ProofParser.TypeContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTypeExp" ):
                return visitor.visitTypeExp(self)
            else:
                return visitor.visitChildren(self)


    class LeqExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def LEQ(self):
            return self.getToken(ProofParser.LEQ, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLeqExp" ):
                return visitor.visitLeqExp(self)
            else:
                return visitor.visitChildren(self)


    class OrExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def OR(self):
            return self.getToken(ProofParser.OR, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOrExp" ):
                return visitor.visitOrExp(self)
            else:
                return visitor.visitChildren(self)


    class CreateTupleExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def L_SQUARE(self):
            return self.getToken(ProofParser.L_SQUARE, 0)
        def R_SQUARE(self):
            return self.getToken(ProofParser.R_SQUARE, 0)
        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.COMMA)
            else:
                return self.getToken(ProofParser.COMMA, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCreateTupleExp" ):
                return visitor.visitCreateTupleExp(self)
            else:
                return visitor.visitChildren(self)


    class SetMinusExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def BACKSLASH(self):
            return self.getToken(ProofParser.BACKSLASH, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSetMinusExp" ):
                return visitor.visitSetMinusExp(self)
            else:
                return visitor.visitChildren(self)


    class DivideExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def DIVIDE(self):
            return self.getToken(ProofParser.DIVIDE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDivideExp" ):
                return visitor.visitDivideExp(self)
            else:
                return visitor.visitChildren(self)


    class BinaryNumExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def BINARYNUM(self):
            return self.getToken(ProofParser.BINARYNUM, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBinaryNumExp" ):
                return visitor.visitBinaryNumExp(self)
            else:
                return visitor.visitChildren(self)


    class ParenExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def L_PAREN(self):
            return self.getToken(ProofParser.L_PAREN, 0)
        def expression(self):
            return self.getTypedRuleContext(ProofParser.ExpressionContext,0)

        def R_PAREN(self):
            return self.getToken(ProofParser.R_PAREN, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitParenExp" ):
                return visitor.visitParenExp(self)
            else:
                return visitor.visitChildren(self)


    class SliceExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self):
            return self.getTypedRuleContext(ProofParser.ExpressionContext,0)

        def L_SQUARE(self):
            return self.getToken(ProofParser.L_SQUARE, 0)
        def integerExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.IntegerExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.IntegerExpressionContext,i)

        def COLON(self):
            return self.getToken(ProofParser.COLON, 0)
        def R_SQUARE(self):
            return self.getToken(ProofParser.R_SQUARE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSliceExp" ):
                return visitor.visitSliceExp(self)
            else:
                return visitor.visitChildren(self)



    def expression(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = ProofParser.ExpressionContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 48
        self.enterRecursionRule(localctx, 48, self.RULE_expression, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 462
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,39,self._ctx)
            if la_ == 1:
                localctx = ProofParser.LvalueExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 424
                self.lvalue()
                pass

            elif la_ == 2:
                localctx = ProofParser.SizeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 425
                self.match(ProofParser.VBAR)
                self.state = 426
                self.expression(0)
                self.state = 427
                self.match(ProofParser.VBAR)
                pass

            elif la_ == 3:
                localctx = ProofParser.CreateTupleExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 429
                self.match(ProofParser.L_SQUARE)
                self.state = 438
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if ((((_la - 13)) & ~0x3f) == 0 and ((1 << (_la - 13)) & 3942904464670741) != 0):
                    self.state = 430
                    self.expression(0)
                    self.state = 435
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==23:
                        self.state = 431
                        self.match(ProofParser.COMMA)
                        self.state = 432
                        self.expression(0)
                        self.state = 437
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 440
                self.match(ProofParser.R_SQUARE)
                pass

            elif la_ == 4:
                localctx = ProofParser.CreateSetExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 441
                self.match(ProofParser.L_CURLY)
                self.state = 450
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if ((((_la - 13)) & ~0x3f) == 0 and ((1 << (_la - 13)) & 3942904464670741) != 0):
                    self.state = 442
                    self.expression(0)
                    self.state = 447
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==23:
                        self.state = 443
                        self.match(ProofParser.COMMA)
                        self.state = 444
                        self.expression(0)
                        self.state = 449
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 452
                self.match(ProofParser.R_CURLY)
                pass

            elif la_ == 5:
                localctx = ProofParser.TypeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 453
                self.type_(0)
                pass

            elif la_ == 6:
                localctx = ProofParser.BinaryNumExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 454
                self.match(ProofParser.BINARYNUM)
                pass

            elif la_ == 7:
                localctx = ProofParser.IntExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 455
                self.match(ProofParser.INT)
                pass

            elif la_ == 8:
                localctx = ProofParser.NotExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 456
                self.match(ProofParser.NOT)
                self.state = 457
                self.expression(2)
                pass

            elif la_ == 9:
                localctx = ProofParser.ParenExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 458
                self.match(ProofParser.L_PAREN)
                self.state = 459
                self.expression(0)
                self.state = 460
                self.match(ProofParser.R_PAREN)
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 527
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,42,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 525
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,41,self._ctx)
                    if la_ == 1:
                        localctx = ProofParser.EqualsExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 464
                        if not self.precpred(self._ctx, 27):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 27)")
                        self.state = 465
                        self.match(ProofParser.EQUALSCOMPARE)
                        self.state = 466
                        self.expression(28)
                        pass

                    elif la_ == 2:
                        localctx = ProofParser.NotEqualsExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 467
                        if not self.precpred(self._ctx, 26):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 26)")
                        self.state = 468
                        self.match(ProofParser.NOTEQUALS)
                        self.state = 469
                        self.expression(27)
                        pass

                    elif la_ == 3:
                        localctx = ProofParser.GtExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 470
                        if not self.precpred(self._ctx, 25):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 25)")
                        self.state = 471
                        self.match(ProofParser.R_ANGLE)
                        self.state = 472
                        self.expression(26)
                        pass

                    elif la_ == 4:
                        localctx = ProofParser.LtExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 473
                        if not self.precpred(self._ctx, 24):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 24)")
                        self.state = 474
                        self.match(ProofParser.L_ANGLE)
                        self.state = 475
                        self.expression(25)
                        pass

                    elif la_ == 5:
                        localctx = ProofParser.GeqExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 476
                        if not self.precpred(self._ctx, 23):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 23)")
                        self.state = 477
                        self.match(ProofParser.GEQ)
                        self.state = 478
                        self.expression(24)
                        pass

                    elif la_ == 6:
                        localctx = ProofParser.LeqExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 479
                        if not self.precpred(self._ctx, 22):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 22)")
                        self.state = 480
                        self.match(ProofParser.LEQ)
                        self.state = 481
                        self.expression(23)
                        pass

                    elif la_ == 7:
                        localctx = ProofParser.AndExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 482
                        if not self.precpred(self._ctx, 21):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 21)")
                        self.state = 483
                        self.match(ProofParser.AND)
                        self.state = 484
                        self.expression(22)
                        pass

                    elif la_ == 8:
                        localctx = ProofParser.SubsetsExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 485
                        if not self.precpred(self._ctx, 20):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 20)")
                        self.state = 486
                        self.match(ProofParser.SUBSETS)
                        self.state = 487
                        self.expression(21)
                        pass

                    elif la_ == 9:
                        localctx = ProofParser.InExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 488
                        if not self.precpred(self._ctx, 19):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 19)")
                        self.state = 489
                        self.match(ProofParser.IN)
                        self.state = 490
                        self.expression(20)
                        pass

                    elif la_ == 10:
                        localctx = ProofParser.OrExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 491
                        if not self.precpred(self._ctx, 18):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 18)")
                        self.state = 492
                        self.match(ProofParser.OR)
                        self.state = 493
                        self.expression(19)
                        pass

                    elif la_ == 11:
                        localctx = ProofParser.UnionExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 494
                        if not self.precpred(self._ctx, 17):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 17)")
                        self.state = 495
                        self.match(ProofParser.UNION)
                        self.state = 496
                        self.expression(18)
                        pass

                    elif la_ == 12:
                        localctx = ProofParser.SetMinusExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 497
                        if not self.precpred(self._ctx, 16):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 16)")
                        self.state = 498
                        self.match(ProofParser.BACKSLASH)
                        self.state = 499
                        self.expression(17)
                        pass

                    elif la_ == 13:
                        localctx = ProofParser.AddExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 500
                        if not self.precpred(self._ctx, 15):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 15)")
                        self.state = 501
                        self.match(ProofParser.PLUS)
                        self.state = 502
                        self.expression(16)
                        pass

                    elif la_ == 14:
                        localctx = ProofParser.SubtractExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 503
                        if not self.precpred(self._ctx, 14):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 14)")
                        self.state = 504
                        self.match(ProofParser.SUBTRACT)
                        self.state = 505
                        self.expression(15)
                        pass

                    elif la_ == 15:
                        localctx = ProofParser.MultiplyExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 506
                        if not self.precpred(self._ctx, 13):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 13)")
                        self.state = 507
                        self.match(ProofParser.TIMES)
                        self.state = 508
                        self.expression(14)
                        pass

                    elif la_ == 16:
                        localctx = ProofParser.DivideExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 509
                        if not self.precpred(self._ctx, 12):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 12)")
                        self.state = 510
                        self.match(ProofParser.DIVIDE)
                        self.state = 511
                        self.expression(13)
                        pass

                    elif la_ == 17:
                        localctx = ProofParser.FnCallExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 512
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 9)")
                        self.state = 513
                        self.match(ProofParser.L_PAREN)
                        self.state = 515
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)
                        if ((((_la - 13)) & ~0x3f) == 0 and ((1 << (_la - 13)) & 3942904464670741) != 0):
                            self.state = 514
                            self.argList()


                        self.state = 517
                        self.match(ProofParser.R_PAREN)
                        pass

                    elif la_ == 18:
                        localctx = ProofParser.SliceExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 518
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 8)")
                        self.state = 519
                        self.match(ProofParser.L_SQUARE)
                        self.state = 520
                        self.integerExpression(0)
                        self.state = 521
                        self.match(ProofParser.COLON)
                        self.state = 522
                        self.integerExpression(0)
                        self.state = 523
                        self.match(ProofParser.R_SQUARE)
                        pass

             
                self.state = 529
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,42,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class ArgListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.COMMA)
            else:
                return self.getToken(ProofParser.COMMA, i)

        def getRuleIndex(self):
            return ProofParser.RULE_argList

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitArgList" ):
                return visitor.visitArgList(self)
            else:
                return visitor.visitChildren(self)




    def argList(self):

        localctx = ProofParser.ArgListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_argList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 530
            self.expression(0)
            self.state = 535
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==23:
                self.state = 531
                self.match(ProofParser.COMMA)
                self.state = 532
                self.expression(0)
                self.state = 537
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class VariableContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def type_(self):
            return self.getTypedRuleContext(ProofParser.TypeContext,0)


        def id_(self):
            return self.getTypedRuleContext(ProofParser.IdContext,0)


        def getRuleIndex(self):
            return ProofParser.RULE_variable

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVariable" ):
                return visitor.visitVariable(self)
            else:
                return visitor.visitChildren(self)




    def variable(self):

        localctx = ProofParser.VariableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 52, self.RULE_variable)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 538
            self.type_(0)
            self.state = 539
            self.id_()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TypeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return ProofParser.RULE_type

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)


    class ArrayTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def ARRAY(self):
            return self.getToken(ProofParser.ARRAY, 0)
        def L_ANGLE(self):
            return self.getToken(ProofParser.L_ANGLE, 0)
        def type_(self):
            return self.getTypedRuleContext(ProofParser.TypeContext,0)

        def COMMA(self):
            return self.getToken(ProofParser.COMMA, 0)
        def integerExpression(self):
            return self.getTypedRuleContext(ProofParser.IntegerExpressionContext,0)

        def R_ANGLE(self):
            return self.getToken(ProofParser.R_ANGLE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitArrayType" ):
                return visitor.visitArrayType(self)
            else:
                return visitor.visitChildren(self)


    class IntTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def INTTYPE(self):
            return self.getToken(ProofParser.INTTYPE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIntType" ):
                return visitor.visitIntType(self)
            else:
                return visitor.visitChildren(self)


    class OptionalTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(ProofParser.TypeContext,0)

        def QUESTION(self):
            return self.getToken(ProofParser.QUESTION, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOptionalType" ):
                return visitor.visitOptionalType(self)
            else:
                return visitor.visitChildren(self)


    class MapTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def MAP(self):
            return self.getToken(ProofParser.MAP, 0)
        def L_ANGLE(self):
            return self.getToken(ProofParser.L_ANGLE, 0)
        def type_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.TypeContext)
            else:
                return self.getTypedRuleContext(ProofParser.TypeContext,i)

        def COMMA(self):
            return self.getToken(ProofParser.COMMA, 0)
        def R_ANGLE(self):
            return self.getToken(ProofParser.R_ANGLE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMapType" ):
                return visitor.visitMapType(self)
            else:
                return visitor.visitChildren(self)


    class UserTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def id_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.IdContext)
            else:
                return self.getTypedRuleContext(ProofParser.IdContext,i)

        def PERIOD(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.PERIOD)
            else:
                return self.getToken(ProofParser.PERIOD, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitUserType" ):
                return visitor.visitUserType(self)
            else:
                return visitor.visitChildren(self)


    class SetTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def set_(self):
            return self.getTypedRuleContext(ProofParser.SetContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSetType" ):
                return visitor.visitSetType(self)
            else:
                return visitor.visitChildren(self)


    class BitStringTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def bitstring(self):
            return self.getTypedRuleContext(ProofParser.BitstringContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBitStringType" ):
                return visitor.visitBitStringType(self)
            else:
                return visitor.visitChildren(self)


    class BoolTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def BOOL(self):
            return self.getToken(ProofParser.BOOL, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBoolType" ):
                return visitor.visitBoolType(self)
            else:
                return visitor.visitChildren(self)


    class ProductTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.TypeContext)
            else:
                return self.getTypedRuleContext(ProofParser.TypeContext,i)

        def TIMES(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.TIMES)
            else:
                return self.getToken(ProofParser.TIMES, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitProductType" ):
                return visitor.visitProductType(self)
            else:
                return visitor.visitChildren(self)



    def type_(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = ProofParser.TypeContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 54
        self.enterRecursionRule(localctx, 54, self.RULE_type, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 568
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [41]:
                localctx = ProofParser.SetTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 542
                self.set_()
                pass
            elif token in [42]:
                localctx = ProofParser.BoolTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 543
                self.match(ProofParser.BOOL)
                pass
            elif token in [44]:
                localctx = ProofParser.MapTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 544
                self.match(ProofParser.MAP)
                self.state = 545
                self.match(ProofParser.L_ANGLE)
                self.state = 546
                self.type_(0)
                self.state = 547
                self.match(ProofParser.COMMA)
                self.state = 548
                self.type_(0)
                self.state = 549
                self.match(ProofParser.R_ANGLE)
                pass
            elif token in [48]:
                localctx = ProofParser.ArrayTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 551
                self.match(ProofParser.ARRAY)
                self.state = 552
                self.match(ProofParser.L_ANGLE)
                self.state = 553
                self.type_(0)
                self.state = 554
                self.match(ProofParser.COMMA)
                self.state = 555
                self.integerExpression(0)
                self.state = 556
                self.match(ProofParser.R_ANGLE)
                pass
            elif token in [43]:
                localctx = ProofParser.IntTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 558
                self.match(ProofParser.INTTYPE)
                pass
            elif token in [54, 64]:
                localctx = ProofParser.UserTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 559
                self.id_()
                self.state = 564
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,44,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 560
                        self.match(ProofParser.PERIOD)
                        self.state = 561
                        self.id_() 
                    self.state = 566
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,44,self._ctx)

                pass
            elif token in [47]:
                localctx = ProofParser.BitStringTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 567
                self.bitstring()
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 581
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,48,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 579
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,47,self._ctx)
                    if la_ == 1:
                        localctx = ProofParser.OptionalTypeContext(self, ProofParser.TypeContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_type)
                        self.state = 570
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 9)")
                        self.state = 571
                        self.match(ProofParser.QUESTION)
                        pass

                    elif la_ == 2:
                        localctx = ProofParser.ProductTypeContext(self, ProofParser.TypeContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_type)
                        self.state = 572
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 3)")
                        self.state = 575 
                        self._errHandler.sync(self)
                        _alt = 1
                        while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                            if _alt == 1:
                                self.state = 573
                                self.match(ProofParser.TIMES)
                                self.state = 574
                                self.type_(0)

                            else:
                                raise NoViableAltException(self)
                            self.state = 577 
                            self._errHandler.sync(self)
                            _alt = self._interp.adaptivePredict(self._input,46,self._ctx)

                        pass

             
                self.state = 583
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,48,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class IntegerExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def lvalue(self):
            return self.getTypedRuleContext(ProofParser.LvalueContext,0)


        def BINARYNUM(self):
            return self.getToken(ProofParser.BINARYNUM, 0)

        def INT(self):
            return self.getToken(ProofParser.INT, 0)

        def integerExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.IntegerExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.IntegerExpressionContext,i)


        def PLUS(self):
            return self.getToken(ProofParser.PLUS, 0)

        def TIMES(self):
            return self.getToken(ProofParser.TIMES, 0)

        def SUBTRACT(self):
            return self.getToken(ProofParser.SUBTRACT, 0)

        def DIVIDE(self):
            return self.getToken(ProofParser.DIVIDE, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_integerExpression

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIntegerExpression" ):
                return visitor.visitIntegerExpression(self)
            else:
                return visitor.visitChildren(self)



    def integerExpression(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = ProofParser.IntegerExpressionContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 56
        self.enterRecursionRule(localctx, 56, self.RULE_integerExpression, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 588
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [54, 64]:
                self.state = 585
                self.lvalue()
                pass
            elif token in [62]:
                self.state = 586
                self.match(ProofParser.BINARYNUM)
                pass
            elif token in [63]:
                self.state = 587
                self.match(ProofParser.INT)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 604
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,51,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 602
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,50,self._ctx)
                    if la_ == 1:
                        localctx = ProofParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 590
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 4)")
                        self.state = 591
                        self.match(ProofParser.PLUS)
                        self.state = 592
                        self.integerExpression(5)
                        pass

                    elif la_ == 2:
                        localctx = ProofParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 593
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 3)")
                        self.state = 594
                        self.match(ProofParser.TIMES)
                        self.state = 595
                        self.integerExpression(4)
                        pass

                    elif la_ == 3:
                        localctx = ProofParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 596
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                        self.state = 597
                        self.match(ProofParser.SUBTRACT)
                        self.state = 598
                        self.integerExpression(3)
                        pass

                    elif la_ == 4:
                        localctx = ProofParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 599
                        if not self.precpred(self._ctx, 1):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 1)")
                        self.state = 600
                        self.match(ProofParser.DIVIDE)
                        self.state = 601
                        self.integerExpression(2)
                        pass

             
                self.state = 606
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,51,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class BitstringContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def BITSTRING(self):
            return self.getToken(ProofParser.BITSTRING, 0)

        def L_ANGLE(self):
            return self.getToken(ProofParser.L_ANGLE, 0)

        def integerExpression(self):
            return self.getTypedRuleContext(ProofParser.IntegerExpressionContext,0)


        def R_ANGLE(self):
            return self.getToken(ProofParser.R_ANGLE, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_bitstring

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBitstring" ):
                return visitor.visitBitstring(self)
            else:
                return visitor.visitChildren(self)




    def bitstring(self):

        localctx = ProofParser.BitstringContext(self, self._ctx, self.state)
        self.enterRule(localctx, 58, self.RULE_bitstring)
        try:
            self.state = 613
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,52,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 607
                self.match(ProofParser.BITSTRING)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 608
                self.match(ProofParser.BITSTRING)
                self.state = 609
                self.match(ProofParser.L_ANGLE)
                self.state = 610
                self.integerExpression(0)
                self.state = 611
                self.match(ProofParser.R_ANGLE)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SetContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def SET(self):
            return self.getToken(ProofParser.SET, 0)

        def L_ANGLE(self):
            return self.getToken(ProofParser.L_ANGLE, 0)

        def type_(self):
            return self.getTypedRuleContext(ProofParser.TypeContext,0)


        def R_ANGLE(self):
            return self.getToken(ProofParser.R_ANGLE, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_set

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSet" ):
                return visitor.visitSet(self)
            else:
                return visitor.visitChildren(self)




    def set_(self):

        localctx = ProofParser.SetContext(self, self._ctx, self.state)
        self.enterRule(localctx, 60, self.RULE_set)
        try:
            self.state = 621
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,53,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 615
                self.match(ProofParser.SET)
                self.state = 616
                self.match(ProofParser.L_ANGLE)
                self.state = 617
                self.type_(0)
                self.state = 618
                self.match(ProofParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 620
                self.match(ProofParser.SET)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ModuleImportContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IMPORT(self):
            return self.getToken(ProofParser.IMPORT, 0)

        def FILESTRING(self):
            return self.getToken(ProofParser.FILESTRING, 0)

        def SEMI(self):
            return self.getToken(ProofParser.SEMI, 0)

        def AS(self):
            return self.getToken(ProofParser.AS, 0)

        def ID(self):
            return self.getToken(ProofParser.ID, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_moduleImport

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitModuleImport" ):
                return visitor.visitModuleImport(self)
            else:
                return visitor.visitChildren(self)




    def moduleImport(self):

        localctx = ProofParser.ModuleImportContext(self, self._ctx, self.state)
        self.enterRule(localctx, 62, self.RULE_moduleImport)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 623
            self.match(ProofParser.IMPORT)
            self.state = 624
            self.match(ProofParser.FILESTRING)
            self.state = 627
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==58:
                self.state = 625
                self.match(ProofParser.AS)
                self.state = 626
                self.match(ProofParser.ID)


            self.state = 629
            self.match(ProofParser.SEMI)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class MethodBodyContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def L_CURLY(self):
            return self.getToken(ProofParser.L_CURLY, 0)

        def R_CURLY(self):
            return self.getToken(ProofParser.R_CURLY, 0)

        def statement(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.StatementContext)
            else:
                return self.getTypedRuleContext(ProofParser.StatementContext,i)


        def getRuleIndex(self):
            return ProofParser.RULE_methodBody

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMethodBody" ):
                return visitor.visitMethodBody(self)
            else:
                return visitor.visitChildren(self)




    def methodBody(self):

        localctx = ProofParser.MethodBodyContext(self, self._ctx, self.state)
        self.enterRule(localctx, 64, self.RULE_methodBody)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 631
            self.match(ProofParser.L_CURLY)
            self.state = 633 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 632
                self.statement()
                self.state = 635 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (((((_la - 13)) & ~0x3f) == 0 and ((1 << (_la - 13)) & 3943733393358869) != 0)):
                    break

            self.state = 637
            self.match(ProofParser.R_CURLY)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class IdContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(ProofParser.ID, 0)

        def IN(self):
            return self.getToken(ProofParser.IN, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_id

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitId" ):
                return visitor.visitId(self)
            else:
                return visitor.visitChildren(self)




    def id_(self):

        localctx = ProofParser.IdContext(self, self._ctx, self.state)
        self.enterRule(localctx, 66, self.RULE_id)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 639
            _la = self._input.LA(1)
            if not(_la==54 or _la==64):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx



    def sempred(self, localctx:RuleContext, ruleIndex:int, predIndex:int):
        if self._predicates == None:
            self._predicates = dict()
        self._predicates[24] = self.expression_sempred
        self._predicates[27] = self.type_sempred
        self._predicates[28] = self.integerExpression_sempred
        pred = self._predicates.get(ruleIndex, None)
        if pred is None:
            raise Exception("No predicate with index:" + str(ruleIndex))
        else:
            return pred(localctx, predIndex)

    def expression_sempred(self, localctx:ExpressionContext, predIndex:int):
            if predIndex == 0:
                return self.precpred(self._ctx, 27)
         

            if predIndex == 1:
                return self.precpred(self._ctx, 26)
         

            if predIndex == 2:
                return self.precpred(self._ctx, 25)
         

            if predIndex == 3:
                return self.precpred(self._ctx, 24)
         

            if predIndex == 4:
                return self.precpred(self._ctx, 23)
         

            if predIndex == 5:
                return self.precpred(self._ctx, 22)
         

            if predIndex == 6:
                return self.precpred(self._ctx, 21)
         

            if predIndex == 7:
                return self.precpred(self._ctx, 20)
         

            if predIndex == 8:
                return self.precpred(self._ctx, 19)
         

            if predIndex == 9:
                return self.precpred(self._ctx, 18)
         

            if predIndex == 10:
                return self.precpred(self._ctx, 17)
         

            if predIndex == 11:
                return self.precpred(self._ctx, 16)
         

            if predIndex == 12:
                return self.precpred(self._ctx, 15)
         

            if predIndex == 13:
                return self.precpred(self._ctx, 14)
         

            if predIndex == 14:
                return self.precpred(self._ctx, 13)
         

            if predIndex == 15:
                return self.precpred(self._ctx, 12)
         

            if predIndex == 16:
                return self.precpred(self._ctx, 9)
         

            if predIndex == 17:
                return self.precpred(self._ctx, 8)
         

    def type_sempred(self, localctx:TypeContext, predIndex:int):
            if predIndex == 18:
                return self.precpred(self._ctx, 9)
         

            if predIndex == 19:
                return self.precpred(self._ctx, 3)
         

    def integerExpression_sempred(self, localctx:IntegerExpressionContext, predIndex:int):
            if predIndex == 20:
                return self.precpred(self._ctx, 4)
         

            if predIndex == 21:
                return self.precpred(self._ctx, 3)
         

            if predIndex == 22:
                return self.precpred(self._ctx, 2)
         

            if predIndex == 23:
                return self.precpred(self._ctx, 1)
         




