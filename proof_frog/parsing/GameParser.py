# Generated from proof_frog/antlr/Game.g4 by ANTLR 4.13.2
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
        4,1,68,549,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        1,0,5,0,56,8,0,10,0,12,0,59,9,0,1,0,1,0,1,0,1,0,1,0,1,1,1,1,1,1,
        1,1,1,1,1,2,1,2,1,2,1,2,3,2,75,8,2,1,2,1,2,1,2,1,2,1,2,1,3,1,3,1,
        3,5,3,85,8,3,10,3,12,3,88,9,3,1,3,4,3,91,8,3,11,3,12,3,92,1,3,1,
        3,1,3,5,3,98,8,3,10,3,12,3,101,9,3,1,3,5,3,104,8,3,10,3,12,3,107,
        9,3,1,3,4,3,110,8,3,11,3,12,3,111,3,3,114,8,3,1,4,1,4,1,4,4,4,119,
        8,4,11,4,12,4,120,1,4,1,4,1,4,1,4,1,4,1,4,5,4,129,8,4,10,4,12,4,
        132,9,4,1,4,1,4,1,4,1,4,1,5,1,5,1,5,3,5,141,8,5,1,6,1,6,1,6,1,6,
        1,7,1,7,1,7,1,8,1,8,5,8,152,8,8,10,8,12,8,155,9,8,1,8,1,8,1,9,1,
        9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,
        9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,
        9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,3,9,205,8,9,1,
        9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,
        9,1,9,1,9,5,9,226,8,9,10,9,12,9,229,9,9,1,9,1,9,3,9,233,8,9,1,9,
        1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,
        1,9,1,9,1,9,3,9,255,8,9,1,10,1,10,1,10,3,10,260,8,10,1,10,1,10,1,
        10,1,10,1,10,1,10,5,10,268,8,10,10,10,12,10,271,9,10,1,11,1,11,1,
        12,5,12,276,8,12,10,12,12,12,279,9,12,1,12,1,12,1,12,1,12,3,12,285,
        8,12,1,12,1,12,1,13,1,13,1,13,5,13,292,8,13,10,13,12,13,295,9,13,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,5,14,311,8,14,10,14,12,14,314,9,14,3,14,316,8,14,1,14,1,14,
        1,14,1,14,1,14,5,14,323,8,14,10,14,12,14,326,9,14,3,14,328,8,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,3,14,344,8,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,3,14,400,8,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,5,14,410,8,14,10,14,12,14,413,9,14,1,15,1,15,
        1,15,5,15,418,8,15,10,15,12,15,421,9,15,1,16,1,16,1,16,1,17,1,17,
        1,17,3,17,429,8,17,1,17,1,17,1,18,1,18,1,18,1,18,1,18,1,18,1,18,
        1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,
        1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,4,18,463,8,18,
        11,18,12,18,464,1,18,1,18,1,18,1,18,1,18,3,18,472,8,18,1,18,1,18,
        5,18,476,8,18,10,18,12,18,479,9,18,1,19,1,19,1,19,1,19,1,19,1,19,
        1,19,1,19,3,19,489,8,19,1,19,1,19,1,19,1,19,1,19,1,19,1,19,1,19,
        1,19,1,19,1,19,1,19,5,19,503,8,19,10,19,12,19,506,9,19,1,20,1,20,
        1,20,1,20,1,20,1,20,3,20,514,8,20,1,21,1,21,1,21,1,21,1,21,1,21,
        3,21,522,8,21,1,22,1,22,1,22,1,22,1,22,1,23,1,23,1,23,1,23,1,23,
        1,23,3,23,535,8,23,1,24,1,24,1,25,1,25,1,25,1,25,3,25,543,8,25,1,
        25,1,25,1,26,1,26,1,26,0,3,28,36,38,27,0,2,4,6,8,10,12,14,16,18,
        20,22,24,26,28,30,32,34,36,38,40,42,44,46,48,50,52,0,3,1,0,57,58,
        1,0,59,60,2,0,47,47,65,65,617,0,57,1,0,0,0,2,65,1,0,0,0,4,70,1,0,
        0,0,6,113,1,0,0,0,8,115,1,0,0,0,10,137,1,0,0,0,12,142,1,0,0,0,14,
        146,1,0,0,0,16,149,1,0,0,0,18,254,1,0,0,0,20,259,1,0,0,0,22,272,
        1,0,0,0,24,277,1,0,0,0,26,288,1,0,0,0,28,343,1,0,0,0,30,414,1,0,
        0,0,32,422,1,0,0,0,34,425,1,0,0,0,36,471,1,0,0,0,38,488,1,0,0,0,
        40,513,1,0,0,0,42,521,1,0,0,0,44,523,1,0,0,0,46,534,1,0,0,0,48,536,
        1,0,0,0,50,538,1,0,0,0,52,546,1,0,0,0,54,56,3,50,25,0,55,54,1,0,
        0,0,56,59,1,0,0,0,57,55,1,0,0,0,57,58,1,0,0,0,58,60,1,0,0,0,59,57,
        1,0,0,0,60,61,3,4,2,0,61,62,3,4,2,0,62,63,3,2,1,0,63,64,5,0,0,1,
        64,1,1,0,0,0,65,66,5,50,0,0,66,67,5,51,0,0,67,68,5,65,0,0,68,69,
        5,9,0,0,69,3,1,0,0,0,70,71,5,49,0,0,71,72,5,65,0,0,72,74,5,5,0,0,
        73,75,3,26,13,0,74,73,1,0,0,0,74,75,1,0,0,0,75,76,1,0,0,0,76,77,
        5,6,0,0,77,78,5,1,0,0,78,79,3,6,3,0,79,80,5,2,0,0,80,5,1,0,0,0,81,
        82,3,10,5,0,82,83,5,9,0,0,83,85,1,0,0,0,84,81,1,0,0,0,85,88,1,0,
        0,0,86,84,1,0,0,0,86,87,1,0,0,0,87,90,1,0,0,0,88,86,1,0,0,0,89,91,
        3,14,7,0,90,89,1,0,0,0,91,92,1,0,0,0,92,90,1,0,0,0,92,93,1,0,0,0,
        93,114,1,0,0,0,94,95,3,10,5,0,95,96,5,9,0,0,96,98,1,0,0,0,97,94,
        1,0,0,0,98,101,1,0,0,0,99,97,1,0,0,0,99,100,1,0,0,0,100,105,1,0,
        0,0,101,99,1,0,0,0,102,104,3,14,7,0,103,102,1,0,0,0,104,107,1,0,
        0,0,105,103,1,0,0,0,105,106,1,0,0,0,106,109,1,0,0,0,107,105,1,0,
        0,0,108,110,3,8,4,0,109,108,1,0,0,0,110,111,1,0,0,0,111,109,1,0,
        0,0,111,112,1,0,0,0,112,114,1,0,0,0,113,86,1,0,0,0,113,99,1,0,0,
        0,114,7,1,0,0,0,115,116,5,52,0,0,116,118,5,1,0,0,117,119,3,14,7,
        0,118,117,1,0,0,0,119,120,1,0,0,0,120,118,1,0,0,0,120,121,1,0,0,
        0,121,122,1,0,0,0,122,123,5,53,0,0,123,124,5,10,0,0,124,125,5,3,
        0,0,125,130,3,52,26,0,126,127,5,11,0,0,127,129,3,52,26,0,128,126,
        1,0,0,0,129,132,1,0,0,0,130,128,1,0,0,0,130,131,1,0,0,0,131,133,
        1,0,0,0,132,130,1,0,0,0,133,134,5,4,0,0,134,135,5,9,0,0,135,136,
        5,2,0,0,136,9,1,0,0,0,137,140,3,32,16,0,138,139,5,14,0,0,139,141,
        3,28,14,0,140,138,1,0,0,0,140,141,1,0,0,0,141,11,1,0,0,0,142,143,
        3,32,16,0,143,144,5,14,0,0,144,145,3,28,14,0,145,13,1,0,0,0,146,
        147,3,24,12,0,147,148,3,16,8,0,148,15,1,0,0,0,149,153,5,1,0,0,150,
        152,3,18,9,0,151,150,1,0,0,0,152,155,1,0,0,0,153,151,1,0,0,0,153,
        154,1,0,0,0,154,156,1,0,0,0,155,153,1,0,0,0,156,157,5,2,0,0,157,
        17,1,0,0,0,158,159,3,36,18,0,159,160,3,52,26,0,160,161,5,9,0,0,161,
        255,1,0,0,0,162,163,3,36,18,0,163,164,3,20,10,0,164,165,5,14,0,0,
        165,166,3,28,14,0,166,167,5,9,0,0,167,255,1,0,0,0,168,169,3,36,18,
        0,169,170,3,20,10,0,170,171,5,25,0,0,171,172,3,28,14,0,172,173,5,
        9,0,0,173,255,1,0,0,0,174,175,3,20,10,0,175,176,5,14,0,0,176,177,
        3,28,14,0,177,178,5,9,0,0,178,255,1,0,0,0,179,180,3,20,10,0,180,
        181,5,25,0,0,181,182,3,28,14,0,182,183,5,9,0,0,183,255,1,0,0,0,184,
        185,3,36,18,0,185,186,3,20,10,0,186,187,5,24,0,0,187,188,5,3,0,0,
        188,189,3,20,10,0,189,190,5,4,0,0,190,191,3,36,18,0,191,192,5,9,
        0,0,192,255,1,0,0,0,193,194,3,20,10,0,194,195,5,24,0,0,195,196,5,
        3,0,0,196,197,3,20,10,0,197,198,5,4,0,0,198,199,3,36,18,0,199,200,
        5,9,0,0,200,255,1,0,0,0,201,202,3,28,14,0,202,204,5,5,0,0,203,205,
        3,30,15,0,204,203,1,0,0,0,204,205,1,0,0,0,205,206,1,0,0,0,206,207,
        5,6,0,0,207,208,5,9,0,0,208,255,1,0,0,0,209,210,5,36,0,0,210,211,
        3,28,14,0,211,212,5,9,0,0,212,255,1,0,0,0,213,214,5,44,0,0,214,215,
        5,5,0,0,215,216,3,28,14,0,216,217,5,6,0,0,217,227,3,16,8,0,218,219,
        5,54,0,0,219,220,5,44,0,0,220,221,5,5,0,0,221,222,3,28,14,0,222,
        223,5,6,0,0,223,224,3,16,8,0,224,226,1,0,0,0,225,218,1,0,0,0,226,
        229,1,0,0,0,227,225,1,0,0,0,227,228,1,0,0,0,228,232,1,0,0,0,229,
        227,1,0,0,0,230,231,5,54,0,0,231,233,3,16,8,0,232,230,1,0,0,0,232,
        233,1,0,0,0,233,255,1,0,0,0,234,235,5,45,0,0,235,236,5,5,0,0,236,
        237,5,34,0,0,237,238,3,52,26,0,238,239,5,14,0,0,239,240,3,28,14,
        0,240,241,5,46,0,0,241,242,3,28,14,0,242,243,5,6,0,0,243,244,3,16,
        8,0,244,255,1,0,0,0,245,246,5,45,0,0,246,247,5,5,0,0,247,248,3,36,
        18,0,248,249,3,52,26,0,249,250,5,47,0,0,250,251,3,28,14,0,251,252,
        5,6,0,0,252,253,3,16,8,0,253,255,1,0,0,0,254,158,1,0,0,0,254,162,
        1,0,0,0,254,168,1,0,0,0,254,174,1,0,0,0,254,179,1,0,0,0,254,184,
        1,0,0,0,254,193,1,0,0,0,254,201,1,0,0,0,254,209,1,0,0,0,254,213,
        1,0,0,0,254,234,1,0,0,0,254,245,1,0,0,0,255,19,1,0,0,0,256,260,3,
        52,26,0,257,260,3,34,17,0,258,260,5,56,0,0,259,256,1,0,0,0,259,257,
        1,0,0,0,259,258,1,0,0,0,260,269,1,0,0,0,261,262,5,12,0,0,262,268,
        3,52,26,0,263,264,5,3,0,0,264,265,3,28,14,0,265,266,5,4,0,0,266,
        268,1,0,0,0,267,261,1,0,0,0,267,263,1,0,0,0,268,271,1,0,0,0,269,
        267,1,0,0,0,269,270,1,0,0,0,270,21,1,0,0,0,271,269,1,0,0,0,272,273,
        7,0,0,0,273,23,1,0,0,0,274,276,3,22,11,0,275,274,1,0,0,0,276,279,
        1,0,0,0,277,275,1,0,0,0,277,278,1,0,0,0,278,280,1,0,0,0,279,277,
        1,0,0,0,280,281,3,36,18,0,281,282,3,52,26,0,282,284,5,5,0,0,283,
        285,3,26,13,0,284,283,1,0,0,0,284,285,1,0,0,0,285,286,1,0,0,0,286,
        287,5,6,0,0,287,25,1,0,0,0,288,293,3,32,16,0,289,290,5,11,0,0,290,
        292,3,32,16,0,291,289,1,0,0,0,292,295,1,0,0,0,293,291,1,0,0,0,293,
        294,1,0,0,0,294,27,1,0,0,0,295,293,1,0,0,0,296,297,6,14,-1,0,297,
        298,5,28,0,0,298,344,3,28,14,31,299,300,5,30,0,0,300,301,3,28,14,
        0,301,302,5,30,0,0,302,344,1,0,0,0,303,304,5,16,0,0,304,344,3,28,
        14,26,305,344,3,20,10,0,306,315,5,3,0,0,307,312,3,28,14,0,308,309,
        5,11,0,0,309,311,3,28,14,0,310,308,1,0,0,0,311,314,1,0,0,0,312,310,
        1,0,0,0,312,313,1,0,0,0,313,316,1,0,0,0,314,312,1,0,0,0,315,307,
        1,0,0,0,315,316,1,0,0,0,316,317,1,0,0,0,317,344,5,4,0,0,318,327,
        5,1,0,0,319,324,3,28,14,0,320,321,5,11,0,0,321,323,3,28,14,0,322,
        320,1,0,0,0,323,326,1,0,0,0,324,322,1,0,0,0,324,325,1,0,0,0,325,
        328,1,0,0,0,326,324,1,0,0,0,327,319,1,0,0,0,327,328,1,0,0,0,328,
        329,1,0,0,0,329,344,5,2,0,0,330,344,3,36,18,0,331,332,5,62,0,0,332,
        344,3,40,20,0,333,334,5,63,0,0,334,344,3,40,20,0,335,344,5,61,0,
        0,336,344,5,64,0,0,337,344,3,48,24,0,338,344,5,55,0,0,339,340,5,
        5,0,0,340,341,3,28,14,0,341,342,5,6,0,0,342,344,1,0,0,0,343,296,
        1,0,0,0,343,299,1,0,0,0,343,303,1,0,0,0,343,305,1,0,0,0,343,306,
        1,0,0,0,343,318,1,0,0,0,343,330,1,0,0,0,343,331,1,0,0,0,343,333,
        1,0,0,0,343,335,1,0,0,0,343,336,1,0,0,0,343,337,1,0,0,0,343,338,
        1,0,0,0,343,339,1,0,0,0,344,411,1,0,0,0,345,346,10,29,0,0,346,347,
        5,29,0,0,347,410,3,28,14,29,348,349,10,28,0,0,349,350,5,13,0,0,350,
        410,3,28,14,29,351,352,10,27,0,0,352,353,5,17,0,0,353,410,3,28,14,
        28,354,355,10,25,0,0,355,356,5,15,0,0,356,410,3,28,14,26,357,358,
        10,24,0,0,358,359,5,16,0,0,359,410,3,28,14,25,360,361,10,23,0,0,
        361,362,5,19,0,0,362,410,3,28,14,24,363,364,10,22,0,0,364,365,5,
        20,0,0,365,410,3,28,14,23,366,367,10,21,0,0,367,368,5,8,0,0,368,
        410,3,28,14,22,369,370,10,20,0,0,370,371,5,7,0,0,371,410,3,28,14,
        21,372,373,10,19,0,0,373,374,5,21,0,0,374,410,3,28,14,20,375,376,
        10,18,0,0,376,377,5,22,0,0,377,410,3,28,14,19,378,379,10,17,0,0,
        379,380,5,47,0,0,380,410,3,28,14,18,381,382,10,16,0,0,382,383,5,
        43,0,0,383,410,3,28,14,17,384,385,10,15,0,0,385,386,5,26,0,0,386,
        410,3,28,14,16,387,388,10,14,0,0,388,389,5,23,0,0,389,410,3,28,14,
        15,390,391,10,13,0,0,391,392,5,48,0,0,392,410,3,28,14,14,393,394,
        10,12,0,0,394,395,5,27,0,0,395,410,3,28,14,13,396,397,10,33,0,0,
        397,399,5,5,0,0,398,400,3,30,15,0,399,398,1,0,0,0,399,400,1,0,0,
        0,400,401,1,0,0,0,401,410,5,6,0,0,402,403,10,32,0,0,403,404,5,3,
        0,0,404,405,3,38,19,0,405,406,5,10,0,0,406,407,3,38,19,0,407,408,
        5,4,0,0,408,410,1,0,0,0,409,345,1,0,0,0,409,348,1,0,0,0,409,351,
        1,0,0,0,409,354,1,0,0,0,409,357,1,0,0,0,409,360,1,0,0,0,409,363,
        1,0,0,0,409,366,1,0,0,0,409,369,1,0,0,0,409,372,1,0,0,0,409,375,
        1,0,0,0,409,378,1,0,0,0,409,381,1,0,0,0,409,384,1,0,0,0,409,387,
        1,0,0,0,409,390,1,0,0,0,409,393,1,0,0,0,409,396,1,0,0,0,409,402,
        1,0,0,0,410,413,1,0,0,0,411,409,1,0,0,0,411,412,1,0,0,0,412,29,1,
        0,0,0,413,411,1,0,0,0,414,419,3,28,14,0,415,416,5,11,0,0,416,418,
        3,28,14,0,417,415,1,0,0,0,418,421,1,0,0,0,419,417,1,0,0,0,419,420,
        1,0,0,0,420,31,1,0,0,0,421,419,1,0,0,0,422,423,3,36,18,0,423,424,
        3,52,26,0,424,33,1,0,0,0,425,426,5,65,0,0,426,428,5,5,0,0,427,429,
        3,30,15,0,428,427,1,0,0,0,428,429,1,0,0,0,429,430,1,0,0,0,430,431,
        5,6,0,0,431,35,1,0,0,0,432,433,6,18,-1,0,433,472,3,46,23,0,434,472,
        5,32,0,0,435,472,5,33,0,0,436,437,5,35,0,0,437,438,5,7,0,0,438,439,
        3,36,18,0,439,440,5,11,0,0,440,441,3,36,18,0,441,442,5,8,0,0,442,
        472,1,0,0,0,443,444,5,40,0,0,444,445,5,7,0,0,445,446,3,36,18,0,446,
        447,5,11,0,0,447,448,3,38,19,0,448,449,5,8,0,0,449,472,1,0,0,0,450,
        451,5,41,0,0,451,452,5,7,0,0,452,453,3,36,18,0,453,454,5,11,0,0,
        454,455,3,36,18,0,455,456,5,8,0,0,456,472,1,0,0,0,457,472,5,34,0,
        0,458,459,5,3,0,0,459,462,3,36,18,0,460,461,5,11,0,0,461,463,3,36,
        18,0,462,460,1,0,0,0,463,464,1,0,0,0,464,462,1,0,0,0,464,465,1,0,
        0,0,465,466,1,0,0,0,466,467,5,4,0,0,467,472,1,0,0,0,468,472,3,42,
        21,0,469,472,3,44,22,0,470,472,3,20,10,0,471,432,1,0,0,0,471,434,
        1,0,0,0,471,435,1,0,0,0,471,436,1,0,0,0,471,443,1,0,0,0,471,450,
        1,0,0,0,471,457,1,0,0,0,471,458,1,0,0,0,471,468,1,0,0,0,471,469,
        1,0,0,0,471,470,1,0,0,0,472,477,1,0,0,0,473,474,10,12,0,0,474,476,
        5,18,0,0,475,473,1,0,0,0,476,479,1,0,0,0,477,475,1,0,0,0,477,478,
        1,0,0,0,478,37,1,0,0,0,479,477,1,0,0,0,480,481,6,19,-1,0,481,489,
        3,20,10,0,482,489,5,64,0,0,483,489,5,61,0,0,484,485,5,5,0,0,485,
        486,3,38,19,0,486,487,5,6,0,0,487,489,1,0,0,0,488,480,1,0,0,0,488,
        482,1,0,0,0,488,483,1,0,0,0,488,484,1,0,0,0,489,504,1,0,0,0,490,
        491,10,8,0,0,491,492,5,13,0,0,492,503,3,38,19,9,493,494,10,7,0,0,
        494,495,5,17,0,0,495,503,3,38,19,8,496,497,10,6,0,0,497,498,5,15,
        0,0,498,503,3,38,19,7,499,500,10,5,0,0,500,501,5,16,0,0,501,503,
        3,38,19,6,502,490,1,0,0,0,502,493,1,0,0,0,502,496,1,0,0,0,502,499,
        1,0,0,0,503,506,1,0,0,0,504,502,1,0,0,0,504,505,1,0,0,0,505,39,1,
        0,0,0,506,504,1,0,0,0,507,514,3,20,10,0,508,514,5,64,0,0,509,510,
        5,5,0,0,510,511,3,38,19,0,511,512,5,6,0,0,512,514,1,0,0,0,513,507,
        1,0,0,0,513,508,1,0,0,0,513,509,1,0,0,0,514,41,1,0,0,0,515,516,5,
        38,0,0,516,517,5,7,0,0,517,518,3,38,19,0,518,519,5,8,0,0,519,522,
        1,0,0,0,520,522,5,38,0,0,521,515,1,0,0,0,521,520,1,0,0,0,522,43,
        1,0,0,0,523,524,5,39,0,0,524,525,5,7,0,0,525,526,3,38,19,0,526,527,
        5,8,0,0,527,45,1,0,0,0,528,529,5,31,0,0,529,530,5,7,0,0,530,531,
        3,36,18,0,531,532,5,8,0,0,532,535,1,0,0,0,533,535,5,31,0,0,534,528,
        1,0,0,0,534,533,1,0,0,0,535,47,1,0,0,0,536,537,7,1,0,0,537,49,1,
        0,0,0,538,539,5,37,0,0,539,542,5,68,0,0,540,541,5,51,0,0,541,543,
        5,65,0,0,542,540,1,0,0,0,542,543,1,0,0,0,543,544,1,0,0,0,544,545,
        5,9,0,0,545,51,1,0,0,0,546,547,7,2,0,0,547,53,1,0,0,0,42,57,74,86,
        92,99,105,111,113,120,130,140,153,204,227,232,254,259,267,269,277,
        284,293,312,315,324,327,343,399,409,411,419,428,464,471,477,488,
        502,504,513,521,534,542
    ]

