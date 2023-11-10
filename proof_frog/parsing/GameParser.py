# Generated from proof_frog/antlr/Game.g4 by ANTLR 4.13.1
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
        4,1,56,469,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,1,0,5,0,46,8,0,10,0,12,0,49,9,0,1,0,1,0,1,0,1,0,1,
        0,1,1,1,1,1,1,1,1,1,1,1,2,1,2,1,2,1,2,3,2,65,8,2,1,2,1,2,1,2,1,2,
        1,2,1,3,1,3,1,3,5,3,75,8,3,10,3,12,3,78,9,3,1,3,4,3,81,8,3,11,3,
        12,3,82,1,3,1,3,1,3,5,3,88,8,3,10,3,12,3,91,9,3,1,3,5,3,94,8,3,10,
        3,12,3,97,9,3,1,3,4,3,100,8,3,11,3,12,3,101,3,3,104,8,3,1,4,1,4,
        1,4,4,4,109,8,4,11,4,12,4,110,1,4,1,4,1,4,1,4,1,4,1,4,5,4,119,8,
        4,10,4,12,4,122,9,4,1,4,1,4,1,4,1,4,1,5,1,5,1,5,3,5,131,8,5,1,6,
        1,6,1,6,1,6,1,7,1,7,1,7,1,8,1,8,5,8,142,8,8,10,8,12,8,145,9,8,1,
        8,1,8,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,
        9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,3,9,178,
        8,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,
        1,9,1,9,1,9,1,9,5,9,199,8,9,10,9,12,9,202,9,9,1,9,1,9,3,9,206,8,
        9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,
        9,1,9,1,9,1,9,1,9,3,9,228,8,9,1,10,1,10,1,10,1,10,1,10,1,10,1,10,
        5,10,237,8,10,10,10,12,10,240,9,10,1,11,1,11,1,11,1,11,3,11,246,
        8,11,1,11,1,11,1,12,1,12,1,12,5,12,253,8,12,10,12,12,12,256,9,12,
        1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,5,13,
        270,8,13,10,13,12,13,273,9,13,3,13,275,8,13,1,13,1,13,1,13,1,13,
        1,13,5,13,282,8,13,10,13,12,13,285,9,13,3,13,287,8,13,1,13,1,13,
        1,13,1,13,1,13,1,13,1,13,1,13,1,13,3,13,298,8,13,1,13,1,13,1,13,
        1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,
        1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,
        1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,
        1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,3,13,351,8,13,1,13,
        1,13,1,13,1,13,1,13,1,13,1,13,1,13,5,13,361,8,13,10,13,12,13,364,
        9,13,1,14,1,14,1,14,5,14,369,8,14,10,14,12,14,372,9,14,1,15,1,15,
        1,15,1,16,1,16,1,16,1,16,1,16,1,16,1,16,1,16,1,16,1,16,1,16,1,16,
        1,16,1,16,1,16,1,16,1,16,1,16,1,16,1,16,1,16,5,16,398,8,16,10,16,
        12,16,401,9,16,1,16,3,16,404,8,16,1,16,1,16,1,16,1,16,1,16,4,16,
        411,8,16,11,16,12,16,412,5,16,415,8,16,10,16,12,16,418,9,16,1,17,
        1,17,1,17,1,17,3,17,424,8,17,1,17,1,17,1,17,1,17,1,17,1,17,1,17,
        1,17,1,17,1,17,1,17,1,17,5,17,438,8,17,10,17,12,17,441,9,17,1,18,
        1,18,1,18,1,18,1,18,1,18,3,18,449,8,18,1,19,1,19,1,19,1,19,1,19,
        1,19,3,19,457,8,19,1,20,1,20,1,20,1,20,3,20,463,8,20,1,20,1,20,1,
        21,1,21,1,21,0,3,26,32,34,22,0,2,4,6,8,10,12,14,16,18,20,22,24,26,
        28,30,32,34,36,38,40,42,0,1,2,0,42,42,53,53,526,0,47,1,0,0,0,2,55,
        1,0,0,0,4,60,1,0,0,0,6,103,1,0,0,0,8,105,1,0,0,0,10,127,1,0,0,0,
        12,132,1,0,0,0,14,136,1,0,0,0,16,139,1,0,0,0,18,227,1,0,0,0,20,229,
        1,0,0,0,22,241,1,0,0,0,24,249,1,0,0,0,26,297,1,0,0,0,28,365,1,0,
        0,0,30,373,1,0,0,0,32,403,1,0,0,0,34,423,1,0,0,0,36,448,1,0,0,0,
        38,456,1,0,0,0,40,458,1,0,0,0,42,466,1,0,0,0,44,46,3,40,20,0,45,
        44,1,0,0,0,46,49,1,0,0,0,47,45,1,0,0,0,47,48,1,0,0,0,48,50,1,0,0,
        0,49,47,1,0,0,0,50,51,3,4,2,0,51,52,3,4,2,0,52,53,3,2,1,0,53,54,
        5,0,0,1,54,1,1,0,0,0,55,56,5,45,0,0,56,57,5,46,0,0,57,58,5,53,0,
        0,58,59,5,9,0,0,59,3,1,0,0,0,60,61,5,44,0,0,61,62,5,53,0,0,62,64,
        5,5,0,0,63,65,3,24,12,0,64,63,1,0,0,0,64,65,1,0,0,0,65,66,1,0,0,
        0,66,67,5,6,0,0,67,68,5,1,0,0,68,69,3,6,3,0,69,70,5,2,0,0,70,5,1,
        0,0,0,71,72,3,10,5,0,72,73,5,9,0,0,73,75,1,0,0,0,74,71,1,0,0,0,75,
        78,1,0,0,0,76,74,1,0,0,0,76,77,1,0,0,0,77,80,1,0,0,0,78,76,1,0,0,
        0,79,81,3,14,7,0,80,79,1,0,0,0,81,82,1,0,0,0,82,80,1,0,0,0,82,83,
        1,0,0,0,83,104,1,0,0,0,84,85,3,10,5,0,85,86,5,9,0,0,86,88,1,0,0,
        0,87,84,1,0,0,0,88,91,1,0,0,0,89,87,1,0,0,0,89,90,1,0,0,0,90,95,
        1,0,0,0,91,89,1,0,0,0,92,94,3,14,7,0,93,92,1,0,0,0,94,97,1,0,0,0,
        95,93,1,0,0,0,95,96,1,0,0,0,96,99,1,0,0,0,97,95,1,0,0,0,98,100,3,
        8,4,0,99,98,1,0,0,0,100,101,1,0,0,0,101,99,1,0,0,0,101,102,1,0,0,
        0,102,104,1,0,0,0,103,76,1,0,0,0,103,89,1,0,0,0,104,7,1,0,0,0,105,
        106,5,47,0,0,106,108,5,1,0,0,107,109,3,14,7,0,108,107,1,0,0,0,109,
        110,1,0,0,0,110,108,1,0,0,0,110,111,1,0,0,0,111,112,1,0,0,0,112,
        113,5,48,0,0,113,114,5,10,0,0,114,115,5,3,0,0,115,120,3,42,21,0,
        116,117,5,11,0,0,117,119,3,42,21,0,118,116,1,0,0,0,119,122,1,0,0,
        0,120,118,1,0,0,0,120,121,1,0,0,0,121,123,1,0,0,0,122,120,1,0,0,
        0,123,124,5,4,0,0,124,125,5,9,0,0,125,126,5,2,0,0,126,9,1,0,0,0,
        127,130,3,30,15,0,128,129,5,14,0,0,129,131,3,26,13,0,130,128,1,0,
        0,0,130,131,1,0,0,0,131,11,1,0,0,0,132,133,3,30,15,0,133,134,5,14,
        0,0,134,135,3,26,13,0,135,13,1,0,0,0,136,137,3,22,11,0,137,138,3,
        16,8,0,138,15,1,0,0,0,139,143,5,1,0,0,140,142,3,18,9,0,141,140,1,
        0,0,0,142,145,1,0,0,0,143,141,1,0,0,0,143,144,1,0,0,0,144,146,1,
        0,0,0,145,143,1,0,0,0,146,147,5,2,0,0,147,17,1,0,0,0,148,149,3,32,
        16,0,149,150,3,42,21,0,150,151,5,9,0,0,151,228,1,0,0,0,152,153,3,
        32,16,0,153,154,3,20,10,0,154,155,5,14,0,0,155,156,3,26,13,0,156,
        157,5,9,0,0,157,228,1,0,0,0,158,159,3,32,16,0,159,160,3,20,10,0,
        160,161,5,24,0,0,161,162,3,26,13,0,162,163,5,9,0,0,163,228,1,0,0,
        0,164,165,3,20,10,0,165,166,5,14,0,0,166,167,3,26,13,0,167,168,5,
        9,0,0,168,228,1,0,0,0,169,170,3,20,10,0,170,171,5,24,0,0,171,172,
        3,26,13,0,172,173,5,9,0,0,173,228,1,0,0,0,174,175,3,26,13,0,175,
        177,5,5,0,0,176,178,3,28,14,0,177,176,1,0,0,0,177,178,1,0,0,0,178,
        179,1,0,0,0,179,180,5,6,0,0,180,181,5,9,0,0,181,228,1,0,0,0,182,
        183,5,33,0,0,183,184,3,26,13,0,184,185,5,9,0,0,185,228,1,0,0,0,186,
        187,5,39,0,0,187,188,5,5,0,0,188,189,3,26,13,0,189,190,5,6,0,0,190,
        200,3,16,8,0,191,192,5,49,0,0,192,193,5,39,0,0,193,194,5,5,0,0,194,
        195,3,26,13,0,195,196,5,6,0,0,196,197,3,16,8,0,197,199,1,0,0,0,198,
        191,1,0,0,0,199,202,1,0,0,0,200,198,1,0,0,0,200,201,1,0,0,0,201,
        205,1,0,0,0,202,200,1,0,0,0,203,204,5,49,0,0,204,206,3,16,8,0,205,
        203,1,0,0,0,205,206,1,0,0,0,206,228,1,0,0,0,207,208,5,40,0,0,208,
        209,5,5,0,0,209,210,5,31,0,0,210,211,3,42,21,0,211,212,5,14,0,0,
        212,213,3,26,13,0,213,214,5,41,0,0,214,215,3,26,13,0,215,216,5,6,
        0,0,216,217,3,16,8,0,217,228,1,0,0,0,218,219,5,40,0,0,219,220,5,
        5,0,0,220,221,3,32,16,0,221,222,3,42,21,0,222,223,5,42,0,0,223,224,
        3,26,13,0,224,225,5,6,0,0,225,226,3,16,8,0,226,228,1,0,0,0,227,148,
        1,0,0,0,227,152,1,0,0,0,227,158,1,0,0,0,227,164,1,0,0,0,227,169,
        1,0,0,0,227,174,1,0,0,0,227,182,1,0,0,0,227,186,1,0,0,0,227,207,
        1,0,0,0,227,218,1,0,0,0,228,19,1,0,0,0,229,238,3,42,21,0,230,231,
        5,12,0,0,231,237,3,42,21,0,232,233,5,3,0,0,233,234,3,34,17,0,234,
        235,5,4,0,0,235,237,1,0,0,0,236,230,1,0,0,0,236,232,1,0,0,0,237,
        240,1,0,0,0,238,236,1,0,0,0,238,239,1,0,0,0,239,21,1,0,0,0,240,238,
        1,0,0,0,241,242,3,32,16,0,242,243,3,42,21,0,243,245,5,5,0,0,244,
        246,3,24,12,0,245,244,1,0,0,0,245,246,1,0,0,0,246,247,1,0,0,0,247,
        248,5,6,0,0,248,23,1,0,0,0,249,254,3,30,15,0,250,251,5,11,0,0,251,
        253,3,30,15,0,252,250,1,0,0,0,253,256,1,0,0,0,254,252,1,0,0,0,254,
        255,1,0,0,0,255,25,1,0,0,0,256,254,1,0,0,0,257,258,6,13,-1,0,258,
        298,3,20,10,0,259,260,5,27,0,0,260,298,3,26,13,11,261,262,5,28,0,
        0,262,263,3,26,13,0,263,264,5,28,0,0,264,298,1,0,0,0,265,274,5,3,
        0,0,266,271,3,26,13,0,267,268,5,11,0,0,268,270,3,26,13,0,269,267,
        1,0,0,0,270,273,1,0,0,0,271,269,1,0,0,0,271,272,1,0,0,0,272,275,
        1,0,0,0,273,271,1,0,0,0,274,266,1,0,0,0,274,275,1,0,0,0,275,276,
        1,0,0,0,276,298,5,4,0,0,277,286,5,1,0,0,278,283,3,26,13,0,279,280,
        5,11,0,0,280,282,3,26,13,0,281,279,1,0,0,0,282,285,1,0,0,0,283,281,
        1,0,0,0,283,284,1,0,0,0,284,287,1,0,0,0,285,283,1,0,0,0,286,278,
        1,0,0,0,286,287,1,0,0,0,287,288,1,0,0,0,288,298,5,2,0,0,289,298,
        3,32,16,0,290,298,5,51,0,0,291,298,5,52,0,0,292,298,5,50,0,0,293,
        294,5,5,0,0,294,295,3,26,13,0,295,296,5,6,0,0,296,298,1,0,0,0,297,
        257,1,0,0,0,297,259,1,0,0,0,297,261,1,0,0,0,297,265,1,0,0,0,297,
        277,1,0,0,0,297,289,1,0,0,0,297,290,1,0,0,0,297,291,1,0,0,0,297,
        292,1,0,0,0,297,293,1,0,0,0,298,362,1,0,0,0,299,300,10,28,0,0,300,
        301,5,19,0,0,301,361,3,26,13,29,302,303,10,27,0,0,303,304,5,20,0,
        0,304,361,3,26,13,28,305,306,10,26,0,0,306,307,5,8,0,0,307,361,3,
        26,13,27,308,309,10,25,0,0,309,310,5,7,0,0,310,361,3,26,13,26,311,
        312,10,24,0,0,312,313,5,21,0,0,313,361,3,26,13,25,314,315,10,23,
        0,0,315,316,5,22,0,0,316,361,3,26,13,24,317,318,10,22,0,0,318,319,
        5,25,0,0,319,361,3,26,13,23,320,321,10,21,0,0,321,322,5,38,0,0,322,
        361,3,26,13,22,323,324,10,20,0,0,324,325,5,42,0,0,325,361,3,26,13,
        21,326,327,10,19,0,0,327,328,5,23,0,0,328,361,3,26,13,20,329,330,
        10,18,0,0,330,331,5,43,0,0,331,361,3,26,13,19,332,333,10,17,0,0,
        333,334,5,26,0,0,334,361,3,26,13,18,335,336,10,16,0,0,336,337,5,
        15,0,0,337,361,3,26,13,17,338,339,10,15,0,0,339,340,5,16,0,0,340,
        361,3,26,13,16,341,342,10,14,0,0,342,343,5,13,0,0,343,361,3,26,13,
        15,344,345,10,13,0,0,345,346,5,17,0,0,346,361,3,26,13,14,347,348,
        10,9,0,0,348,350,5,5,0,0,349,351,3,28,14,0,350,349,1,0,0,0,350,351,
        1,0,0,0,351,352,1,0,0,0,352,361,5,6,0,0,353,354,10,8,0,0,354,355,
        5,3,0,0,355,356,3,34,17,0,356,357,5,10,0,0,357,358,3,34,17,0,358,
        359,5,4,0,0,359,361,1,0,0,0,360,299,1,0,0,0,360,302,1,0,0,0,360,
        305,1,0,0,0,360,308,1,0,0,0,360,311,1,0,0,0,360,314,1,0,0,0,360,
        317,1,0,0,0,360,320,1,0,0,0,360,323,1,0,0,0,360,326,1,0,0,0,360,
        329,1,0,0,0,360,332,1,0,0,0,360,335,1,0,0,0,360,338,1,0,0,0,360,
        341,1,0,0,0,360,344,1,0,0,0,360,347,1,0,0,0,360,353,1,0,0,0,361,
        364,1,0,0,0,362,360,1,0,0,0,362,363,1,0,0,0,363,27,1,0,0,0,364,362,
        1,0,0,0,365,370,3,26,13,0,366,367,5,11,0,0,367,369,3,26,13,0,368,
        366,1,0,0,0,369,372,1,0,0,0,370,368,1,0,0,0,370,371,1,0,0,0,371,
        29,1,0,0,0,372,370,1,0,0,0,373,374,3,32,16,0,374,375,3,42,21,0,375,
        31,1,0,0,0,376,377,6,16,-1,0,377,404,3,38,19,0,378,404,5,30,0,0,
        379,380,5,32,0,0,380,381,5,7,0,0,381,382,3,32,16,0,382,383,5,11,
        0,0,383,384,3,32,16,0,384,385,5,8,0,0,385,404,1,0,0,0,386,387,5,
        36,0,0,387,388,5,7,0,0,388,389,3,32,16,0,389,390,5,11,0,0,390,391,
        3,34,17,0,391,392,5,8,0,0,392,404,1,0,0,0,393,404,5,31,0,0,394,399,
        3,42,21,0,395,396,5,12,0,0,396,398,3,42,21,0,397,395,1,0,0,0,398,
        401,1,0,0,0,399,397,1,0,0,0,399,400,1,0,0,0,400,404,1,0,0,0,401,
        399,1,0,0,0,402,404,3,36,18,0,403,376,1,0,0,0,403,378,1,0,0,0,403,
        379,1,0,0,0,403,386,1,0,0,0,403,393,1,0,0,0,403,394,1,0,0,0,403,
        402,1,0,0,0,404,416,1,0,0,0,405,406,10,9,0,0,406,415,5,18,0,0,407,
        410,10,3,0,0,408,409,5,13,0,0,409,411,3,32,16,0,410,408,1,0,0,0,
        411,412,1,0,0,0,412,410,1,0,0,0,412,413,1,0,0,0,413,415,1,0,0,0,
        414,405,1,0,0,0,414,407,1,0,0,0,415,418,1,0,0,0,416,414,1,0,0,0,
        416,417,1,0,0,0,417,33,1,0,0,0,418,416,1,0,0,0,419,420,6,17,-1,0,
        420,424,3,20,10,0,421,424,5,51,0,0,422,424,5,52,0,0,423,419,1,0,
        0,0,423,421,1,0,0,0,423,422,1,0,0,0,424,439,1,0,0,0,425,426,10,4,
        0,0,426,427,5,15,0,0,427,438,3,34,17,5,428,429,10,3,0,0,429,430,
        5,13,0,0,430,438,3,34,17,4,431,432,10,2,0,0,432,433,5,16,0,0,433,
        438,3,34,17,3,434,435,10,1,0,0,435,436,5,17,0,0,436,438,3,34,17,
        2,437,425,1,0,0,0,437,428,1,0,0,0,437,431,1,0,0,0,437,434,1,0,0,
        0,438,441,1,0,0,0,439,437,1,0,0,0,439,440,1,0,0,0,440,35,1,0,0,0,
        441,439,1,0,0,0,442,449,5,35,0,0,443,444,5,35,0,0,444,445,5,7,0,
        0,445,446,3,34,17,0,446,447,5,8,0,0,447,449,1,0,0,0,448,442,1,0,
        0,0,448,443,1,0,0,0,449,37,1,0,0,0,450,451,5,29,0,0,451,452,5,7,
        0,0,452,453,3,32,16,0,453,454,5,8,0,0,454,457,1,0,0,0,455,457,5,
        29,0,0,456,450,1,0,0,0,456,455,1,0,0,0,457,39,1,0,0,0,458,459,5,
        34,0,0,459,462,5,56,0,0,460,461,5,46,0,0,461,463,5,53,0,0,462,460,
        1,0,0,0,462,463,1,0,0,0,463,464,1,0,0,0,464,465,5,9,0,0,465,41,1,
        0,0,0,466,467,7,0,0,0,467,43,1,0,0,0,40,47,64,76,82,89,95,101,103,
        110,120,130,143,177,200,205,227,236,238,245,254,271,274,283,286,
        297,350,360,362,370,399,403,412,414,416,423,437,439,448,456,462
    ]