class GameParser ( Parser ):

    grammarFileName = "Game.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'{'", "'}'", "'['", "']'", "'('", "')'", 
                     "'<'", "'>'", "';'", "':'", "','", "'.'", "'*'", "'='", 
                     "'+'", "'-'", "'/'", "'?'", "'=='", "'!='", "'>='", 
                     "'<='", "'||'", "'<-uniq'", "'<-'", "'&&'", "'\\'", 
                     "'!'", "'^'", "'|'", "'Set'", "'Bool'", "'Void'", "'Int'", 
                     "'Map'", "'return'", "'import'", "'BitString'", "'ModInt'", 
                     "'Array'", "'RandomFunctions'", "'Primitive'", "'subsets'", 
                     "'if'", "'for'", "'to'", "'in'", "'union'", "'Game'", 
                     "'export'", "'as'", "'Phase'", "'oracles'", "'else'", 
                     "'None'", "'this'", "'deterministic'", "'injective'", 
                     "'true'", "'false'", "<INVALID>", "'0^'", "'1^'" ]

    symbolicNames = [ "<INVALID>", "L_CURLY", "R_CURLY", "L_SQUARE", "R_SQUARE", 
                      "L_PAREN", "R_PAREN", "L_ANGLE", "R_ANGLE", "SEMI", 
                      "COLON", "COMMA", "PERIOD", "TIMES", "EQUALS", "PLUS", 
                      "SUBTRACT", "DIVIDE", "QUESTION", "EQUALSCOMPARE", 
                      "NOTEQUALS", "GEQ", "LEQ", "OR", "SAMPUNIQ", "SAMPLES", 
                      "AND", "BACKSLASH", "NOT", "CARET", "VBAR", "SET", 
                      "BOOL", "VOID", "INTTYPE", "MAP", "RETURN", "IMPORT", 
                      "BITSTRING", "MODINT", "ARRAY", "RANDOMFUNCTIONS", 
                      "PRIMITIVE", "SUBSETS", "IF", "FOR", "TO", "IN", "UNION", 
                      "GAME", "EXPORT", "AS", "PHASE", "ORACLES", "ELSE", 
                      "NONE", "THIS", "DETERMINISTIC", "INJECTIVE", "TRUE", 
                      "FALSE", "BINARYNUM", "ZEROS_CARET", "ONES_CARET", 
                      "INT", "ID", "WS", "LINE_COMMENT", "FILESTRING" ]

    RULE_program = 0
    RULE_gameExport = 1
    RULE_game = 2
    RULE_gameBody = 3
    RULE_gamePhase = 4
    RULE_field = 5
    RULE_initializedField = 6
    RULE_method = 7
    RULE_block = 8
    RULE_statement = 9
    RULE_lvalue = 10
    RULE_methodModifier = 11
    RULE_methodSignature = 12
    RULE_paramList = 13
    RULE_expression = 14
    RULE_argList = 15
    RULE_variable = 16
    RULE_parameterizedGame = 17
    RULE_type = 18
    RULE_integerExpression = 19
    RULE_integerAtom = 20
    RULE_bitstring = 21
    RULE_modint = 22
    RULE_set = 23
    RULE_bool = 24
    RULE_moduleImport = 25
    RULE_id = 26

    ruleNames =  [ "program", "gameExport", "game", "gameBody", "gamePhase", 
                   "field", "initializedField", "method", "block", "statement", 
                   "lvalue", "methodModifier", "methodSignature", "paramList", 
                   "expression", "argList", "variable", "parameterizedGame", 
                   "type", "integerExpression", "integerAtom", "bitstring", 
                   "modint", "set", "bool", "moduleImport", "id" ]

    EOF = Token.EOF
    L_CURLY=1
    R_CURLY=2
    L_SQUARE=3
    R_SQUARE=4
    L_PAREN=5
    R_PAREN=6
    L_ANGLE=7
    R_ANGLE=8
    SEMI=9
    COLON=10
    COMMA=11
    PERIOD=12
    TIMES=13
    EQUALS=14
    PLUS=15
    SUBTRACT=16
    DIVIDE=17
    QUESTION=18
    EQUALSCOMPARE=19
    NOTEQUALS=20
    GEQ=21
    LEQ=22
    OR=23
    SAMPUNIQ=24
    SAMPLES=25
    AND=26
    BACKSLASH=27
    NOT=28
    CARET=29
    VBAR=30
    SET=31
    BOOL=32
    VOID=33
    INTTYPE=34
    MAP=35
    RETURN=36
    IMPORT=37
    BITSTRING=38
    MODINT=39
    ARRAY=40
    RANDOMFUNCTIONS=41
    PRIMITIVE=42
    SUBSETS=43
    IF=44
    FOR=45
    TO=46
    IN=47
    UNION=48
    GAME=49
    EXPORT=50
    AS=51
    PHASE=52
    ORACLES=53
    ELSE=54
    NONE=55
    THIS=56
    DETERMINISTIC=57
    INJECTIVE=58
    TRUE=59
    FALSE=60
    BINARYNUM=61
    ZEROS_CARET=62
    ONES_CARET=63
    INT=64
    ID=65
    WS=66
    LINE_COMMENT=67
    FILESTRING=68

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.2")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class ProgramContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def game(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.GameContext)
            else:
                return self.getTypedRuleContext(GameParser.GameContext,i)


        def gameExport(self):
            return self.getTypedRuleContext(GameParser.GameExportContext,0)


        def EOF(self):
            return self.getToken(GameParser.EOF, 0)

        def moduleImport(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ModuleImportContext)
            else:
                return self.getTypedRuleContext(GameParser.ModuleImportContext,i)


        def getRuleIndex(self):
            return GameParser.RULE_program

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitProgram" ):
                return visitor.visitProgram(self)
            else:
                return visitor.visitChildren(self)




    def program(self):

        localctx = GameParser.ProgramContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_program)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 57
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==37:
                self.state = 54
                self.moduleImport()
                self.state = 59
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 60
            self.game()
            self.state = 61
            self.game()
            self.state = 62
            self.gameExport()
            self.state = 63
            self.match(GameParser.EOF)
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
            return self.getToken(GameParser.EXPORT, 0)

        def AS(self):
            return self.getToken(GameParser.AS, 0)

        def ID(self):
            return self.getToken(GameParser.ID, 0)

        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)

        def getRuleIndex(self):
            return GameParser.RULE_gameExport

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGameExport" ):
                return visitor.visitGameExport(self)
            else:
                return visitor.visitChildren(self)




    def gameExport(self):

        localctx = GameParser.GameExportContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_gameExport)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 65
            self.match(GameParser.EXPORT)
            self.state = 66
            self.match(GameParser.AS)
            self.state = 67
            self.match(GameParser.ID)
            self.state = 68
            self.match(GameParser.SEMI)
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
            return self.getToken(GameParser.GAME, 0)

        def ID(self):
            return self.getToken(GameParser.ID, 0)

        def L_PAREN(self):
            return self.getToken(GameParser.L_PAREN, 0)

        def R_PAREN(self):
            return self.getToken(GameParser.R_PAREN, 0)

        def L_CURLY(self):
            return self.getToken(GameParser.L_CURLY, 0)

        def gameBody(self):
            return self.getTypedRuleContext(GameParser.GameBodyContext,0)


        def R_CURLY(self):
            return self.getToken(GameParser.R_CURLY, 0)

        def paramList(self):
            return self.getTypedRuleContext(GameParser.ParamListContext,0)


        def getRuleIndex(self):
            return GameParser.RULE_game

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGame" ):
                return visitor.visitGame(self)
            else:
                return visitor.visitChildren(self)




    def game(self):

        localctx = GameParser.GameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_game)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 70
            self.match(GameParser.GAME)
            self.state = 71
            self.match(GameParser.ID)
            self.state = 72
            self.match(GameParser.L_PAREN)
            self.state = 74
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 3)) & ~0x3f) == 0 and ((1 << (_la - 3)) & 4620711333585747969) != 0):
                self.state = 73
                self.paramList()


            self.state = 76
            self.match(GameParser.R_PAREN)
            self.state = 77
            self.match(GameParser.L_CURLY)
            self.state = 78
            self.gameBody()
            self.state = 79
            self.match(GameParser.R_CURLY)
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
                return self.getTypedRuleContexts(GameParser.FieldContext)
            else:
                return self.getTypedRuleContext(GameParser.FieldContext,i)


        def SEMI(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.SEMI)
            else:
                return self.getToken(GameParser.SEMI, i)

        def method(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.MethodContext)
            else:
                return self.getTypedRuleContext(GameParser.MethodContext,i)


        def gamePhase(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.GamePhaseContext)
            else:
                return self.getTypedRuleContext(GameParser.GamePhaseContext,i)


        def getRuleIndex(self):
            return GameParser.RULE_gameBody

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGameBody" ):
                return visitor.visitGameBody(self)
            else:
                return visitor.visitChildren(self)




    def gameBody(self):

        localctx = GameParser.GameBodyContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_gameBody)
        self._la = 0 # Token type
        try:
            self.state = 113
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,7,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 86
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,2,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 81
                        self.field()
                        self.state = 82
                        self.match(GameParser.SEMI) 
                    self.state = 88
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,2,self._ctx)

                self.state = 90 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 89
                    self.method()
                    self.state = 92 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (((((_la - 3)) & ~0x3f) == 0 and ((1 << (_la - 3)) & 4674754529114193921) != 0)):
                        break

                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 99
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,4,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 94
                        self.field()
                        self.state = 95
                        self.match(GameParser.SEMI) 
                    self.state = 101
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,4,self._ctx)

                self.state = 105
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while ((((_la - 3)) & ~0x3f) == 0 and ((1 << (_la - 3)) & 4674754529114193921) != 0):
                    self.state = 102
                    self.method()
                    self.state = 107
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 109 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 108
                    self.gamePhase()
                    self.state = 111 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==52):
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
            return self.getToken(GameParser.PHASE, 0)

        def L_CURLY(self):
            return self.getToken(GameParser.L_CURLY, 0)

        def ORACLES(self):
            return self.getToken(GameParser.ORACLES, 0)

        def COLON(self):
            return self.getToken(GameParser.COLON, 0)

        def L_SQUARE(self):
            return self.getToken(GameParser.L_SQUARE, 0)

        def id_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.IdContext)
            else:
                return self.getTypedRuleContext(GameParser.IdContext,i)


        def R_SQUARE(self):
            return self.getToken(GameParser.R_SQUARE, 0)

        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)

        def R_CURLY(self):
            return self.getToken(GameParser.R_CURLY, 0)

        def method(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.MethodContext)
            else:
                return self.getTypedRuleContext(GameParser.MethodContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.COMMA)
            else:
                return self.getToken(GameParser.COMMA, i)

        def getRuleIndex(self):
            return GameParser.RULE_gamePhase

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGamePhase" ):
                return visitor.visitGamePhase(self)
            else:
                return visitor.visitChildren(self)




    def gamePhase(self):

        localctx = GameParser.GamePhaseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_gamePhase)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 115
            self.match(GameParser.PHASE)
            self.state = 116
            self.match(GameParser.L_CURLY)
            self.state = 118 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 117
                self.method()
                self.state = 120 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (((((_la - 3)) & ~0x3f) == 0 and ((1 << (_la - 3)) & 4674754529114193921) != 0)):
                    break

            self.state = 122
            self.match(GameParser.ORACLES)
            self.state = 123
            self.match(GameParser.COLON)
            self.state = 124
            self.match(GameParser.L_SQUARE)
            self.state = 125
            self.id_()
            self.state = 130
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==11:
                self.state = 126
                self.match(GameParser.COMMA)
                self.state = 127
                self.id_()
                self.state = 132
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 133
            self.match(GameParser.R_SQUARE)
            self.state = 134
            self.match(GameParser.SEMI)
            self.state = 135
            self.match(GameParser.R_CURLY)
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
            return self.getTypedRuleContext(GameParser.VariableContext,0)


        def EQUALS(self):
            return self.getToken(GameParser.EQUALS, 0)

        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)


        def getRuleIndex(self):
            return GameParser.RULE_field

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitField" ):
                return visitor.visitField(self)
            else:
                return visitor.visitChildren(self)




    def field(self):

        localctx = GameParser.FieldContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_field)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 137
            self.variable()
            self.state = 140
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==14:
                self.state = 138
                self.match(GameParser.EQUALS)
                self.state = 139
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
            return self.getTypedRuleContext(GameParser.VariableContext,0)


        def EQUALS(self):
            return self.getToken(GameParser.EQUALS, 0)

        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)


        def getRuleIndex(self):
            return GameParser.RULE_initializedField

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitInitializedField" ):
                return visitor.visitInitializedField(self)
            else:
                return visitor.visitChildren(self)




    def initializedField(self):

        localctx = GameParser.InitializedFieldContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_initializedField)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 142
            self.variable()
            self.state = 143
            self.match(GameParser.EQUALS)
            self.state = 144
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
            return self.getTypedRuleContext(GameParser.MethodSignatureContext,0)


        def block(self):
            return self.getTypedRuleContext(GameParser.BlockContext,0)


        def getRuleIndex(self):
            return GameParser.RULE_method

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMethod" ):
                return visitor.visitMethod(self)
            else:
                return visitor.visitChildren(self)




    def method(self):

        localctx = GameParser.MethodContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_method)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 146
            self.methodSignature()
            self.state = 147
            self.block()
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

        def L_CURLY(self):
            return self.getToken(GameParser.L_CURLY, 0)

        def R_CURLY(self):
            return self.getToken(GameParser.R_CURLY, 0)

        def statement(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.StatementContext)
            else:
                return self.getTypedRuleContext(GameParser.StatementContext,i)


        def getRuleIndex(self):
            return GameParser.RULE_block

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBlock" ):
                return visitor.visitBlock(self)
            else:
                return visitor.visitChildren(self)




    def block(self):

        localctx = GameParser.BlockContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_block)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 149
            self.match(GameParser.L_CURLY)
            self.state = 153
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & -468176587397726166) != 0) or _la==64 or _la==65:
                self.state = 150
                self.statement()
                self.state = 155
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 156
            self.match(GameParser.R_CURLY)
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
            return GameParser.RULE_statement

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)



    class UniqueSampleStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.TypeContext)
            else:
                return self.getTypedRuleContext(GameParser.TypeContext,i)

        def lvalue(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.LvalueContext)
            else:
                return self.getTypedRuleContext(GameParser.LvalueContext,i)

        def SAMPUNIQ(self):
            return self.getToken(GameParser.SAMPUNIQ, 0)
        def L_SQUARE(self):
            return self.getToken(GameParser.L_SQUARE, 0)
        def R_SQUARE(self):
            return self.getToken(GameParser.R_SQUARE, 0)
        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitUniqueSampleStatement" ):
                return visitor.visitUniqueSampleStatement(self)
            else:
                return visitor.visitChildren(self)


    class VarDeclWithSampleStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(GameParser.TypeContext,0)

        def lvalue(self):
            return self.getTypedRuleContext(GameParser.LvalueContext,0)

        def SAMPLES(self):
            return self.getToken(GameParser.SAMPLES, 0)
        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)

        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVarDeclWithSampleStatement" ):
                return visitor.visitVarDeclWithSampleStatement(self)
            else:
                return visitor.visitChildren(self)


    class VarDeclStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(GameParser.TypeContext,0)

        def id_(self):
            return self.getTypedRuleContext(GameParser.IdContext,0)

        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVarDeclStatement" ):
                return visitor.visitVarDeclStatement(self)
            else:
                return visitor.visitChildren(self)


    class GenericForStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def FOR(self):
            return self.getToken(GameParser.FOR, 0)
        def L_PAREN(self):
            return self.getToken(GameParser.L_PAREN, 0)
        def type_(self):
            return self.getTypedRuleContext(GameParser.TypeContext,0)

        def id_(self):
            return self.getTypedRuleContext(GameParser.IdContext,0)

        def IN(self):
            return self.getToken(GameParser.IN, 0)
        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)

        def R_PAREN(self):
            return self.getToken(GameParser.R_PAREN, 0)
        def block(self):
            return self.getTypedRuleContext(GameParser.BlockContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGenericForStatement" ):
                return visitor.visitGenericForStatement(self)
            else:
                return visitor.visitChildren(self)


    class VarDeclWithValueStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(GameParser.TypeContext,0)

        def lvalue(self):
            return self.getTypedRuleContext(GameParser.LvalueContext,0)

        def EQUALS(self):
            return self.getToken(GameParser.EQUALS, 0)
        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)

        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVarDeclWithValueStatement" ):
                return visitor.visitVarDeclWithValueStatement(self)
            else:
                return visitor.visitChildren(self)


    class AssignmentStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def lvalue(self):
            return self.getTypedRuleContext(GameParser.LvalueContext,0)

        def EQUALS(self):
            return self.getToken(GameParser.EQUALS, 0)
        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)

        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssignmentStatement" ):
                return visitor.visitAssignmentStatement(self)
            else:
                return visitor.visitChildren(self)


    class NumericForStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def FOR(self):
            return self.getToken(GameParser.FOR, 0)
        def L_PAREN(self):
            return self.getToken(GameParser.L_PAREN, 0)
        def INTTYPE(self):
            return self.getToken(GameParser.INTTYPE, 0)
        def id_(self):
            return self.getTypedRuleContext(GameParser.IdContext,0)

        def EQUALS(self):
            return self.getToken(GameParser.EQUALS, 0)
        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def TO(self):
            return self.getToken(GameParser.TO, 0)
        def R_PAREN(self):
            return self.getToken(GameParser.R_PAREN, 0)
        def block(self):
            return self.getTypedRuleContext(GameParser.BlockContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNumericForStatement" ):
                return visitor.visitNumericForStatement(self)
            else:
                return visitor.visitChildren(self)


    class FunctionCallStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)

        def L_PAREN(self):
            return self.getToken(GameParser.L_PAREN, 0)
        def R_PAREN(self):
            return self.getToken(GameParser.R_PAREN, 0)
        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)
        def argList(self):
            return self.getTypedRuleContext(GameParser.ArgListContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFunctionCallStatement" ):
                return visitor.visitFunctionCallStatement(self)
            else:
                return visitor.visitChildren(self)


    class ReturnStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def RETURN(self):
            return self.getToken(GameParser.RETURN, 0)
        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)

        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitReturnStatement" ):
                return visitor.visitReturnStatement(self)
            else:
                return visitor.visitChildren(self)


    class IfStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def IF(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.IF)
            else:
                return self.getToken(GameParser.IF, i)
        def L_PAREN(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.L_PAREN)
            else:
                return self.getToken(GameParser.L_PAREN, i)
        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def R_PAREN(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.R_PAREN)
            else:
                return self.getToken(GameParser.R_PAREN, i)
        def block(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.BlockContext)
            else:
                return self.getTypedRuleContext(GameParser.BlockContext,i)

        def ELSE(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.ELSE)
            else:
                return self.getToken(GameParser.ELSE, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIfStatement" ):
                return visitor.visitIfStatement(self)
            else:
                return visitor.visitChildren(self)


    class UniqueSampleNoTypeStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def lvalue(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.LvalueContext)
            else:
                return self.getTypedRuleContext(GameParser.LvalueContext,i)

        def SAMPUNIQ(self):
            return self.getToken(GameParser.SAMPUNIQ, 0)
        def L_SQUARE(self):
            return self.getToken(GameParser.L_SQUARE, 0)
        def R_SQUARE(self):
            return self.getToken(GameParser.R_SQUARE, 0)
        def type_(self):
            return self.getTypedRuleContext(GameParser.TypeContext,0)

        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitUniqueSampleNoTypeStatement" ):
                return visitor.visitUniqueSampleNoTypeStatement(self)
            else:
                return visitor.visitChildren(self)


    class SampleStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def lvalue(self):
            return self.getTypedRuleContext(GameParser.LvalueContext,0)

        def SAMPLES(self):
            return self.getToken(GameParser.SAMPLES, 0)
        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)

        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSampleStatement" ):
                return visitor.visitSampleStatement(self)
            else:
                return visitor.visitChildren(self)



    def statement(self):

        localctx = GameParser.StatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_statement)
        self._la = 0 # Token type
        try:
            self.state = 254
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,15,self._ctx)
            if la_ == 1:
                localctx = GameParser.VarDeclStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 158
                self.type_(0)
                self.state = 159
                self.id_()
                self.state = 160
                self.match(GameParser.SEMI)
                pass

            elif la_ == 2:
                localctx = GameParser.VarDeclWithValueStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 162
                self.type_(0)
                self.state = 163
                self.lvalue()
                self.state = 164
                self.match(GameParser.EQUALS)
                self.state = 165
                self.expression(0)
                self.state = 166
                self.match(GameParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GameParser.VarDeclWithSampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 168
                self.type_(0)
                self.state = 169
                self.lvalue()
                self.state = 170
                self.match(GameParser.SAMPLES)
                self.state = 171
                self.expression(0)
                self.state = 172
                self.match(GameParser.SEMI)
                pass

            elif la_ == 4:
                localctx = GameParser.AssignmentStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 174
                self.lvalue()
                self.state = 175
                self.match(GameParser.EQUALS)
                self.state = 176
                self.expression(0)
                self.state = 177
                self.match(GameParser.SEMI)
                pass

            elif la_ == 5:
                localctx = GameParser.SampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 5)
                self.state = 179
                self.lvalue()
                self.state = 180
                self.match(GameParser.SAMPLES)
                self.state = 181
                self.expression(0)
                self.state = 182
                self.match(GameParser.SEMI)
                pass

            elif la_ == 6:
                localctx = GameParser.UniqueSampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 6)
                self.state = 184
                self.type_(0)
                self.state = 185
                self.lvalue()
                self.state = 186
                self.match(GameParser.SAMPUNIQ)
                self.state = 187
                self.match(GameParser.L_SQUARE)
                self.state = 188
                self.lvalue()
                self.state = 189
                self.match(GameParser.R_SQUARE)
                self.state = 190
                self.type_(0)
                self.state = 191
                self.match(GameParser.SEMI)
                pass

            elif la_ == 7:
                localctx = GameParser.UniqueSampleNoTypeStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 7)
                self.state = 193
                self.lvalue()
                self.state = 194
                self.match(GameParser.SAMPUNIQ)
                self.state = 195
                self.match(GameParser.L_SQUARE)
                self.state = 196
                self.lvalue()
                self.state = 197
                self.match(GameParser.R_SQUARE)
                self.state = 198
                self.type_(0)
                self.state = 199
                self.match(GameParser.SEMI)
                pass

            elif la_ == 8:
                localctx = GameParser.FunctionCallStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 8)
                self.state = 201
                self.expression(0)
                self.state = 202
                self.match(GameParser.L_PAREN)
                self.state = 204
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & -468229432675336150) != 0) or _la==64 or _la==65:
                    self.state = 203
                    self.argList()


                self.state = 206
                self.match(GameParser.R_PAREN)
                self.state = 207
                self.match(GameParser.SEMI)
                pass

            elif la_ == 9:
                localctx = GameParser.ReturnStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 9)
                self.state = 209
                self.match(GameParser.RETURN)
                self.state = 210
                self.expression(0)
                self.state = 211
                self.match(GameParser.SEMI)
                pass

            elif la_ == 10:
                localctx = GameParser.IfStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 10)
                self.state = 213
                self.match(GameParser.IF)
                self.state = 214
                self.match(GameParser.L_PAREN)
                self.state = 215
                self.expression(0)
                self.state = 216
                self.match(GameParser.R_PAREN)
                self.state = 217
                self.block()
                self.state = 227
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,13,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 218
                        self.match(GameParser.ELSE)
                        self.state = 219
                        self.match(GameParser.IF)
                        self.state = 220
                        self.match(GameParser.L_PAREN)
                        self.state = 221
                        self.expression(0)
                        self.state = 222
                        self.match(GameParser.R_PAREN)
                        self.state = 223
                        self.block() 
                    self.state = 229
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,13,self._ctx)

                self.state = 232
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==54:
                    self.state = 230
                    self.match(GameParser.ELSE)
                    self.state = 231
                    self.block()


                pass

            elif la_ == 11:
                localctx = GameParser.NumericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 11)
                self.state = 234
                self.match(GameParser.FOR)
                self.state = 235
                self.match(GameParser.L_PAREN)
                self.state = 236
                self.match(GameParser.INTTYPE)
                self.state = 237
                self.id_()
                self.state = 238
                self.match(GameParser.EQUALS)
                self.state = 239
                self.expression(0)
                self.state = 240
                self.match(GameParser.TO)
                self.state = 241
                self.expression(0)
                self.state = 242
                self.match(GameParser.R_PAREN)
                self.state = 243
                self.block()
                pass

            elif la_ == 12:
                localctx = GameParser.GenericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 12)
                self.state = 245
                self.match(GameParser.FOR)
                self.state = 246
                self.match(GameParser.L_PAREN)
                self.state = 247
                self.type_(0)
                self.state = 248
                self.id_()
                self.state = 249
                self.match(GameParser.IN)
                self.state = 250
                self.expression(0)
                self.state = 251
                self.match(GameParser.R_PAREN)
                self.state = 252
                self.block()
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
                return self.getTypedRuleContexts(GameParser.IdContext)
            else:
                return self.getTypedRuleContext(GameParser.IdContext,i)


        def parameterizedGame(self):
            return self.getTypedRuleContext(GameParser.ParameterizedGameContext,0)


        def THIS(self):
            return self.getToken(GameParser.THIS, 0)

        def PERIOD(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.PERIOD)
            else:
                return self.getToken(GameParser.PERIOD, i)

        def L_SQUARE(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.L_SQUARE)
            else:
                return self.getToken(GameParser.L_SQUARE, i)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)


        def R_SQUARE(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.R_SQUARE)
            else:
                return self.getToken(GameParser.R_SQUARE, i)

        def getRuleIndex(self):
            return GameParser.RULE_lvalue

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLvalue" ):
                return visitor.visitLvalue(self)
            else:
                return visitor.visitChildren(self)




    def lvalue(self):

        localctx = GameParser.LvalueContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_lvalue)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 259
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,16,self._ctx)
            if la_ == 1:
                self.state = 256
                self.id_()
                pass

            elif la_ == 2:
                self.state = 257
                self.parameterizedGame()
                pass

            elif la_ == 3:
                self.state = 258
                self.match(GameParser.THIS)
                pass


            self.state = 269
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,18,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 267
                    self._errHandler.sync(self)
                    token = self._input.LA(1)
                    if token in [12]:
                        self.state = 261
                        self.match(GameParser.PERIOD)
                        self.state = 262
                        self.id_()
                        pass
                    elif token in [3]:
                        self.state = 263
                        self.match(GameParser.L_SQUARE)
                        self.state = 264
                        self.expression(0)
                        self.state = 265
                        self.match(GameParser.R_SQUARE)
                        pass
                    else:
                        raise NoViableAltException(self)
             
                self.state = 271
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,18,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class MethodModifierContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def DETERMINISTIC(self):
            return self.getToken(GameParser.DETERMINISTIC, 0)

        def INJECTIVE(self):
            return self.getToken(GameParser.INJECTIVE, 0)

        def getRuleIndex(self):
            return GameParser.RULE_methodModifier

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMethodModifier" ):
                return visitor.visitMethodModifier(self)
            else:
                return visitor.visitChildren(self)




    def methodModifier(self):

        localctx = GameParser.MethodModifierContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_methodModifier)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 272
            _la = self._input.LA(1)
            if not(_la==57 or _la==58):
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


    class MethodSignatureContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def type_(self):
            return self.getTypedRuleContext(GameParser.TypeContext,0)


        def id_(self):
            return self.getTypedRuleContext(GameParser.IdContext,0)


        def L_PAREN(self):
            return self.getToken(GameParser.L_PAREN, 0)

        def R_PAREN(self):
            return self.getToken(GameParser.R_PAREN, 0)

        def methodModifier(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.MethodModifierContext)
            else:
                return self.getTypedRuleContext(GameParser.MethodModifierContext,i)


        def paramList(self):
            return self.getTypedRuleContext(GameParser.ParamListContext,0)


        def getRuleIndex(self):
            return GameParser.RULE_methodSignature

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMethodSignature" ):
                return visitor.visitMethodSignature(self)
            else:
                return visitor.visitChildren(self)




    def methodSignature(self):

        localctx = GameParser.MethodSignatureContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_methodSignature)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 277
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==57 or _la==58:
                self.state = 274
                self.methodModifier()
                self.state = 279
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 280
            self.type_(0)
            self.state = 281
            self.id_()
            self.state = 282
            self.match(GameParser.L_PAREN)
            self.state = 284
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 3)) & ~0x3f) == 0 and ((1 << (_la - 3)) & 4620711333585747969) != 0):
                self.state = 283
                self.paramList()


            self.state = 286
            self.match(GameParser.R_PAREN)
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
                return self.getTypedRuleContexts(GameParser.VariableContext)
            else:
                return self.getTypedRuleContext(GameParser.VariableContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.COMMA)
            else:
                return self.getToken(GameParser.COMMA, i)

        def getRuleIndex(self):
            return GameParser.RULE_paramList

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitParamList" ):
                return visitor.visitParamList(self)
            else:
                return visitor.visitChildren(self)




    def paramList(self):

        localctx = GameParser.ParamListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_paramList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 288
            self.variable()
            self.state = 293
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==11:
                self.state = 289
                self.match(GameParser.COMMA)
                self.state = 290
                self.variable()
                self.state = 295
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
            return GameParser.RULE_expression

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)


    class CreateSetExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def L_CURLY(self):
            return self.getToken(GameParser.L_CURLY, 0)
        def R_CURLY(self):
            return self.getToken(GameParser.R_CURLY, 0)
        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.COMMA)
            else:
                return self.getToken(GameParser.COMMA, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCreateSetExp" ):
                return visitor.visitCreateSetExp(self)
            else:
                return visitor.visitChildren(self)


    class InExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def IN(self):
            return self.getToken(GameParser.IN, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitInExp" ):
                return visitor.visitInExp(self)
            else:
                return visitor.visitChildren(self)


    class AndExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def AND(self):
            return self.getToken(GameParser.AND, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAndExp" ):
                return visitor.visitAndExp(self)
            else:
                return visitor.visitChildren(self)


    class FnCallExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)

        def L_PAREN(self):
            return self.getToken(GameParser.L_PAREN, 0)
        def R_PAREN(self):
            return self.getToken(GameParser.R_PAREN, 0)
        def argList(self):
            return self.getTypedRuleContext(GameParser.ArgListContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFnCallExp" ):
                return visitor.visitFnCallExp(self)
            else:
                return visitor.visitChildren(self)


    class LvalueExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def lvalue(self):
            return self.getTypedRuleContext(GameParser.LvalueContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLvalueExp" ):
                return visitor.visitLvalueExp(self)
            else:
                return visitor.visitChildren(self)


    class BoolExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def bool_(self):
            return self.getTypedRuleContext(GameParser.BoolContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBoolExp" ):
                return visitor.visitBoolExp(self)
            else:
                return visitor.visitChildren(self)


    class AddExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def PLUS(self):
            return self.getToken(GameParser.PLUS, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAddExp" ):
                return visitor.visitAddExp(self)
            else:
                return visitor.visitChildren(self)


    class NotEqualsExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def NOTEQUALS(self):
            return self.getToken(GameParser.NOTEQUALS, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNotEqualsExp" ):
                return visitor.visitNotEqualsExp(self)
            else:
                return visitor.visitChildren(self)


    class GeqExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def GEQ(self):
            return self.getToken(GameParser.GEQ, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGeqExp" ):
                return visitor.visitGeqExp(self)
            else:
                return visitor.visitChildren(self)


    class NotExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def NOT(self):
            return self.getToken(GameParser.NOT, 0)
        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNotExp" ):
                return visitor.visitNotExp(self)
            else:
                return visitor.visitChildren(self)


    class NoneExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def NONE(self):
            return self.getToken(GameParser.NONE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNoneExp" ):
                return visitor.visitNoneExp(self)
            else:
                return visitor.visitChildren(self)


    class GtExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def R_ANGLE(self):
            return self.getToken(GameParser.R_ANGLE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGtExp" ):
                return visitor.visitGtExp(self)
            else:
                return visitor.visitChildren(self)


    class LtExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def L_ANGLE(self):
            return self.getToken(GameParser.L_ANGLE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLtExp" ):
                return visitor.visitLtExp(self)
            else:
                return visitor.visitChildren(self)


    class SubtractExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def SUBTRACT(self):
            return self.getToken(GameParser.SUBTRACT, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSubtractExp" ):
                return visitor.visitSubtractExp(self)
            else:
                return visitor.visitChildren(self)


    class EqualsExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def EQUALSCOMPARE(self):
            return self.getToken(GameParser.EQUALSCOMPARE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitEqualsExp" ):
                return visitor.visitEqualsExp(self)
            else:
                return visitor.visitChildren(self)


    class MultiplyExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def TIMES(self):
            return self.getToken(GameParser.TIMES, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMultiplyExp" ):
                return visitor.visitMultiplyExp(self)
            else:
                return visitor.visitChildren(self)


    class SubsetsExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def SUBSETS(self):
            return self.getToken(GameParser.SUBSETS, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSubsetsExp" ):
                return visitor.visitSubsetsExp(self)
            else:
                return visitor.visitChildren(self)


    class OnesExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def ONES_CARET(self):
            return self.getToken(GameParser.ONES_CARET, 0)
        def integerAtom(self):
            return self.getTypedRuleContext(GameParser.IntegerAtomContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOnesExp" ):
                return visitor.visitOnesExp(self)
            else:
                return visitor.visitChildren(self)


    class UnionExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def UNION(self):
            return self.getToken(GameParser.UNION, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitUnionExp" ):
                return visitor.visitUnionExp(self)
            else:
                return visitor.visitChildren(self)


    class IntExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def INT(self):
            return self.getToken(GameParser.INT, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIntExp" ):
                return visitor.visitIntExp(self)
            else:
                return visitor.visitChildren(self)


    class SizeExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def VBAR(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.VBAR)
            else:
                return self.getToken(GameParser.VBAR, i)
        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSizeExp" ):
                return visitor.visitSizeExp(self)
            else:
                return visitor.visitChildren(self)


    class MinusExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def SUBTRACT(self):
            return self.getToken(GameParser.SUBTRACT, 0)
        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMinusExp" ):
                return visitor.visitMinusExp(self)
            else:
                return visitor.visitChildren(self)


    class TypeExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(GameParser.TypeContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTypeExp" ):
                return visitor.visitTypeExp(self)
            else:
                return visitor.visitChildren(self)


    class LeqExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def LEQ(self):
            return self.getToken(GameParser.LEQ, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLeqExp" ):
                return visitor.visitLeqExp(self)
            else:
                return visitor.visitChildren(self)


    class OrExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def OR(self):
            return self.getToken(GameParser.OR, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOrExp" ):
                return visitor.visitOrExp(self)
            else:
                return visitor.visitChildren(self)


    class ZerosExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def ZEROS_CARET(self):
            return self.getToken(GameParser.ZEROS_CARET, 0)
        def integerAtom(self):
            return self.getTypedRuleContext(GameParser.IntegerAtomContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitZerosExp" ):
                return visitor.visitZerosExp(self)
            else:
                return visitor.visitChildren(self)


    class ExponentiationExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def CARET(self):
            return self.getToken(GameParser.CARET, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitExponentiationExp" ):
                return visitor.visitExponentiationExp(self)
            else:
                return visitor.visitChildren(self)


    class CreateTupleExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def L_SQUARE(self):
            return self.getToken(GameParser.L_SQUARE, 0)
        def R_SQUARE(self):
            return self.getToken(GameParser.R_SQUARE, 0)
        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.COMMA)
            else:
                return self.getToken(GameParser.COMMA, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCreateTupleExp" ):
                return visitor.visitCreateTupleExp(self)
            else:
                return visitor.visitChildren(self)


    class SetMinusExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def BACKSLASH(self):
            return self.getToken(GameParser.BACKSLASH, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSetMinusExp" ):
                return visitor.visitSetMinusExp(self)
            else:
                return visitor.visitChildren(self)


    class DivideExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def DIVIDE(self):
            return self.getToken(GameParser.DIVIDE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDivideExp" ):
                return visitor.visitDivideExp(self)
            else:
                return visitor.visitChildren(self)


    class BinaryNumExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def BINARYNUM(self):
            return self.getToken(GameParser.BINARYNUM, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBinaryNumExp" ):
                return visitor.visitBinaryNumExp(self)
            else:
                return visitor.visitChildren(self)


    class ParenExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def L_PAREN(self):
            return self.getToken(GameParser.L_PAREN, 0)
        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)

        def R_PAREN(self):
            return self.getToken(GameParser.R_PAREN, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitParenExp" ):
                return visitor.visitParenExp(self)
            else:
                return visitor.visitChildren(self)


    class SliceExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)

        def L_SQUARE(self):
            return self.getToken(GameParser.L_SQUARE, 0)
        def integerExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.IntegerExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.IntegerExpressionContext,i)

        def COLON(self):
            return self.getToken(GameParser.COLON, 0)
        def R_SQUARE(self):
            return self.getToken(GameParser.R_SQUARE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSliceExp" ):
                return visitor.visitSliceExp(self)
            else:
                return visitor.visitChildren(self)



    def expression(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = GameParser.ExpressionContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 28
        self.enterRecursionRule(localctx, 28, self.RULE_expression, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 343
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,26,self._ctx)
            if la_ == 1:
                localctx = GameParser.NotExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 297
                self.match(GameParser.NOT)
                self.state = 298
                self.expression(31)
                pass

            elif la_ == 2:
                localctx = GameParser.SizeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 299
                self.match(GameParser.VBAR)
                self.state = 300
                self.expression(0)
                self.state = 301
                self.match(GameParser.VBAR)
                pass

            elif la_ == 3:
                localctx = GameParser.MinusExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 303
                self.match(GameParser.SUBTRACT)
                self.state = 304
                self.expression(26)
                pass

            elif la_ == 4:
                localctx = GameParser.LvalueExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 305
                self.lvalue()
                pass

            elif la_ == 5:
                localctx = GameParser.CreateTupleExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 306
                self.match(GameParser.L_SQUARE)
                self.state = 315
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & -468229432675336150) != 0) or _la==64 or _la==65:
                    self.state = 307
                    self.expression(0)
                    self.state = 312
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==11:
                        self.state = 308
                        self.match(GameParser.COMMA)
                        self.state = 309
                        self.expression(0)
                        self.state = 314
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 317
                self.match(GameParser.R_SQUARE)
                pass

            elif la_ == 6:
                localctx = GameParser.CreateSetExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 318
                self.match(GameParser.L_CURLY)
                self.state = 327
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & -468229432675336150) != 0) or _la==64 or _la==65:
                    self.state = 319
                    self.expression(0)
                    self.state = 324
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==11:
                        self.state = 320
                        self.match(GameParser.COMMA)
                        self.state = 321
                        self.expression(0)
                        self.state = 326
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 329
                self.match(GameParser.R_CURLY)
                pass

            elif la_ == 7:
                localctx = GameParser.TypeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 330
                self.type_(0)
                pass

            elif la_ == 8:
                localctx = GameParser.ZerosExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 331
                self.match(GameParser.ZEROS_CARET)
                self.state = 332
                self.integerAtom()
                pass

            elif la_ == 9:
                localctx = GameParser.OnesExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 333
                self.match(GameParser.ONES_CARET)
                self.state = 334
                self.integerAtom()
                pass

            elif la_ == 10:
                localctx = GameParser.BinaryNumExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 335
                self.match(GameParser.BINARYNUM)
                pass

            elif la_ == 11:
                localctx = GameParser.IntExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 336
                self.match(GameParser.INT)
                pass

            elif la_ == 12:
                localctx = GameParser.BoolExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 337
                self.bool_()
                pass

            elif la_ == 13:
                localctx = GameParser.NoneExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 338
                self.match(GameParser.NONE)
                pass

            elif la_ == 14:
                localctx = GameParser.ParenExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 339
                self.match(GameParser.L_PAREN)
                self.state = 340
                self.expression(0)
                self.state = 341
                self.match(GameParser.R_PAREN)
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 411
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,29,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 409
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,28,self._ctx)
                    if la_ == 1:
                        localctx = GameParser.ExponentiationExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 345
                        if not self.precpred(self._ctx, 29):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 29)")
                        self.state = 346
                        self.match(GameParser.CARET)
                        self.state = 347
                        self.expression(29)
                        pass

                    elif la_ == 2:
                        localctx = GameParser.MultiplyExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 348
                        if not self.precpred(self._ctx, 28):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 28)")
                        self.state = 349
                        self.match(GameParser.TIMES)
                        self.state = 350
                        self.expression(29)
                        pass

                    elif la_ == 3:
                        localctx = GameParser.DivideExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 351
                        if not self.precpred(self._ctx, 27):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 27)")
                        self.state = 352
                        self.match(GameParser.DIVIDE)
                        self.state = 353
                        self.expression(28)
                        pass

                    elif la_ == 4:
                        localctx = GameParser.AddExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 354
                        if not self.precpred(self._ctx, 25):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 25)")
                        self.state = 355
                        self.match(GameParser.PLUS)
                        self.state = 356
                        self.expression(26)
                        pass

                    elif la_ == 5:
                        localctx = GameParser.SubtractExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 357
                        if not self.precpred(self._ctx, 24):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 24)")
                        self.state = 358
                        self.match(GameParser.SUBTRACT)
                        self.state = 359
                        self.expression(25)
                        pass

                    elif la_ == 6:
                        localctx = GameParser.EqualsExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 360
                        if not self.precpred(self._ctx, 23):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 23)")
                        self.state = 361
                        self.match(GameParser.EQUALSCOMPARE)
                        self.state = 362
                        self.expression(24)
                        pass

                    elif la_ == 7:
                        localctx = GameParser.NotEqualsExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 363
                        if not self.precpred(self._ctx, 22):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 22)")
                        self.state = 364
                        self.match(GameParser.NOTEQUALS)
                        self.state = 365
                        self.expression(23)
                        pass

                    elif la_ == 8:
                        localctx = GameParser.GtExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 366
                        if not self.precpred(self._ctx, 21):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 21)")
                        self.state = 367
                        self.match(GameParser.R_ANGLE)
                        self.state = 368
                        self.expression(22)
                        pass

                    elif la_ == 9:
                        localctx = GameParser.LtExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 369
                        if not self.precpred(self._ctx, 20):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 20)")
                        self.state = 370
                        self.match(GameParser.L_ANGLE)
                        self.state = 371
                        self.expression(21)
                        pass

                    elif la_ == 10:
                        localctx = GameParser.GeqExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 372
                        if not self.precpred(self._ctx, 19):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 19)")
                        self.state = 373
                        self.match(GameParser.GEQ)
                        self.state = 374
                        self.expression(20)
                        pass

                    elif la_ == 11:
                        localctx = GameParser.LeqExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 375
                        if not self.precpred(self._ctx, 18):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 18)")
                        self.state = 376
                        self.match(GameParser.LEQ)
                        self.state = 377
                        self.expression(19)
                        pass

                    elif la_ == 12:
                        localctx = GameParser.InExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 378
                        if not self.precpred(self._ctx, 17):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 17)")
                        self.state = 379
                        self.match(GameParser.IN)
                        self.state = 380
                        self.expression(18)
                        pass

                    elif la_ == 13:
                        localctx = GameParser.SubsetsExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 381
                        if not self.precpred(self._ctx, 16):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 16)")
                        self.state = 382
                        self.match(GameParser.SUBSETS)
                        self.state = 383
                        self.expression(17)
                        pass

                    elif la_ == 14:
                        localctx = GameParser.AndExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 384
                        if not self.precpred(self._ctx, 15):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 15)")
                        self.state = 385
                        self.match(GameParser.AND)
                        self.state = 386
                        self.expression(16)
                        pass

                    elif la_ == 15:
                        localctx = GameParser.OrExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 387
                        if not self.precpred(self._ctx, 14):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 14)")
                        self.state = 388
                        self.match(GameParser.OR)
                        self.state = 389
                        self.expression(15)
                        pass

                    elif la_ == 16:
                        localctx = GameParser.UnionExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 390
                        if not self.precpred(self._ctx, 13):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 13)")
                        self.state = 391
                        self.match(GameParser.UNION)
                        self.state = 392
                        self.expression(14)
                        pass

                    elif la_ == 17:
                        localctx = GameParser.SetMinusExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 393
                        if not self.precpred(self._ctx, 12):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 12)")
                        self.state = 394
                        self.match(GameParser.BACKSLASH)
                        self.state = 395
                        self.expression(13)
                        pass

                    elif la_ == 18:
                        localctx = GameParser.FnCallExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 396
                        if not self.precpred(self._ctx, 33):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 33)")
                        self.state = 397
                        self.match(GameParser.L_PAREN)
                        self.state = 399
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)
                        if (((_la) & ~0x3f) == 0 and ((1 << _la) & -468229432675336150) != 0) or _la==64 or _la==65:
                            self.state = 398
                            self.argList()


                        self.state = 401
                        self.match(GameParser.R_PAREN)
                        pass

                    elif la_ == 19:
                        localctx = GameParser.SliceExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 402
                        if not self.precpred(self._ctx, 32):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 32)")
                        self.state = 403
                        self.match(GameParser.L_SQUARE)
                        self.state = 404
                        self.integerExpression(0)
                        self.state = 405
                        self.match(GameParser.COLON)
                        self.state = 406
                        self.integerExpression(0)
                        self.state = 407
                        self.match(GameParser.R_SQUARE)
                        pass

             
                self.state = 413
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,29,self._ctx)

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
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.COMMA)
            else:
                return self.getToken(GameParser.COMMA, i)

        def getRuleIndex(self):
            return GameParser.RULE_argList

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitArgList" ):
                return visitor.visitArgList(self)
            else:
                return visitor.visitChildren(self)




    def argList(self):

        localctx = GameParser.ArgListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 30, self.RULE_argList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 414
            self.expression(0)
            self.state = 419
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==11:
                self.state = 415
                self.match(GameParser.COMMA)
                self.state = 416
                self.expression(0)
                self.state = 421
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
            return self.getTypedRuleContext(GameParser.TypeContext,0)


        def id_(self):
            return self.getTypedRuleContext(GameParser.IdContext,0)


        def getRuleIndex(self):
            return GameParser.RULE_variable

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVariable" ):
                return visitor.visitVariable(self)
            else:
                return visitor.visitChildren(self)




    def variable(self):

        localctx = GameParser.VariableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_variable)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 422
            self.type_(0)
            self.state = 423
            self.id_()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ParameterizedGameContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(GameParser.ID, 0)

        def L_PAREN(self):
            return self.getToken(GameParser.L_PAREN, 0)

        def R_PAREN(self):
            return self.getToken(GameParser.R_PAREN, 0)

        def argList(self):
            return self.getTypedRuleContext(GameParser.ArgListContext,0)


        def getRuleIndex(self):
            return GameParser.RULE_parameterizedGame

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitParameterizedGame" ):
                return visitor.visitParameterizedGame(self)
            else:
                return visitor.visitChildren(self)




    def parameterizedGame(self):

        localctx = GameParser.ParameterizedGameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_parameterizedGame)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 425
            self.match(GameParser.ID)
            self.state = 426
            self.match(GameParser.L_PAREN)
            self.state = 428
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & -468229432675336150) != 0) or _la==64 or _la==65:
                self.state = 427
                self.argList()


            self.state = 430
            self.match(GameParser.R_PAREN)
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
            return GameParser.RULE_type

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)


    class ArrayTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def ARRAY(self):
            return self.getToken(GameParser.ARRAY, 0)
        def L_ANGLE(self):
            return self.getToken(GameParser.L_ANGLE, 0)
        def type_(self):
            return self.getTypedRuleContext(GameParser.TypeContext,0)

        def COMMA(self):
            return self.getToken(GameParser.COMMA, 0)
        def integerExpression(self):
            return self.getTypedRuleContext(GameParser.IntegerExpressionContext,0)

        def R_ANGLE(self):
            return self.getToken(GameParser.R_ANGLE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitArrayType" ):
                return visitor.visitArrayType(self)
            else:
                return visitor.visitChildren(self)


    class IntTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def INTTYPE(self):
            return self.getToken(GameParser.INTTYPE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIntType" ):
                return visitor.visitIntType(self)
            else:
                return visitor.visitChildren(self)


    class LvalueTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def lvalue(self):
            return self.getTypedRuleContext(GameParser.LvalueContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLvalueType" ):
                return visitor.visitLvalueType(self)
            else:
                return visitor.visitChildren(self)


    class OptionalTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(GameParser.TypeContext,0)

        def QUESTION(self):
            return self.getToken(GameParser.QUESTION, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOptionalType" ):
                return visitor.visitOptionalType(self)
            else:
                return visitor.visitChildren(self)


    class MapTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def MAP(self):
            return self.getToken(GameParser.MAP, 0)
        def L_ANGLE(self):
            return self.getToken(GameParser.L_ANGLE, 0)
        def type_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.TypeContext)
            else:
                return self.getTypedRuleContext(GameParser.TypeContext,i)

        def COMMA(self):
            return self.getToken(GameParser.COMMA, 0)
        def R_ANGLE(self):
            return self.getToken(GameParser.R_ANGLE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMapType" ):
                return visitor.visitMapType(self)
            else:
                return visitor.visitChildren(self)


    class VoidTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def VOID(self):
            return self.getToken(GameParser.VOID, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVoidType" ):
                return visitor.visitVoidType(self)
            else:
                return visitor.visitChildren(self)


    class RandomFunctionTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def RANDOMFUNCTIONS(self):
            return self.getToken(GameParser.RANDOMFUNCTIONS, 0)
        def L_ANGLE(self):
            return self.getToken(GameParser.L_ANGLE, 0)
        def type_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.TypeContext)
            else:
                return self.getTypedRuleContext(GameParser.TypeContext,i)

        def COMMA(self):
            return self.getToken(GameParser.COMMA, 0)
        def R_ANGLE(self):
            return self.getToken(GameParser.R_ANGLE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRandomFunctionType" ):
                return visitor.visitRandomFunctionType(self)
            else:
                return visitor.visitChildren(self)


    class ModIntTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def modint(self):
            return self.getTypedRuleContext(GameParser.ModintContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitModIntType" ):
                return visitor.visitModIntType(self)
            else:
                return visitor.visitChildren(self)


    class SetTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def set_(self):
            return self.getTypedRuleContext(GameParser.SetContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSetType" ):
                return visitor.visitSetType(self)
            else:
                return visitor.visitChildren(self)


    class BitStringTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def bitstring(self):
            return self.getTypedRuleContext(GameParser.BitstringContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBitStringType" ):
                return visitor.visitBitStringType(self)
            else:
                return visitor.visitChildren(self)


    class BoolTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def BOOL(self):
            return self.getToken(GameParser.BOOL, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBoolType" ):
                return visitor.visitBoolType(self)
            else:
                return visitor.visitChildren(self)


    class ProductTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def L_SQUARE(self):
            return self.getToken(GameParser.L_SQUARE, 0)
        def type_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.TypeContext)
            else:
                return self.getTypedRuleContext(GameParser.TypeContext,i)

        def R_SQUARE(self):
            return self.getToken(GameParser.R_SQUARE, 0)
        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.COMMA)
            else:
                return self.getToken(GameParser.COMMA, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitProductType" ):
                return visitor.visitProductType(self)
            else:
                return visitor.visitChildren(self)



    def type_(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = GameParser.TypeContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 36
        self.enterRecursionRule(localctx, 36, self.RULE_type, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 471
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [31]:
                localctx = GameParser.SetTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 433
                self.set_()
                pass
            elif token in [32]:
                localctx = GameParser.BoolTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 434
                self.match(GameParser.BOOL)
                pass
            elif token in [33]:
                localctx = GameParser.VoidTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 435
                self.match(GameParser.VOID)
                pass
            elif token in [35]:
                localctx = GameParser.MapTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 436
                self.match(GameParser.MAP)
                self.state = 437
                self.match(GameParser.L_ANGLE)
                self.state = 438
                self.type_(0)
                self.state = 439
                self.match(GameParser.COMMA)
                self.state = 440
                self.type_(0)
                self.state = 441
                self.match(GameParser.R_ANGLE)
                pass
            elif token in [40]:
                localctx = GameParser.ArrayTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 443
                self.match(GameParser.ARRAY)
                self.state = 444
                self.match(GameParser.L_ANGLE)
                self.state = 445
                self.type_(0)
                self.state = 446
                self.match(GameParser.COMMA)
                self.state = 447
                self.integerExpression(0)
                self.state = 448
                self.match(GameParser.R_ANGLE)
                pass
            elif token in [41]:
                localctx = GameParser.RandomFunctionTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 450
                self.match(GameParser.RANDOMFUNCTIONS)
                self.state = 451
                self.match(GameParser.L_ANGLE)
                self.state = 452
                self.type_(0)
                self.state = 453
                self.match(GameParser.COMMA)
                self.state = 454
                self.type_(0)
                self.state = 455
                self.match(GameParser.R_ANGLE)
                pass
            elif token in [34]:
                localctx = GameParser.IntTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 457
                self.match(GameParser.INTTYPE)
                pass
            elif token in [3]:
                localctx = GameParser.ProductTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 458
                self.match(GameParser.L_SQUARE)
                self.state = 459
                self.type_(0)
                self.state = 462 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 460
                    self.match(GameParser.COMMA)
                    self.state = 461
                    self.type_(0)
                    self.state = 464 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==11):
                        break

                self.state = 466
                self.match(GameParser.R_SQUARE)
                pass
            elif token in [38]:
                localctx = GameParser.BitStringTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 468
                self.bitstring()
                pass
            elif token in [39]:
                localctx = GameParser.ModIntTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 469
                self.modint()
                pass
            elif token in [47, 56, 65]:
                localctx = GameParser.LvalueTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 470
                self.lvalue()
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 477
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,34,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = GameParser.OptionalTypeContext(self, GameParser.TypeContext(self, _parentctx, _parentState))
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_type)
                    self.state = 473
                    if not self.precpred(self._ctx, 12):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 12)")
                    self.state = 474
                    self.match(GameParser.QUESTION) 
                self.state = 479
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,34,self._ctx)

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
            return self.getTypedRuleContext(GameParser.LvalueContext,0)


        def INT(self):
            return self.getToken(GameParser.INT, 0)

        def BINARYNUM(self):
            return self.getToken(GameParser.BINARYNUM, 0)

        def L_PAREN(self):
            return self.getToken(GameParser.L_PAREN, 0)

        def integerExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.IntegerExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.IntegerExpressionContext,i)


        def R_PAREN(self):
            return self.getToken(GameParser.R_PAREN, 0)

        def TIMES(self):
            return self.getToken(GameParser.TIMES, 0)

        def DIVIDE(self):
            return self.getToken(GameParser.DIVIDE, 0)

        def PLUS(self):
            return self.getToken(GameParser.PLUS, 0)

        def SUBTRACT(self):
            return self.getToken(GameParser.SUBTRACT, 0)

        def getRuleIndex(self):
            return GameParser.RULE_integerExpression

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIntegerExpression" ):
                return visitor.visitIntegerExpression(self)
            else:
                return visitor.visitChildren(self)



    def integerExpression(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = GameParser.IntegerExpressionContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 38
        self.enterRecursionRule(localctx, 38, self.RULE_integerExpression, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 488
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [47, 56, 65]:
                self.state = 481
                self.lvalue()
                pass
            elif token in [64]:
                self.state = 482
                self.match(GameParser.INT)
                pass
            elif token in [61]:
                self.state = 483
                self.match(GameParser.BINARYNUM)
                pass
            elif token in [5]:
                self.state = 484
                self.match(GameParser.L_PAREN)
                self.state = 485
                self.integerExpression(0)
                self.state = 486
                self.match(GameParser.R_PAREN)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 504
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,37,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 502
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,36,self._ctx)
                    if la_ == 1:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 490
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 8)")
                        self.state = 491
                        self.match(GameParser.TIMES)
                        self.state = 492
                        self.integerExpression(9)
                        pass

                    elif la_ == 2:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 493
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 7)")
                        self.state = 494
                        self.match(GameParser.DIVIDE)
                        self.state = 495
                        self.integerExpression(8)
                        pass

                    elif la_ == 3:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 496
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 6)")
                        self.state = 497
                        self.match(GameParser.PLUS)
                        self.state = 498
                        self.integerExpression(7)
                        pass

                    elif la_ == 4:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 499
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 5)")
                        self.state = 500
                        self.match(GameParser.SUBTRACT)
                        self.state = 501
                        self.integerExpression(6)
                        pass

             
                self.state = 506
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,37,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class IntegerAtomContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def lvalue(self):
            return self.getTypedRuleContext(GameParser.LvalueContext,0)


        def INT(self):
            return self.getToken(GameParser.INT, 0)

        def L_PAREN(self):
            return self.getToken(GameParser.L_PAREN, 0)

        def integerExpression(self):
            return self.getTypedRuleContext(GameParser.IntegerExpressionContext,0)


        def R_PAREN(self):
            return self.getToken(GameParser.R_PAREN, 0)

        def getRuleIndex(self):
            return GameParser.RULE_integerAtom

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIntegerAtom" ):
                return visitor.visitIntegerAtom(self)
            else:
                return visitor.visitChildren(self)




    def integerAtom(self):

        localctx = GameParser.IntegerAtomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_integerAtom)
        try:
            self.state = 513
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [47, 56, 65]:
                self.enterOuterAlt(localctx, 1)
                self.state = 507
                self.lvalue()
                pass
            elif token in [64]:
                self.enterOuterAlt(localctx, 2)
                self.state = 508
                self.match(GameParser.INT)
                pass
            elif token in [5]:
                self.enterOuterAlt(localctx, 3)
                self.state = 509
                self.match(GameParser.L_PAREN)
                self.state = 510
                self.integerExpression(0)
                self.state = 511
                self.match(GameParser.R_PAREN)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class BitstringContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def BITSTRING(self):
            return self.getToken(GameParser.BITSTRING, 0)

        def L_ANGLE(self):
            return self.getToken(GameParser.L_ANGLE, 0)

        def integerExpression(self):
            return self.getTypedRuleContext(GameParser.IntegerExpressionContext,0)


        def R_ANGLE(self):
            return self.getToken(GameParser.R_ANGLE, 0)

        def getRuleIndex(self):
            return GameParser.RULE_bitstring

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBitstring" ):
                return visitor.visitBitstring(self)
            else:
                return visitor.visitChildren(self)




    def bitstring(self):

        localctx = GameParser.BitstringContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_bitstring)
        try:
            self.state = 521
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,39,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 515
                self.match(GameParser.BITSTRING)
                self.state = 516
                self.match(GameParser.L_ANGLE)
                self.state = 517
                self.integerExpression(0)
                self.state = 518
                self.match(GameParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 520
                self.match(GameParser.BITSTRING)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ModintContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def MODINT(self):
            return self.getToken(GameParser.MODINT, 0)

        def L_ANGLE(self):
            return self.getToken(GameParser.L_ANGLE, 0)

        def integerExpression(self):
            return self.getTypedRuleContext(GameParser.IntegerExpressionContext,0)


        def R_ANGLE(self):
            return self.getToken(GameParser.R_ANGLE, 0)

        def getRuleIndex(self):
            return GameParser.RULE_modint

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitModint" ):
                return visitor.visitModint(self)
            else:
                return visitor.visitChildren(self)




    def modint(self):

        localctx = GameParser.ModintContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_modint)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 523
            self.match(GameParser.MODINT)
            self.state = 524
            self.match(GameParser.L_ANGLE)
            self.state = 525
            self.integerExpression(0)
            self.state = 526
            self.match(GameParser.R_ANGLE)
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
            return self.getToken(GameParser.SET, 0)

        def L_ANGLE(self):
            return self.getToken(GameParser.L_ANGLE, 0)

        def type_(self):
            return self.getTypedRuleContext(GameParser.TypeContext,0)


        def R_ANGLE(self):
            return self.getToken(GameParser.R_ANGLE, 0)

        def getRuleIndex(self):
            return GameParser.RULE_set

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSet" ):
                return visitor.visitSet(self)
            else:
                return visitor.visitChildren(self)




    def set_(self):

        localctx = GameParser.SetContext(self, self._ctx, self.state)
        self.enterRule(localctx, 46, self.RULE_set)
        try:
            self.state = 534
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,40,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 528
                self.match(GameParser.SET)
                self.state = 529
                self.match(GameParser.L_ANGLE)
                self.state = 530
                self.type_(0)
                self.state = 531
                self.match(GameParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 533
                self.match(GameParser.SET)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class BoolContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def TRUE(self):
            return self.getToken(GameParser.TRUE, 0)

        def FALSE(self):
            return self.getToken(GameParser.FALSE, 0)

        def getRuleIndex(self):
            return GameParser.RULE_bool

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBool" ):
                return visitor.visitBool(self)
            else:
                return visitor.visitChildren(self)




    def bool_(self):

        localctx = GameParser.BoolContext(self, self._ctx, self.state)
        self.enterRule(localctx, 48, self.RULE_bool)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 536
            _la = self._input.LA(1)
            if not(_la==59 or _la==60):
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


    class ModuleImportContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IMPORT(self):
            return self.getToken(GameParser.IMPORT, 0)

        def FILESTRING(self):
            return self.getToken(GameParser.FILESTRING, 0)

        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)

        def AS(self):
            return self.getToken(GameParser.AS, 0)

        def ID(self):
            return self.getToken(GameParser.ID, 0)

        def getRuleIndex(self):
            return GameParser.RULE_moduleImport

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitModuleImport" ):
                return visitor.visitModuleImport(self)
            else:
                return visitor.visitChildren(self)




    def moduleImport(self):

        localctx = GameParser.ModuleImportContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_moduleImport)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 538
            self.match(GameParser.IMPORT)
            self.state = 539
            self.match(GameParser.FILESTRING)
            self.state = 542
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==51:
                self.state = 540
                self.match(GameParser.AS)
                self.state = 541
                self.match(GameParser.ID)


            self.state = 544
            self.match(GameParser.SEMI)
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
            return self.getToken(GameParser.ID, 0)

        def IN(self):
            return self.getToken(GameParser.IN, 0)

        def getRuleIndex(self):
            return GameParser.RULE_id

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitId" ):
                return visitor.visitId(self)
            else:
                return visitor.visitChildren(self)




    def id_(self):

        localctx = GameParser.IdContext(self, self._ctx, self.state)
        self.enterRule(localctx, 52, self.RULE_id)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 546
            _la = self._input.LA(1)
            if not(_la==47 or _la==65):
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
        self._predicates[14] = self.expression_sempred
        self._predicates[18] = self.type_sempred
        self._predicates[19] = self.integerExpression_sempred
        pred = self._predicates.get(ruleIndex, None)
        if pred is None:
            raise Exception("No predicate with index:" + str(ruleIndex))
        else:
            return pred(localctx, predIndex)

    def expression_sempred(self, localctx:ExpressionContext, predIndex:int):
            if predIndex == 0:
                return self.precpred(self._ctx, 29)
         

            if predIndex == 1:
                return self.precpred(self._ctx, 28)
         

            if predIndex == 2:
                return self.precpred(self._ctx, 27)
         

            if predIndex == 3:
                return self.precpred(self._ctx, 25)
         

            if predIndex == 4:
                return self.precpred(self._ctx, 24)
         

            if predIndex == 5:
                return self.precpred(self._ctx, 23)
         

            if predIndex == 6:
                return self.precpred(self._ctx, 22)
         

            if predIndex == 7:
                return self.precpred(self._ctx, 21)
         

            if predIndex == 8:
                return self.precpred(self._ctx, 20)
         

            if predIndex == 9:
                return self.precpred(self._ctx, 19)
         

            if predIndex == 10:
                return self.precpred(self._ctx, 18)
         

            if predIndex == 11:
                return self.precpred(self._ctx, 17)
         

            if predIndex == 12:
                return self.precpred(self._ctx, 16)
         

            if predIndex == 13:
                return self.precpred(self._ctx, 15)
         

            if predIndex == 14:
                return self.precpred(self._ctx, 14)
         

            if predIndex == 15:
                return self.precpred(self._ctx, 13)
         

            if predIndex == 16:
                return self.precpred(self._ctx, 12)
         

            if predIndex == 17:
                return self.precpred(self._ctx, 33)
         

            if predIndex == 18:
                return self.precpred(self._ctx, 32)
         

    def type_sempred(self, localctx:TypeContext, predIndex:int):
            if predIndex == 19:
                return self.precpred(self._ctx, 12)
         

    def integerExpression_sempred(self, localctx:IntegerExpressionContext, predIndex:int):
            if predIndex == 20:
                return self.precpred(self._ctx, 8)
         

            if predIndex == 21:
                return self.precpred(self._ctx, 7)
         

            if predIndex == 22:
                return self.precpred(self._ctx, 6)
         

            if predIndex == 23:
                return self.precpred(self._ctx, 5)
         