class GameParser ( Parser ):

    grammarFileName = "Game.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'{'", "'}'", "'['", "']'", "'('", "')'", 
                     "'<'", "'>'", "';'", "':'", "','", "'.'", "'*'", "'='", 
                     "'+'", "'-'", "'/'", "'?'", "'=='", "'!='", "'>='", 
                     "'<='", "'||'", "'<-'", "'&&'", "'\\'", "'!'", "'|'", 
                     "'Set'", "'Bool'", "'Int'", "'Map'", "'return'", "'import'", 
                     "'BitString'", "'Array'", "'Primitive'", "'subsets'", 
                     "'if'", "'for'", "'to'", "'in'", "'union'", "'Game'", 
                     "'export'", "'as'", "'Phase'", "'oracles'", "'else'", 
                     "'None'" ]

    symbolicNames = [ "<INVALID>", "L_CURLY", "R_CURLY", "L_SQUARE", "R_SQUARE", 
                      "L_PAREN", "R_PAREN", "L_ANGLE", "R_ANGLE", "SEMI", 
                      "COLON", "COMMA", "PERIOD", "TIMES", "EQUALS", "PLUS", 
                      "SUBTRACT", "DIVIDE", "QUESTION", "EQUALSCOMPARE", 
                      "NOTEQUALS", "GEQ", "LEQ", "OR", "SAMPLES", "AND", 
                      "BACKSLASH", "NOT", "VBAR", "SET", "BOOL", "INTTYPE", 
                      "MAP", "RETURN", "IMPORT", "BITSTRING", "ARRAY", "PRIMITIVE", 
                      "SUBSETS", "IF", "FOR", "TO", "IN", "UNION", "GAME", 
                      "EXPORT", "AS", "PHASE", "ORACLES", "ELSE", "NONE", 
                      "BINARYNUM", "INT", "ID", "WS", "LINE_COMMENT", "FILESTRING" ]

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
    RULE_methodSignature = 11
    RULE_paramList = 12
    RULE_expression = 13
    RULE_argList = 14
    RULE_variable = 15
    RULE_type = 16
    RULE_integerExpression = 17
    RULE_bitstring = 18
    RULE_set = 19
    RULE_moduleImport = 20
    RULE_id = 21

    ruleNames =  [ "program", "gameExport", "game", "gameBody", "gamePhase", 
                   "field", "initializedField", "method", "block", "statement", 
                   "lvalue", "methodSignature", "paramList", "expression", 
                   "argList", "variable", "type", "integerExpression", "bitstring", 
                   "set", "moduleImport", "id" ]

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
    SAMPLES=24
    AND=25
    BACKSLASH=26
    NOT=27
    VBAR=28
    SET=29
    BOOL=30
    INTTYPE=31
    MAP=32
    RETURN=33
    IMPORT=34
    BITSTRING=35
    ARRAY=36
    PRIMITIVE=37
    SUBSETS=38
    IF=39
    FOR=40
    TO=41
    IN=42
    UNION=43
    GAME=44
    EXPORT=45
    AS=46
    PHASE=47
    ORACLES=48
    ELSE=49
    NONE=50
    BINARYNUM=51
    INT=52
    ID=53
    WS=54
    LINE_COMMENT=55
    FILESTRING=56

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
            self.state = 47
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==34:
                self.state = 44
                self.moduleImport()
                self.state = 49
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 50
            self.game()
            self.state = 51
            self.game()
            self.state = 52
            self.gameExport()
            self.state = 53
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
            self.state = 55
            self.match(GameParser.EXPORT)
            self.state = 56
            self.match(GameParser.AS)
            self.state = 57
            self.match(GameParser.ID)
            self.state = 58
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
            self.state = 60
            self.match(GameParser.GAME)
            self.state = 61
            self.match(GameParser.ID)
            self.state = 62
            self.match(GameParser.L_PAREN)
            self.state = 64
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 9011708433530880) != 0):
                self.state = 63
                self.paramList()


            self.state = 66
            self.match(GameParser.R_PAREN)
            self.state = 67
            self.match(GameParser.L_CURLY)
            self.state = 68
            self.gameBody()
            self.state = 69
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
            self.state = 103
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,7,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 76
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,2,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 71
                        self.field()
                        self.state = 72
                        self.match(GameParser.SEMI) 
                    self.state = 78
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,2,self._ctx)

                self.state = 80 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 79
                    self.method()
                    self.state = 82 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 9011708433530880) != 0)):
                        break

                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 89
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,4,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 84
                        self.field()
                        self.state = 85
                        self.match(GameParser.SEMI) 
                    self.state = 91
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,4,self._ctx)

                self.state = 95
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while (((_la) & ~0x3f) == 0 and ((1 << _la) & 9011708433530880) != 0):
                    self.state = 92
                    self.method()
                    self.state = 97
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 99 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 98
                    self.gamePhase()
                    self.state = 101 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==47):
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
            self.state = 105
            self.match(GameParser.PHASE)
            self.state = 106
            self.match(GameParser.L_CURLY)
            self.state = 108 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 107
                self.method()
                self.state = 110 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 9011708433530880) != 0)):
                    break

            self.state = 112
            self.match(GameParser.ORACLES)
            self.state = 113
            self.match(GameParser.COLON)
            self.state = 114
            self.match(GameParser.L_SQUARE)
            self.state = 115
            self.id_()
            self.state = 120
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==11:
                self.state = 116
                self.match(GameParser.COMMA)
                self.state = 117
                self.id_()
                self.state = 122
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 123
            self.match(GameParser.R_SQUARE)
            self.state = 124
            self.match(GameParser.SEMI)
            self.state = 125
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
            self.state = 127
            self.variable()
            self.state = 130
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==14:
                self.state = 128
                self.match(GameParser.EQUALS)
                self.state = 129
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
            self.state = 132
            self.variable()
            self.state = 133
            self.match(GameParser.EQUALS)
            self.state = 134
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
            self.state = 136
            self.methodSignature()
            self.state = 137
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
            self.state = 139
            self.match(GameParser.L_CURLY)
            self.state = 143
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 16894666041458730) != 0):
                self.state = 140
                self.statement()
                self.state = 145
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 146
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
            self.state = 227
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,15,self._ctx)
            if la_ == 1:
                localctx = GameParser.VarDeclStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 148
                self.type_(0)
                self.state = 149
                self.id_()
                self.state = 150
                self.match(GameParser.SEMI)
                pass

            elif la_ == 2:
                localctx = GameParser.VarDeclWithValueStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 152
                self.type_(0)
                self.state = 153
                self.lvalue()
                self.state = 154
                self.match(GameParser.EQUALS)
                self.state = 155
                self.expression(0)
                self.state = 156
                self.match(GameParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GameParser.VarDeclWithSampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 158
                self.type_(0)
                self.state = 159
                self.lvalue()
                self.state = 160
                self.match(GameParser.SAMPLES)
                self.state = 161
                self.expression(0)
                self.state = 162
                self.match(GameParser.SEMI)
                pass

            elif la_ == 4:
                localctx = GameParser.AssignmentStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 164
                self.lvalue()
                self.state = 165
                self.match(GameParser.EQUALS)
                self.state = 166
                self.expression(0)
                self.state = 167
                self.match(GameParser.SEMI)
                pass

            elif la_ == 5:
                localctx = GameParser.SampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 5)
                self.state = 169
                self.lvalue()
                self.state = 170
                self.match(GameParser.SAMPLES)
                self.state = 171
                self.expression(0)
                self.state = 172
                self.match(GameParser.SEMI)
                pass

            elif la_ == 6:
                localctx = GameParser.FunctionCallStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 6)
                self.state = 174
                self.expression(0)
                self.state = 175
                self.match(GameParser.L_PAREN)
                self.state = 177
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 16893008184082474) != 0):
                    self.state = 176
                    self.argList()


                self.state = 179
                self.match(GameParser.R_PAREN)
                self.state = 180
                self.match(GameParser.SEMI)
                pass

            elif la_ == 7:
                localctx = GameParser.ReturnStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 7)
                self.state = 182
                self.match(GameParser.RETURN)
                self.state = 183
                self.expression(0)
                self.state = 184
                self.match(GameParser.SEMI)
                pass

            elif la_ == 8:
                localctx = GameParser.IfStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 8)
                self.state = 186
                self.match(GameParser.IF)
                self.state = 187
                self.match(GameParser.L_PAREN)
                self.state = 188
                self.expression(0)
                self.state = 189
                self.match(GameParser.R_PAREN)
                self.state = 190
                self.block()
                self.state = 200
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,13,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 191
                        self.match(GameParser.ELSE)
                        self.state = 192
                        self.match(GameParser.IF)
                        self.state = 193
                        self.match(GameParser.L_PAREN)
                        self.state = 194
                        self.expression(0)
                        self.state = 195
                        self.match(GameParser.R_PAREN)
                        self.state = 196
                        self.block() 
                    self.state = 202
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,13,self._ctx)

                self.state = 205
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==49:
                    self.state = 203
                    self.match(GameParser.ELSE)
                    self.state = 204
                    self.block()


                pass

            elif la_ == 9:
                localctx = GameParser.NumericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 9)
                self.state = 207
                self.match(GameParser.FOR)
                self.state = 208
                self.match(GameParser.L_PAREN)
                self.state = 209
                self.match(GameParser.INTTYPE)
                self.state = 210
                self.id_()
                self.state = 211
                self.match(GameParser.EQUALS)
                self.state = 212
                self.expression(0)
                self.state = 213
                self.match(GameParser.TO)
                self.state = 214
                self.expression(0)
                self.state = 215
                self.match(GameParser.R_PAREN)
                self.state = 216
                self.block()
                pass

            elif la_ == 10:
                localctx = GameParser.GenericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 10)
                self.state = 218
                self.match(GameParser.FOR)
                self.state = 219
                self.match(GameParser.L_PAREN)
                self.state = 220
                self.type_(0)
                self.state = 221
                self.id_()
                self.state = 222
                self.match(GameParser.IN)
                self.state = 223
                self.expression(0)
                self.state = 224
                self.match(GameParser.R_PAREN)
                self.state = 225
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

        def integerExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.IntegerExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.IntegerExpressionContext,i)


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
            self.state = 229
            self.id_()
            self.state = 238
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,17,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 236
                    self._errHandler.sync(self)
                    token = self._input.LA(1)
                    if token in [12]:
                        self.state = 230
                        self.match(GameParser.PERIOD)
                        self.state = 231
                        self.id_()
                        pass
                    elif token in [3]:
                        self.state = 232
                        self.match(GameParser.L_SQUARE)
                        self.state = 233
                        self.integerExpression(0)
                        self.state = 234
                        self.match(GameParser.R_SQUARE)
                        pass
                    else:
                        raise NoViableAltException(self)
             
                self.state = 240
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,17,self._ctx)

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
        self.enterRule(localctx, 22, self.RULE_methodSignature)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 241
            self.type_(0)
            self.state = 242
            self.id_()
            self.state = 243
            self.match(GameParser.L_PAREN)
            self.state = 245
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 9011708433530880) != 0):
                self.state = 244
                self.paramList()


            self.state = 247
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
        self.enterRule(localctx, 24, self.RULE_paramList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 249
            self.variable()
            self.state = 254
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==11:
                self.state = 250
                self.match(GameParser.COMMA)
                self.state = 251
                self.variable()
                self.state = 256
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
        _startState = 26
        self.enterRecursionRule(localctx, 26, self.RULE_expression, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 297
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,24,self._ctx)
            if la_ == 1:
                localctx = GameParser.LvalueExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 258
                self.lvalue()
                pass

            elif la_ == 2:
                localctx = GameParser.NotExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 259
                self.match(GameParser.NOT)
                self.state = 260
                self.expression(11)
                pass

            elif la_ == 3:
                localctx = GameParser.SizeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 261
                self.match(GameParser.VBAR)
                self.state = 262
                self.expression(0)
                self.state = 263
                self.match(GameParser.VBAR)
                pass

            elif la_ == 4:
                localctx = GameParser.CreateTupleExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 265
                self.match(GameParser.L_SQUARE)
                self.state = 274
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 16893008184082474) != 0):
                    self.state = 266
                    self.expression(0)
                    self.state = 271
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==11:
                        self.state = 267
                        self.match(GameParser.COMMA)
                        self.state = 268
                        self.expression(0)
                        self.state = 273
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 276
                self.match(GameParser.R_SQUARE)
                pass

            elif la_ == 5:
                localctx = GameParser.CreateSetExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 277
                self.match(GameParser.L_CURLY)
                self.state = 286
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 16893008184082474) != 0):
                    self.state = 278
                    self.expression(0)
                    self.state = 283
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==11:
                        self.state = 279
                        self.match(GameParser.COMMA)
                        self.state = 280
                        self.expression(0)
                        self.state = 285
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 288
                self.match(GameParser.R_CURLY)
                pass

            elif la_ == 6:
                localctx = GameParser.TypeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 289
                self.type_(0)
                pass

            elif la_ == 7:
                localctx = GameParser.BinaryNumExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 290
                self.match(GameParser.BINARYNUM)
                pass

            elif la_ == 8:
                localctx = GameParser.IntExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 291
                self.match(GameParser.INT)
                pass

            elif la_ == 9:
                localctx = GameParser.NoneExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 292
                self.match(GameParser.NONE)
                pass

            elif la_ == 10:
                localctx = GameParser.ParenExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 293
                self.match(GameParser.L_PAREN)
                self.state = 294
                self.expression(0)
                self.state = 295
                self.match(GameParser.R_PAREN)
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 362
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,27,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 360
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,26,self._ctx)
                    if la_ == 1:
                        localctx = GameParser.EqualsExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 299
                        if not self.precpred(self._ctx, 28):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 28)")
                        self.state = 300
                        self.match(GameParser.EQUALSCOMPARE)
                        self.state = 301
                        self.expression(29)
                        pass

                    elif la_ == 2:
                        localctx = GameParser.NotEqualsExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 302
                        if not self.precpred(self._ctx, 27):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 27)")
                        self.state = 303
                        self.match(GameParser.NOTEQUALS)
                        self.state = 304
                        self.expression(28)
                        pass

                    elif la_ == 3:
                        localctx = GameParser.GtExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 305
                        if not self.precpred(self._ctx, 26):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 26)")
                        self.state = 306
                        self.match(GameParser.R_ANGLE)
                        self.state = 307
                        self.expression(27)
                        pass

                    elif la_ == 4:
                        localctx = GameParser.LtExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 308
                        if not self.precpred(self._ctx, 25):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 25)")
                        self.state = 309
                        self.match(GameParser.L_ANGLE)
                        self.state = 310
                        self.expression(26)
                        pass

                    elif la_ == 5:
                        localctx = GameParser.GeqExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 311
                        if not self.precpred(self._ctx, 24):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 24)")
                        self.state = 312
                        self.match(GameParser.GEQ)
                        self.state = 313
                        self.expression(25)
                        pass

                    elif la_ == 6:
                        localctx = GameParser.LeqExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 314
                        if not self.precpred(self._ctx, 23):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 23)")
                        self.state = 315
                        self.match(GameParser.LEQ)
                        self.state = 316
                        self.expression(24)
                        pass

                    elif la_ == 7:
                        localctx = GameParser.AndExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 317
                        if not self.precpred(self._ctx, 22):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 22)")
                        self.state = 318
                        self.match(GameParser.AND)
                        self.state = 319
                        self.expression(23)
                        pass

                    elif la_ == 8:
                        localctx = GameParser.SubsetsExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 320
                        if not self.precpred(self._ctx, 21):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 21)")
                        self.state = 321
                        self.match(GameParser.SUBSETS)
                        self.state = 322
                        self.expression(22)
                        pass

                    elif la_ == 9:
                        localctx = GameParser.InExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 323
                        if not self.precpred(self._ctx, 20):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 20)")
                        self.state = 324
                        self.match(GameParser.IN)
                        self.state = 325
                        self.expression(21)
                        pass

                    elif la_ == 10:
                        localctx = GameParser.OrExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 326
                        if not self.precpred(self._ctx, 19):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 19)")
                        self.state = 327
                        self.match(GameParser.OR)
                        self.state = 328
                        self.expression(20)
                        pass

                    elif la_ == 11:
                        localctx = GameParser.UnionExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 329
                        if not self.precpred(self._ctx, 18):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 18)")
                        self.state = 330
                        self.match(GameParser.UNION)
                        self.state = 331
                        self.expression(19)
                        pass

                    elif la_ == 12:
                        localctx = GameParser.SetMinusExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 332
                        if not self.precpred(self._ctx, 17):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 17)")
                        self.state = 333
                        self.match(GameParser.BACKSLASH)
                        self.state = 334
                        self.expression(18)
                        pass

                    elif la_ == 13:
                        localctx = GameParser.AddExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 335
                        if not self.precpred(self._ctx, 16):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 16)")
                        self.state = 336
                        self.match(GameParser.PLUS)
                        self.state = 337
                        self.expression(17)
                        pass

                    elif la_ == 14:
                        localctx = GameParser.SubtractExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 338
                        if not self.precpred(self._ctx, 15):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 15)")
                        self.state = 339
                        self.match(GameParser.SUBTRACT)
                        self.state = 340
                        self.expression(16)
                        pass

                    elif la_ == 15:
                        localctx = GameParser.MultiplyExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 341
                        if not self.precpred(self._ctx, 14):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 14)")
                        self.state = 342
                        self.match(GameParser.TIMES)
                        self.state = 343
                        self.expression(15)
                        pass

                    elif la_ == 16:
                        localctx = GameParser.DivideExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 344
                        if not self.precpred(self._ctx, 13):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 13)")
                        self.state = 345
                        self.match(GameParser.DIVIDE)
                        self.state = 346
                        self.expression(14)
                        pass

                    elif la_ == 17:
                        localctx = GameParser.FnCallExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 347
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 9)")
                        self.state = 348
                        self.match(GameParser.L_PAREN)
                        self.state = 350
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)
                        if (((_la) & ~0x3f) == 0 and ((1 << _la) & 16893008184082474) != 0):
                            self.state = 349
                            self.argList()


                        self.state = 352
                        self.match(GameParser.R_PAREN)
                        pass

                    elif la_ == 18:
                        localctx = GameParser.SliceExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 353
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 8)")
                        self.state = 354
                        self.match(GameParser.L_SQUARE)
                        self.state = 355
                        self.integerExpression(0)
                        self.state = 356
                        self.match(GameParser.COLON)
                        self.state = 357
                        self.integerExpression(0)
                        self.state = 358
                        self.match(GameParser.R_SQUARE)
                        pass

             
                self.state = 364
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,27,self._ctx)

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
        self.enterRule(localctx, 28, self.RULE_argList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 365
            self.expression(0)
            self.state = 370
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==11:
                self.state = 366
                self.match(GameParser.COMMA)
                self.state = 367
                self.expression(0)
                self.state = 372
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
        self.enterRule(localctx, 30, self.RULE_variable)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 373
            self.type_(0)
            self.state = 374
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


    class UserTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def id_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.IdContext)
            else:
                return self.getTypedRuleContext(GameParser.IdContext,i)

        def PERIOD(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.PERIOD)
            else:
                return self.getToken(GameParser.PERIOD, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitUserType" ):
                return visitor.visitUserType(self)
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

        def type_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.TypeContext)
            else:
                return self.getTypedRuleContext(GameParser.TypeContext,i)

        def TIMES(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.TIMES)
            else:
                return self.getToken(GameParser.TIMES, i)

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
        _startState = 32
        self.enterRecursionRule(localctx, 32, self.RULE_type, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 403
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [29]:
                localctx = GameParser.SetTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 377
                self.set_()
                pass
            elif token in [30]:
                localctx = GameParser.BoolTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 378
                self.match(GameParser.BOOL)
                pass
            elif token in [32]:
                localctx = GameParser.MapTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 379
                self.match(GameParser.MAP)
                self.state = 380
                self.match(GameParser.L_ANGLE)
                self.state = 381
                self.type_(0)
                self.state = 382
                self.match(GameParser.COMMA)
                self.state = 383
                self.type_(0)
                self.state = 384
                self.match(GameParser.R_ANGLE)
                pass
            elif token in [36]:
                localctx = GameParser.ArrayTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 386
                self.match(GameParser.ARRAY)
                self.state = 387
                self.match(GameParser.L_ANGLE)
                self.state = 388
                self.type_(0)
                self.state = 389
                self.match(GameParser.COMMA)
                self.state = 390
                self.integerExpression(0)
                self.state = 391
                self.match(GameParser.R_ANGLE)
                pass
            elif token in [31]:
                localctx = GameParser.IntTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 393
                self.match(GameParser.INTTYPE)
                pass
            elif token in [42, 53]:
                localctx = GameParser.UserTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 394
                self.id_()
                self.state = 399
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,29,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 395
                        self.match(GameParser.PERIOD)
                        self.state = 396
                        self.id_() 
                    self.state = 401
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,29,self._ctx)

                pass
            elif token in [35]:
                localctx = GameParser.BitStringTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 402
                self.bitstring()
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 416
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,33,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 414
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,32,self._ctx)
                    if la_ == 1:
                        localctx = GameParser.OptionalTypeContext(self, GameParser.TypeContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_type)
                        self.state = 405
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 9)")
                        self.state = 406
                        self.match(GameParser.QUESTION)
                        pass

                    elif la_ == 2:
                        localctx = GameParser.ProductTypeContext(self, GameParser.TypeContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_type)
                        self.state = 407
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 3)")
                        self.state = 410 
                        self._errHandler.sync(self)
                        _alt = 1
                        while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                            if _alt == 1:
                                self.state = 408
                                self.match(GameParser.TIMES)
                                self.state = 409
                                self.type_(0)

                            else:
                                raise NoViableAltException(self)
                            self.state = 412 
                            self._errHandler.sync(self)
                            _alt = self._interp.adaptivePredict(self._input,31,self._ctx)

                        pass

             
                self.state = 418
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,33,self._ctx)

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


        def BINARYNUM(self):
            return self.getToken(GameParser.BINARYNUM, 0)

        def INT(self):
            return self.getToken(GameParser.INT, 0)

        def integerExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.IntegerExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.IntegerExpressionContext,i)


        def PLUS(self):
            return self.getToken(GameParser.PLUS, 0)

        def TIMES(self):
            return self.getToken(GameParser.TIMES, 0)

        def SUBTRACT(self):
            return self.getToken(GameParser.SUBTRACT, 0)

        def DIVIDE(self):
            return self.getToken(GameParser.DIVIDE, 0)

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
        _startState = 34
        self.enterRecursionRule(localctx, 34, self.RULE_integerExpression, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 423
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [42, 53]:
                self.state = 420
                self.lvalue()
                pass
            elif token in [51]:
                self.state = 421
                self.match(GameParser.BINARYNUM)
                pass
            elif token in [52]:
                self.state = 422
                self.match(GameParser.INT)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 439
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,36,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 437
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,35,self._ctx)
                    if la_ == 1:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 425
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 4)")
                        self.state = 426
                        self.match(GameParser.PLUS)
                        self.state = 427
                        self.integerExpression(5)
                        pass

                    elif la_ == 2:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 428
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 3)")
                        self.state = 429
                        self.match(GameParser.TIMES)
                        self.state = 430
                        self.integerExpression(4)
                        pass

                    elif la_ == 3:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 431
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                        self.state = 432
                        self.match(GameParser.SUBTRACT)
                        self.state = 433
                        self.integerExpression(3)
                        pass

                    elif la_ == 4:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 434
                        if not self.precpred(self._ctx, 1):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 1)")
                        self.state = 435
                        self.match(GameParser.DIVIDE)
                        self.state = 436
                        self.integerExpression(2)
                        pass

             
                self.state = 441
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,36,self._ctx)

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
        self.enterRule(localctx, 36, self.RULE_bitstring)
        try:
            self.state = 448
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,37,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 442
                self.match(GameParser.BITSTRING)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 443
                self.match(GameParser.BITSTRING)
                self.state = 444
                self.match(GameParser.L_ANGLE)
                self.state = 445
                self.integerExpression(0)
                self.state = 446
                self.match(GameParser.R_ANGLE)
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
        self.enterRule(localctx, 38, self.RULE_set)
        try:
            self.state = 456
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,38,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 450
                self.match(GameParser.SET)
                self.state = 451
                self.match(GameParser.L_ANGLE)
                self.state = 452
                self.type_(0)
                self.state = 453
                self.match(GameParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 455
                self.match(GameParser.SET)
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
        self.enterRule(localctx, 40, self.RULE_moduleImport)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 458
            self.match(GameParser.IMPORT)
            self.state = 459
            self.match(GameParser.FILESTRING)
            self.state = 462
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==46:
                self.state = 460
                self.match(GameParser.AS)
                self.state = 461
                self.match(GameParser.ID)


            self.state = 464
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
        self.enterRule(localctx, 42, self.RULE_id)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 466
            _la = self._input.LA(1)
            if not(_la==42 or _la==53):
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
        self._predicates[13] = self.expression_sempred
        self._predicates[16] = self.type_sempred
        self._predicates[17] = self.integerExpression_sempred
        pred = self._predicates.get(ruleIndex, None)
        if pred is None:
            raise Exception("No predicate with index:" + str(ruleIndex))
        else:
            return pred(localctx, predIndex)

    def expression_sempred(self, localctx:ExpressionContext, predIndex:int):
            if predIndex == 0:
                return self.precpred(self._ctx, 28)
         

            if predIndex == 1:
                return self.precpred(self._ctx, 27)
         

            if predIndex == 2:
                return self.precpred(self._ctx, 26)
         

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
         




