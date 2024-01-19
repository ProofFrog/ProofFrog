# Generated from proof_frog/antlr/Scheme.g4 by ANTLR 4.13.1
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
        4,1,61,511,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,1,0,5,0,54,
        8,0,10,0,12,0,57,9,0,1,0,1,0,1,0,1,1,1,1,1,1,1,1,3,1,66,8,1,1,1,
        1,1,1,1,1,1,1,1,1,1,1,1,1,2,1,2,1,2,1,2,5,2,79,8,2,10,2,12,2,82,
        9,2,1,2,1,2,1,2,1,2,4,2,88,8,2,11,2,12,2,89,1,3,1,3,1,3,1,3,3,3,
        96,8,3,1,3,1,3,1,3,1,3,1,3,1,4,1,4,1,4,5,4,106,8,4,10,4,12,4,109,
        9,4,1,4,4,4,112,8,4,11,4,12,4,113,1,4,1,4,1,4,5,4,119,8,4,10,4,12,
        4,122,9,4,1,4,5,4,125,8,4,10,4,12,4,128,9,4,1,4,4,4,131,8,4,11,4,
        12,4,132,3,4,135,8,4,1,5,1,5,1,5,4,5,140,8,5,11,5,12,5,141,1,5,1,
        5,1,5,1,5,1,5,1,5,5,5,150,8,5,10,5,12,5,153,9,5,1,5,1,5,1,5,1,5,
        1,6,1,6,1,6,3,6,162,8,6,1,7,1,7,1,7,1,7,1,8,1,8,1,8,1,9,1,9,5,9,
        173,8,9,10,9,12,9,176,9,9,1,9,1,9,1,10,1,10,1,10,1,10,1,10,1,10,
        1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,
        1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,3,10,209,8,10,
        1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,
        1,10,1,10,1,10,1,10,1,10,1,10,5,10,230,8,10,10,10,12,10,233,9,10,
        1,10,1,10,3,10,237,8,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,
        1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,3,10,
        259,8,10,1,11,1,11,1,11,3,11,264,8,11,1,11,1,11,1,11,1,11,1,11,1,
        11,5,11,272,8,11,10,11,12,11,275,9,11,1,12,1,12,1,12,1,12,3,12,281,
        8,12,1,12,1,12,1,13,1,13,1,13,5,13,288,8,13,10,13,12,13,291,9,13,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,5,14,
        305,8,14,10,14,12,14,308,9,14,3,14,310,8,14,1,14,1,14,1,14,1,14,
        1,14,5,14,317,8,14,10,14,12,14,320,9,14,3,14,322,8,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,3,14,334,8,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,3,14,387,8,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,5,14,397,8,14,10,14,12,14,
        400,9,14,1,15,1,15,1,15,3,15,405,8,15,1,15,1,15,1,16,1,16,1,16,1,
        16,1,17,1,17,1,17,5,17,416,8,17,10,17,12,17,419,9,17,1,18,1,18,1,
        18,1,19,1,19,1,19,1,19,1,19,1,19,1,19,1,19,1,19,1,19,1,19,1,19,1,
        19,1,19,1,19,1,19,1,19,1,19,1,19,1,19,3,19,444,8,19,1,19,1,19,1,
        19,1,19,1,19,4,19,451,8,19,11,19,12,19,452,5,19,455,8,19,10,19,12,
        19,458,9,19,1,20,1,20,1,20,1,20,3,20,464,8,20,1,20,1,20,1,20,1,20,
        1,20,1,20,1,20,1,20,1,20,1,20,1,20,1,20,5,20,478,8,20,10,20,12,20,
        481,9,20,1,21,1,21,1,21,1,21,1,21,1,21,3,21,489,8,21,1,22,1,22,1,
        22,1,22,1,22,1,22,3,22,497,8,22,1,23,1,23,1,24,1,24,1,24,1,24,3,
        24,505,8,24,1,24,1,24,1,25,1,25,1,25,0,3,28,38,40,26,0,2,4,6,8,10,
        12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48,50,0,2,
        1,0,54,55,2,0,45,45,58,58,571,0,55,1,0,0,0,2,61,1,0,0,0,4,80,1,0,
        0,0,6,91,1,0,0,0,8,134,1,0,0,0,10,136,1,0,0,0,12,158,1,0,0,0,14,
        163,1,0,0,0,16,167,1,0,0,0,18,170,1,0,0,0,20,258,1,0,0,0,22,263,
        1,0,0,0,24,276,1,0,0,0,26,284,1,0,0,0,28,333,1,0,0,0,30,401,1,0,
        0,0,32,408,1,0,0,0,34,412,1,0,0,0,36,420,1,0,0,0,38,443,1,0,0,0,
        40,463,1,0,0,0,42,488,1,0,0,0,44,496,1,0,0,0,46,498,1,0,0,0,48,500,
        1,0,0,0,50,508,1,0,0,0,52,54,3,48,24,0,53,52,1,0,0,0,54,57,1,0,0,
        0,55,53,1,0,0,0,55,56,1,0,0,0,56,58,1,0,0,0,57,55,1,0,0,0,58,59,
        3,2,1,0,59,60,5,0,0,1,60,1,1,0,0,0,61,62,5,2,0,0,62,63,5,58,0,0,
        63,65,5,8,0,0,64,66,3,26,13,0,65,64,1,0,0,0,65,66,1,0,0,0,66,67,
        1,0,0,0,67,68,5,9,0,0,68,69,5,3,0,0,69,70,5,58,0,0,70,71,5,4,0,0,
        71,72,3,4,2,0,72,73,5,5,0,0,73,3,1,0,0,0,74,75,5,1,0,0,75,76,3,28,
        14,0,76,77,5,12,0,0,77,79,1,0,0,0,78,74,1,0,0,0,79,82,1,0,0,0,80,
        78,1,0,0,0,80,81,1,0,0,0,81,87,1,0,0,0,82,80,1,0,0,0,83,84,3,12,
        6,0,84,85,5,12,0,0,85,88,1,0,0,0,86,88,3,16,8,0,87,83,1,0,0,0,87,
        86,1,0,0,0,88,89,1,0,0,0,89,87,1,0,0,0,89,90,1,0,0,0,90,5,1,0,0,
        0,91,92,5,47,0,0,92,93,5,58,0,0,93,95,5,8,0,0,94,96,3,26,13,0,95,
        94,1,0,0,0,95,96,1,0,0,0,96,97,1,0,0,0,97,98,5,9,0,0,98,99,5,4,0,
        0,99,100,3,8,4,0,100,101,5,5,0,0,101,7,1,0,0,0,102,103,3,12,6,0,
        103,104,5,12,0,0,104,106,1,0,0,0,105,102,1,0,0,0,106,109,1,0,0,0,
        107,105,1,0,0,0,107,108,1,0,0,0,108,111,1,0,0,0,109,107,1,0,0,0,
        110,112,3,16,8,0,111,110,1,0,0,0,112,113,1,0,0,0,113,111,1,0,0,0,
        113,114,1,0,0,0,114,135,1,0,0,0,115,116,3,12,6,0,116,117,5,12,0,
        0,117,119,1,0,0,0,118,115,1,0,0,0,119,122,1,0,0,0,120,118,1,0,0,
        0,120,121,1,0,0,0,121,126,1,0,0,0,122,120,1,0,0,0,123,125,3,16,8,
        0,124,123,1,0,0,0,125,128,1,0,0,0,126,124,1,0,0,0,126,127,1,0,0,
        0,127,130,1,0,0,0,128,126,1,0,0,0,129,131,3,10,5,0,130,129,1,0,0,
        0,131,132,1,0,0,0,132,130,1,0,0,0,132,133,1,0,0,0,133,135,1,0,0,
        0,134,107,1,0,0,0,134,120,1,0,0,0,135,9,1,0,0,0,136,137,5,50,0,0,
        137,139,5,4,0,0,138,140,3,16,8,0,139,138,1,0,0,0,140,141,1,0,0,0,
        141,139,1,0,0,0,141,142,1,0,0,0,142,143,1,0,0,0,143,144,5,51,0,0,
        144,145,5,13,0,0,145,146,5,6,0,0,146,151,3,50,25,0,147,148,5,14,
        0,0,148,150,3,50,25,0,149,147,1,0,0,0,150,153,1,0,0,0,151,149,1,
        0,0,0,151,152,1,0,0,0,152,154,1,0,0,0,153,151,1,0,0,0,154,155,5,
        7,0,0,155,156,5,12,0,0,156,157,5,5,0,0,157,11,1,0,0,0,158,161,3,
        36,18,0,159,160,5,17,0,0,160,162,3,28,14,0,161,159,1,0,0,0,161,162,
        1,0,0,0,162,13,1,0,0,0,163,164,3,36,18,0,164,165,5,17,0,0,165,166,
        3,28,14,0,166,15,1,0,0,0,167,168,3,24,12,0,168,169,3,18,9,0,169,
        17,1,0,0,0,170,174,5,4,0,0,171,173,3,20,10,0,172,171,1,0,0,0,173,
        176,1,0,0,0,174,172,1,0,0,0,174,175,1,0,0,0,175,177,1,0,0,0,176,
        174,1,0,0,0,177,178,5,5,0,0,178,19,1,0,0,0,179,180,3,38,19,0,180,
        181,3,50,25,0,181,182,5,12,0,0,182,259,1,0,0,0,183,184,3,38,19,0,
        184,185,3,22,11,0,185,186,5,17,0,0,186,187,3,28,14,0,187,188,5,12,
        0,0,188,259,1,0,0,0,189,190,3,38,19,0,190,191,3,22,11,0,191,192,
        5,27,0,0,192,193,3,28,14,0,193,194,5,12,0,0,194,259,1,0,0,0,195,
        196,3,22,11,0,196,197,5,17,0,0,197,198,3,28,14,0,198,199,5,12,0,
        0,199,259,1,0,0,0,200,201,3,22,11,0,201,202,5,27,0,0,202,203,3,28,
        14,0,203,204,5,12,0,0,204,259,1,0,0,0,205,206,3,28,14,0,206,208,
        5,8,0,0,207,209,3,34,17,0,208,207,1,0,0,0,208,209,1,0,0,0,209,210,
        1,0,0,0,210,211,5,9,0,0,211,212,5,12,0,0,212,259,1,0,0,0,213,214,
        5,36,0,0,214,215,3,28,14,0,215,216,5,12,0,0,216,259,1,0,0,0,217,
        218,5,42,0,0,218,219,5,8,0,0,219,220,3,28,14,0,220,221,5,9,0,0,221,
        231,3,18,9,0,222,223,5,52,0,0,223,224,5,42,0,0,224,225,5,8,0,0,225,
        226,3,28,14,0,226,227,5,9,0,0,227,228,3,18,9,0,228,230,1,0,0,0,229,
        222,1,0,0,0,230,233,1,0,0,0,231,229,1,0,0,0,231,232,1,0,0,0,232,
        236,1,0,0,0,233,231,1,0,0,0,234,235,5,52,0,0,235,237,3,18,9,0,236,
        234,1,0,0,0,236,237,1,0,0,0,237,259,1,0,0,0,238,239,5,43,0,0,239,
        240,5,8,0,0,240,241,5,34,0,0,241,242,3,50,25,0,242,243,5,17,0,0,
        243,244,3,28,14,0,244,245,5,44,0,0,245,246,3,28,14,0,246,247,5,9,
        0,0,247,248,3,18,9,0,248,259,1,0,0,0,249,250,5,43,0,0,250,251,5,
        8,0,0,251,252,3,38,19,0,252,253,3,50,25,0,253,254,5,45,0,0,254,255,
        3,28,14,0,255,256,5,9,0,0,256,257,3,18,9,0,257,259,1,0,0,0,258,179,
        1,0,0,0,258,183,1,0,0,0,258,189,1,0,0,0,258,195,1,0,0,0,258,200,
        1,0,0,0,258,205,1,0,0,0,258,213,1,0,0,0,258,217,1,0,0,0,258,238,
        1,0,0,0,258,249,1,0,0,0,259,21,1,0,0,0,260,264,3,50,25,0,261,264,
        3,30,15,0,262,264,3,32,16,0,263,260,1,0,0,0,263,261,1,0,0,0,263,
        262,1,0,0,0,264,273,1,0,0,0,265,266,5,15,0,0,266,272,3,50,25,0,267,
        268,5,6,0,0,268,269,3,40,20,0,269,270,5,7,0,0,270,272,1,0,0,0,271,
        265,1,0,0,0,271,267,1,0,0,0,272,275,1,0,0,0,273,271,1,0,0,0,273,
        274,1,0,0,0,274,23,1,0,0,0,275,273,1,0,0,0,276,277,3,38,19,0,277,
        278,3,50,25,0,278,280,5,8,0,0,279,281,3,26,13,0,280,279,1,0,0,0,
        280,281,1,0,0,0,281,282,1,0,0,0,282,283,5,9,0,0,283,25,1,0,0,0,284,
        289,3,36,18,0,285,286,5,14,0,0,286,288,3,36,18,0,287,285,1,0,0,0,
        288,291,1,0,0,0,289,287,1,0,0,0,289,290,1,0,0,0,290,27,1,0,0,0,291,
        289,1,0,0,0,292,293,6,14,-1,0,293,334,3,22,11,0,294,295,5,30,0,0,
        295,334,3,28,14,12,296,297,5,31,0,0,297,298,3,28,14,0,298,299,5,
        31,0,0,299,334,1,0,0,0,300,309,5,6,0,0,301,306,3,28,14,0,302,303,
        5,14,0,0,303,305,3,28,14,0,304,302,1,0,0,0,305,308,1,0,0,0,306,304,
        1,0,0,0,306,307,1,0,0,0,307,310,1,0,0,0,308,306,1,0,0,0,309,301,
        1,0,0,0,309,310,1,0,0,0,310,311,1,0,0,0,311,334,5,7,0,0,312,321,
        5,4,0,0,313,318,3,28,14,0,314,315,5,14,0,0,315,317,3,28,14,0,316,
        314,1,0,0,0,317,320,1,0,0,0,318,316,1,0,0,0,318,319,1,0,0,0,319,
        322,1,0,0,0,320,318,1,0,0,0,321,313,1,0,0,0,321,322,1,0,0,0,322,
        323,1,0,0,0,323,334,5,5,0,0,324,334,3,38,19,0,325,334,5,56,0,0,326,
        334,5,57,0,0,327,334,3,46,23,0,328,334,5,53,0,0,329,330,5,8,0,0,
        330,331,3,28,14,0,331,332,5,9,0,0,332,334,1,0,0,0,333,292,1,0,0,
        0,333,294,1,0,0,0,333,296,1,0,0,0,333,300,1,0,0,0,333,312,1,0,0,
        0,333,324,1,0,0,0,333,325,1,0,0,0,333,326,1,0,0,0,333,327,1,0,0,
        0,333,328,1,0,0,0,333,329,1,0,0,0,334,398,1,0,0,0,335,336,10,29,
        0,0,336,337,5,22,0,0,337,397,3,28,14,30,338,339,10,28,0,0,339,340,
        5,23,0,0,340,397,3,28,14,29,341,342,10,27,0,0,342,343,5,11,0,0,343,
        397,3,28,14,28,344,345,10,26,0,0,345,346,5,10,0,0,346,397,3,28,14,
        27,347,348,10,25,0,0,348,349,5,24,0,0,349,397,3,28,14,26,350,351,
        10,24,0,0,351,352,5,25,0,0,352,397,3,28,14,25,353,354,10,23,0,0,
        354,355,5,28,0,0,355,397,3,28,14,24,356,357,10,22,0,0,357,358,5,
        41,0,0,358,397,3,28,14,23,359,360,10,21,0,0,360,361,5,45,0,0,361,
        397,3,28,14,22,362,363,10,20,0,0,363,364,5,26,0,0,364,397,3,28,14,
        21,365,366,10,19,0,0,366,367,5,46,0,0,367,397,3,28,14,20,368,369,
        10,18,0,0,369,370,5,29,0,0,370,397,3,28,14,19,371,372,10,17,0,0,
        372,373,5,18,0,0,373,397,3,28,14,18,374,375,10,16,0,0,375,376,5,
        19,0,0,376,397,3,28,14,17,377,378,10,15,0,0,378,379,5,16,0,0,379,
        397,3,28,14,16,380,381,10,14,0,0,381,382,5,20,0,0,382,397,3,28,14,
        15,383,384,10,10,0,0,384,386,5,8,0,0,385,387,3,34,17,0,386,385,1,
        0,0,0,386,387,1,0,0,0,387,388,1,0,0,0,388,397,5,9,0,0,389,390,10,
        9,0,0,390,391,5,6,0,0,391,392,3,40,20,0,392,393,5,13,0,0,393,394,
        3,40,20,0,394,395,5,7,0,0,395,397,1,0,0,0,396,335,1,0,0,0,396,338,
        1,0,0,0,396,341,1,0,0,0,396,344,1,0,0,0,396,347,1,0,0,0,396,350,
        1,0,0,0,396,353,1,0,0,0,396,356,1,0,0,0,396,359,1,0,0,0,396,362,
        1,0,0,0,396,365,1,0,0,0,396,368,1,0,0,0,396,371,1,0,0,0,396,374,
        1,0,0,0,396,377,1,0,0,0,396,380,1,0,0,0,396,383,1,0,0,0,396,389,
        1,0,0,0,397,400,1,0,0,0,398,396,1,0,0,0,398,399,1,0,0,0,399,29,1,
        0,0,0,400,398,1,0,0,0,401,402,5,58,0,0,402,404,5,8,0,0,403,405,3,
        34,17,0,404,403,1,0,0,0,404,405,1,0,0,0,405,406,1,0,0,0,406,407,
        5,9,0,0,407,31,1,0,0,0,408,409,3,30,15,0,409,410,5,15,0,0,410,411,
        5,58,0,0,411,33,1,0,0,0,412,417,3,28,14,0,413,414,5,14,0,0,414,416,
        3,28,14,0,415,413,1,0,0,0,416,419,1,0,0,0,417,415,1,0,0,0,417,418,
        1,0,0,0,418,35,1,0,0,0,419,417,1,0,0,0,420,421,3,38,19,0,421,422,
        3,50,25,0,422,37,1,0,0,0,423,424,6,19,-1,0,424,444,3,44,22,0,425,
        444,5,33,0,0,426,427,5,35,0,0,427,428,5,10,0,0,428,429,3,38,19,0,
        429,430,5,14,0,0,430,431,3,38,19,0,431,432,5,11,0,0,432,444,1,0,
        0,0,433,434,5,39,0,0,434,435,5,10,0,0,435,436,3,38,19,0,436,437,
        5,14,0,0,437,438,3,40,20,0,438,439,5,11,0,0,439,444,1,0,0,0,440,
        444,5,34,0,0,441,444,3,42,21,0,442,444,3,22,11,0,443,423,1,0,0,0,
        443,425,1,0,0,0,443,426,1,0,0,0,443,433,1,0,0,0,443,440,1,0,0,0,
        443,441,1,0,0,0,443,442,1,0,0,0,444,456,1,0,0,0,445,446,10,9,0,0,
        446,455,5,21,0,0,447,450,10,3,0,0,448,449,5,16,0,0,449,451,3,38,
        19,0,450,448,1,0,0,0,451,452,1,0,0,0,452,450,1,0,0,0,452,453,1,0,
        0,0,453,455,1,0,0,0,454,445,1,0,0,0,454,447,1,0,0,0,455,458,1,0,
        0,0,456,454,1,0,0,0,456,457,1,0,0,0,457,39,1,0,0,0,458,456,1,0,0,
        0,459,460,6,20,-1,0,460,464,3,22,11,0,461,464,5,57,0,0,462,464,5,
        56,0,0,463,459,1,0,0,0,463,461,1,0,0,0,463,462,1,0,0,0,464,479,1,
        0,0,0,465,466,10,7,0,0,466,467,5,16,0,0,467,478,3,40,20,8,468,469,
        10,6,0,0,469,470,5,20,0,0,470,478,3,40,20,7,471,472,10,5,0,0,472,
        473,5,18,0,0,473,478,3,40,20,6,474,475,10,4,0,0,475,476,5,19,0,0,
        476,478,3,40,20,5,477,465,1,0,0,0,477,468,1,0,0,0,477,471,1,0,0,
        0,477,474,1,0,0,0,478,481,1,0,0,0,479,477,1,0,0,0,479,480,1,0,0,
        0,480,41,1,0,0,0,481,479,1,0,0,0,482,483,5,38,0,0,483,484,5,10,0,
        0,484,485,3,40,20,0,485,486,5,11,0,0,486,489,1,0,0,0,487,489,5,38,
        0,0,488,482,1,0,0,0,488,487,1,0,0,0,489,43,1,0,0,0,490,491,5,32,
        0,0,491,492,5,10,0,0,492,493,3,38,19,0,493,494,5,11,0,0,494,497,
        1,0,0,0,495,497,5,32,0,0,496,490,1,0,0,0,496,495,1,0,0,0,497,45,
        1,0,0,0,498,499,7,0,0,0,499,47,1,0,0,0,500,501,5,37,0,0,501,504,
        5,61,0,0,502,503,5,49,0,0,503,505,5,58,0,0,504,502,1,0,0,0,504,505,
        1,0,0,0,505,506,1,0,0,0,506,507,5,12,0,0,507,49,1,0,0,0,508,509,
        7,1,0,0,509,51,1,0,0,0,45,55,65,80,87,89,95,107,113,120,126,132,
        134,141,151,161,174,208,231,236,258,263,271,273,280,289,306,309,
        318,321,333,386,396,398,404,417,443,452,454,456,463,477,479,488,
        496,504
    ]

class SchemeParser ( Parser ):

    grammarFileName = "Scheme.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'requires'", "'Scheme'", "'extends'", 
                     "'{'", "'}'", "'['", "']'", "'('", "')'", "'<'", "'>'", 
                     "';'", "':'", "','", "'.'", "'*'", "'='", "'+'", "'-'", 
                     "'/'", "'?'", "'=='", "'!='", "'>='", "'<='", "'||'", 
                     "'<-'", "'&&'", "'\\'", "'!'", "'|'", "'Set'", "'Bool'", 
                     "'Int'", "'Map'", "'return'", "'import'", "'BitString'", 
                     "'Array'", "'Primitive'", "'subsets'", "'if'", "'for'", 
                     "'to'", "'in'", "'union'", "'Game'", "'export'", "'as'", 
                     "'Phase'", "'oracles'", "'else'", "'None'", "'true'", 
                     "'false'" ]

    symbolicNames = [ "<INVALID>", "REQUIRES", "SCHEME", "EXTENDS", "L_CURLY", 
                      "R_CURLY", "L_SQUARE", "R_SQUARE", "L_PAREN", "R_PAREN", 
                      "L_ANGLE", "R_ANGLE", "SEMI", "COLON", "COMMA", "PERIOD", 
                      "TIMES", "EQUALS", "PLUS", "SUBTRACT", "DIVIDE", "QUESTION", 
                      "EQUALSCOMPARE", "NOTEQUALS", "GEQ", "LEQ", "OR", 
                      "SAMPLES", "AND", "BACKSLASH", "NOT", "VBAR", "SET", 
                      "BOOL", "INTTYPE", "MAP", "RETURN", "IMPORT", "BITSTRING", 
                      "ARRAY", "PRIMITIVE", "SUBSETS", "IF", "FOR", "TO", 
                      "IN", "UNION", "GAME", "EXPORT", "AS", "PHASE", "ORACLES", 
                      "ELSE", "NONE", "TRUE", "FALSE", "BINARYNUM", "INT", 
                      "ID", "WS", "LINE_COMMENT", "FILESTRING" ]

    RULE_program = 0
    RULE_scheme = 1
    RULE_schemeBody = 2
    RULE_game = 3
    RULE_gameBody = 4
    RULE_gamePhase = 5
    RULE_field = 6
    RULE_initializedField = 7
    RULE_method = 8
    RULE_block = 9
    RULE_statement = 10
    RULE_lvalue = 11
    RULE_methodSignature = 12
    RULE_paramList = 13
    RULE_expression = 14
    RULE_parameterizedGame = 15
    RULE_concreteGame = 16
    RULE_argList = 17
    RULE_variable = 18
    RULE_type = 19
    RULE_integerExpression = 20
    RULE_bitstring = 21
    RULE_set = 22
    RULE_bool = 23
    RULE_moduleImport = 24
    RULE_id = 25

    ruleNames =  [ "program", "scheme", "schemeBody", "game", "gameBody", 
                   "gamePhase", "field", "initializedField", "method", "block", 
                   "statement", "lvalue", "methodSignature", "paramList", 
                   "expression", "parameterizedGame", "concreteGame", "argList", 
                   "variable", "type", "integerExpression", "bitstring", 
                   "set", "bool", "moduleImport", "id" ]

    EOF = Token.EOF
    REQUIRES=1
    SCHEME=2
    EXTENDS=3
    L_CURLY=4
    R_CURLY=5
    L_SQUARE=6
    R_SQUARE=7
    L_PAREN=8
    R_PAREN=9
    L_ANGLE=10
    R_ANGLE=11
    SEMI=12
    COLON=13
    COMMA=14
    PERIOD=15
    TIMES=16
    EQUALS=17
    PLUS=18
    SUBTRACT=19
    DIVIDE=20
    QUESTION=21
    EQUALSCOMPARE=22
    NOTEQUALS=23
    GEQ=24
    LEQ=25
    OR=26
    SAMPLES=27
    AND=28
    BACKSLASH=29
    NOT=30
    VBAR=31
    SET=32
    BOOL=33
    INTTYPE=34
    MAP=35
    RETURN=36
    IMPORT=37
    BITSTRING=38
    ARRAY=39
    PRIMITIVE=40
    SUBSETS=41
    IF=42
    FOR=43
    TO=44
    IN=45
    UNION=46
    GAME=47
    EXPORT=48
    AS=49
    PHASE=50
    ORACLES=51
    ELSE=52
    NONE=53
    TRUE=54
    FALSE=55
    BINARYNUM=56
    INT=57
    ID=58
    WS=59
    LINE_COMMENT=60
    FILESTRING=61

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

        def scheme(self):
            return self.getTypedRuleContext(SchemeParser.SchemeContext,0)


        def EOF(self):
            return self.getToken(SchemeParser.EOF, 0)

        def moduleImport(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ModuleImportContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ModuleImportContext,i)


        def getRuleIndex(self):
            return SchemeParser.RULE_program

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitProgram" ):
                return visitor.visitProgram(self)
            else:
                return visitor.visitChildren(self)




    def program(self):

        localctx = SchemeParser.ProgramContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_program)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 55
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==37:
                self.state = 52
                self.moduleImport()
                self.state = 57
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 58
            self.scheme()
            self.state = 59
            self.match(SchemeParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SchemeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def SCHEME(self):
            return self.getToken(SchemeParser.SCHEME, 0)

        def ID(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.ID)
            else:
                return self.getToken(SchemeParser.ID, i)

        def L_PAREN(self):
            return self.getToken(SchemeParser.L_PAREN, 0)

        def R_PAREN(self):
            return self.getToken(SchemeParser.R_PAREN, 0)

        def EXTENDS(self):
            return self.getToken(SchemeParser.EXTENDS, 0)

        def L_CURLY(self):
            return self.getToken(SchemeParser.L_CURLY, 0)

        def schemeBody(self):
            return self.getTypedRuleContext(SchemeParser.SchemeBodyContext,0)


        def R_CURLY(self):
            return self.getToken(SchemeParser.R_CURLY, 0)

        def paramList(self):
            return self.getTypedRuleContext(SchemeParser.ParamListContext,0)


        def getRuleIndex(self):
            return SchemeParser.RULE_scheme

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitScheme" ):
                return visitor.visitScheme(self)
            else:
                return visitor.visitChildren(self)




    def scheme(self):

        localctx = SchemeParser.SchemeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_scheme)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 61
            self.match(SchemeParser.SCHEME)
            self.state = 62
            self.match(SchemeParser.ID)
            self.state = 63
            self.match(SchemeParser.L_PAREN)
            self.state = 65
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 288266449582030848) != 0):
                self.state = 64
                self.paramList()


            self.state = 67
            self.match(SchemeParser.R_PAREN)
            self.state = 68
            self.match(SchemeParser.EXTENDS)
            self.state = 69
            self.match(SchemeParser.ID)
            self.state = 70
            self.match(SchemeParser.L_CURLY)
            self.state = 71
            self.schemeBody()
            self.state = 72
            self.match(SchemeParser.R_CURLY)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SchemeBodyContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def REQUIRES(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.REQUIRES)
            else:
                return self.getToken(SchemeParser.REQUIRES, i)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)


        def SEMI(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.SEMI)
            else:
                return self.getToken(SchemeParser.SEMI, i)

        def field(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.FieldContext)
            else:
                return self.getTypedRuleContext(SchemeParser.FieldContext,i)


        def method(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.MethodContext)
            else:
                return self.getTypedRuleContext(SchemeParser.MethodContext,i)


        def getRuleIndex(self):
            return SchemeParser.RULE_schemeBody

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSchemeBody" ):
                return visitor.visitSchemeBody(self)
            else:
                return visitor.visitChildren(self)




    def schemeBody(self):

        localctx = SchemeParser.SchemeBodyContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_schemeBody)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 80
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==1:
                self.state = 74
                self.match(SchemeParser.REQUIRES)
                self.state = 75
                self.expression(0)
                self.state = 76
                self.match(SchemeParser.SEMI)
                self.state = 82
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 87 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 87
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input,3,self._ctx)
                if la_ == 1:
                    self.state = 83
                    self.field()
                    self.state = 84
                    self.match(SchemeParser.SEMI)
                    pass

                elif la_ == 2:
                    self.state = 86
                    self.method()
                    pass


                self.state = 89 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 288266449582030848) != 0)):
                    break

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
            return self.getToken(SchemeParser.GAME, 0)

        def ID(self):
            return self.getToken(SchemeParser.ID, 0)

        def L_PAREN(self):
            return self.getToken(SchemeParser.L_PAREN, 0)

        def R_PAREN(self):
            return self.getToken(SchemeParser.R_PAREN, 0)

        def L_CURLY(self):
            return self.getToken(SchemeParser.L_CURLY, 0)

        def gameBody(self):
            return self.getTypedRuleContext(SchemeParser.GameBodyContext,0)


        def R_CURLY(self):
            return self.getToken(SchemeParser.R_CURLY, 0)

        def paramList(self):
            return self.getTypedRuleContext(SchemeParser.ParamListContext,0)


        def getRuleIndex(self):
            return SchemeParser.RULE_game

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGame" ):
                return visitor.visitGame(self)
            else:
                return visitor.visitChildren(self)




    def game(self):

        localctx = SchemeParser.GameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_game)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 91
            self.match(SchemeParser.GAME)
            self.state = 92
            self.match(SchemeParser.ID)
            self.state = 93
            self.match(SchemeParser.L_PAREN)
            self.state = 95
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 288266449582030848) != 0):
                self.state = 94
                self.paramList()


            self.state = 97
            self.match(SchemeParser.R_PAREN)
            self.state = 98
            self.match(SchemeParser.L_CURLY)
            self.state = 99
            self.gameBody()
            self.state = 100
            self.match(SchemeParser.R_CURLY)
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
                return self.getTypedRuleContexts(SchemeParser.FieldContext)
            else:
                return self.getTypedRuleContext(SchemeParser.FieldContext,i)


        def SEMI(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.SEMI)
            else:
                return self.getToken(SchemeParser.SEMI, i)

        def method(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.MethodContext)
            else:
                return self.getTypedRuleContext(SchemeParser.MethodContext,i)


        def gamePhase(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.GamePhaseContext)
            else:
                return self.getTypedRuleContext(SchemeParser.GamePhaseContext,i)


        def getRuleIndex(self):
            return SchemeParser.RULE_gameBody

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGameBody" ):
                return visitor.visitGameBody(self)
            else:
                return visitor.visitChildren(self)




    def gameBody(self):

        localctx = SchemeParser.GameBodyContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_gameBody)
        self._la = 0 # Token type
        try:
            self.state = 134
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,11,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 107
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,6,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 102
                        self.field()
                        self.state = 103
                        self.match(SchemeParser.SEMI) 
                    self.state = 109
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,6,self._ctx)

                self.state = 111 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 110
                    self.method()
                    self.state = 113 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 288266449582030848) != 0)):
                        break

                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 120
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,8,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 115
                        self.field()
                        self.state = 116
                        self.match(SchemeParser.SEMI) 
                    self.state = 122
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,8,self._ctx)

                self.state = 126
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while (((_la) & ~0x3f) == 0 and ((1 << _la) & 288266449582030848) != 0):
                    self.state = 123
                    self.method()
                    self.state = 128
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 130 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 129
                    self.gamePhase()
                    self.state = 132 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==50):
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
            return self.getToken(SchemeParser.PHASE, 0)

        def L_CURLY(self):
            return self.getToken(SchemeParser.L_CURLY, 0)

        def ORACLES(self):
            return self.getToken(SchemeParser.ORACLES, 0)

        def COLON(self):
            return self.getToken(SchemeParser.COLON, 0)

        def L_SQUARE(self):
            return self.getToken(SchemeParser.L_SQUARE, 0)

        def id_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.IdContext)
            else:
                return self.getTypedRuleContext(SchemeParser.IdContext,i)


        def R_SQUARE(self):
            return self.getToken(SchemeParser.R_SQUARE, 0)

        def SEMI(self):
            return self.getToken(SchemeParser.SEMI, 0)

        def R_CURLY(self):
            return self.getToken(SchemeParser.R_CURLY, 0)

        def method(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.MethodContext)
            else:
                return self.getTypedRuleContext(SchemeParser.MethodContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.COMMA)
            else:
                return self.getToken(SchemeParser.COMMA, i)

        def getRuleIndex(self):
            return SchemeParser.RULE_gamePhase

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGamePhase" ):
                return visitor.visitGamePhase(self)
            else:
                return visitor.visitChildren(self)




    def gamePhase(self):

        localctx = SchemeParser.GamePhaseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_gamePhase)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 136
            self.match(SchemeParser.PHASE)
            self.state = 137
            self.match(SchemeParser.L_CURLY)
            self.state = 139 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 138
                self.method()
                self.state = 141 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 288266449582030848) != 0)):
                    break

            self.state = 143
            self.match(SchemeParser.ORACLES)
            self.state = 144
            self.match(SchemeParser.COLON)
            self.state = 145
            self.match(SchemeParser.L_SQUARE)
            self.state = 146
            self.id_()
            self.state = 151
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==14:
                self.state = 147
                self.match(SchemeParser.COMMA)
                self.state = 148
                self.id_()
                self.state = 153
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 154
            self.match(SchemeParser.R_SQUARE)
            self.state = 155
            self.match(SchemeParser.SEMI)
            self.state = 156
            self.match(SchemeParser.R_CURLY)
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
            return self.getTypedRuleContext(SchemeParser.VariableContext,0)


        def EQUALS(self):
            return self.getToken(SchemeParser.EQUALS, 0)

        def expression(self):
            return self.getTypedRuleContext(SchemeParser.ExpressionContext,0)


        def getRuleIndex(self):
            return SchemeParser.RULE_field

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitField" ):
                return visitor.visitField(self)
            else:
                return visitor.visitChildren(self)




    def field(self):

        localctx = SchemeParser.FieldContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_field)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 158
            self.variable()
            self.state = 161
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==17:
                self.state = 159
                self.match(SchemeParser.EQUALS)
                self.state = 160
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
            return self.getTypedRuleContext(SchemeParser.VariableContext,0)


        def EQUALS(self):
            return self.getToken(SchemeParser.EQUALS, 0)

        def expression(self):
            return self.getTypedRuleContext(SchemeParser.ExpressionContext,0)


        def getRuleIndex(self):
            return SchemeParser.RULE_initializedField

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitInitializedField" ):
                return visitor.visitInitializedField(self)
            else:
                return visitor.visitChildren(self)




    def initializedField(self):

        localctx = SchemeParser.InitializedFieldContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_initializedField)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 163
            self.variable()
            self.state = 164
            self.match(SchemeParser.EQUALS)
            self.state = 165
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
            return self.getTypedRuleContext(SchemeParser.MethodSignatureContext,0)


        def block(self):
            return self.getTypedRuleContext(SchemeParser.BlockContext,0)


        def getRuleIndex(self):
            return SchemeParser.RULE_method

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMethod" ):
                return visitor.visitMethod(self)
            else:
                return visitor.visitChildren(self)




    def method(self):

        localctx = SchemeParser.MethodContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_method)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 167
            self.methodSignature()
            self.state = 168
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
            return self.getToken(SchemeParser.L_CURLY, 0)

        def R_CURLY(self):
            return self.getToken(SchemeParser.R_CURLY, 0)

        def statement(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.StatementContext)
            else:
                return self.getTypedRuleContext(SchemeParser.StatementContext,i)


        def getRuleIndex(self):
            return SchemeParser.RULE_block

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBlock" ):
                return visitor.visitBlock(self)
            else:
                return visitor.visitChildren(self)




    def block(self):

        localctx = SchemeParser.BlockContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_block)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 170
            self.match(SchemeParser.L_CURLY)
            self.state = 174
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 567502892559237456) != 0):
                self.state = 171
                self.statement()
                self.state = 176
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 177
            self.match(SchemeParser.R_CURLY)
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
            return SchemeParser.RULE_statement

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)



    class VarDeclWithSampleStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(SchemeParser.TypeContext,0)

        def lvalue(self):
            return self.getTypedRuleContext(SchemeParser.LvalueContext,0)

        def SAMPLES(self):
            return self.getToken(SchemeParser.SAMPLES, 0)
        def expression(self):
            return self.getTypedRuleContext(SchemeParser.ExpressionContext,0)

        def SEMI(self):
            return self.getToken(SchemeParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVarDeclWithSampleStatement" ):
                return visitor.visitVarDeclWithSampleStatement(self)
            else:
                return visitor.visitChildren(self)


    class VarDeclStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(SchemeParser.TypeContext,0)

        def id_(self):
            return self.getTypedRuleContext(SchemeParser.IdContext,0)

        def SEMI(self):
            return self.getToken(SchemeParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVarDeclStatement" ):
                return visitor.visitVarDeclStatement(self)
            else:
                return visitor.visitChildren(self)


    class GenericForStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def FOR(self):
            return self.getToken(SchemeParser.FOR, 0)
        def L_PAREN(self):
            return self.getToken(SchemeParser.L_PAREN, 0)
        def type_(self):
            return self.getTypedRuleContext(SchemeParser.TypeContext,0)

        def id_(self):
            return self.getTypedRuleContext(SchemeParser.IdContext,0)

        def IN(self):
            return self.getToken(SchemeParser.IN, 0)
        def expression(self):
            return self.getTypedRuleContext(SchemeParser.ExpressionContext,0)

        def R_PAREN(self):
            return self.getToken(SchemeParser.R_PAREN, 0)
        def block(self):
            return self.getTypedRuleContext(SchemeParser.BlockContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGenericForStatement" ):
                return visitor.visitGenericForStatement(self)
            else:
                return visitor.visitChildren(self)


    class VarDeclWithValueStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(SchemeParser.TypeContext,0)

        def lvalue(self):
            return self.getTypedRuleContext(SchemeParser.LvalueContext,0)

        def EQUALS(self):
            return self.getToken(SchemeParser.EQUALS, 0)
        def expression(self):
            return self.getTypedRuleContext(SchemeParser.ExpressionContext,0)

        def SEMI(self):
            return self.getToken(SchemeParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVarDeclWithValueStatement" ):
                return visitor.visitVarDeclWithValueStatement(self)
            else:
                return visitor.visitChildren(self)


    class AssignmentStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def lvalue(self):
            return self.getTypedRuleContext(SchemeParser.LvalueContext,0)

        def EQUALS(self):
            return self.getToken(SchemeParser.EQUALS, 0)
        def expression(self):
            return self.getTypedRuleContext(SchemeParser.ExpressionContext,0)

        def SEMI(self):
            return self.getToken(SchemeParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssignmentStatement" ):
                return visitor.visitAssignmentStatement(self)
            else:
                return visitor.visitChildren(self)


    class NumericForStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def FOR(self):
            return self.getToken(SchemeParser.FOR, 0)
        def L_PAREN(self):
            return self.getToken(SchemeParser.L_PAREN, 0)
        def INTTYPE(self):
            return self.getToken(SchemeParser.INTTYPE, 0)
        def id_(self):
            return self.getTypedRuleContext(SchemeParser.IdContext,0)

        def EQUALS(self):
            return self.getToken(SchemeParser.EQUALS, 0)
        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def TO(self):
            return self.getToken(SchemeParser.TO, 0)
        def R_PAREN(self):
            return self.getToken(SchemeParser.R_PAREN, 0)
        def block(self):
            return self.getTypedRuleContext(SchemeParser.BlockContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNumericForStatement" ):
                return visitor.visitNumericForStatement(self)
            else:
                return visitor.visitChildren(self)


    class FunctionCallStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self):
            return self.getTypedRuleContext(SchemeParser.ExpressionContext,0)

        def L_PAREN(self):
            return self.getToken(SchemeParser.L_PAREN, 0)
        def R_PAREN(self):
            return self.getToken(SchemeParser.R_PAREN, 0)
        def SEMI(self):
            return self.getToken(SchemeParser.SEMI, 0)
        def argList(self):
            return self.getTypedRuleContext(SchemeParser.ArgListContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFunctionCallStatement" ):
                return visitor.visitFunctionCallStatement(self)
            else:
                return visitor.visitChildren(self)


    class ReturnStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def RETURN(self):
            return self.getToken(SchemeParser.RETURN, 0)
        def expression(self):
            return self.getTypedRuleContext(SchemeParser.ExpressionContext,0)

        def SEMI(self):
            return self.getToken(SchemeParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitReturnStatement" ):
                return visitor.visitReturnStatement(self)
            else:
                return visitor.visitChildren(self)


    class IfStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def IF(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.IF)
            else:
                return self.getToken(SchemeParser.IF, i)
        def L_PAREN(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.L_PAREN)
            else:
                return self.getToken(SchemeParser.L_PAREN, i)
        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def R_PAREN(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.R_PAREN)
            else:
                return self.getToken(SchemeParser.R_PAREN, i)
        def block(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.BlockContext)
            else:
                return self.getTypedRuleContext(SchemeParser.BlockContext,i)

        def ELSE(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.ELSE)
            else:
                return self.getToken(SchemeParser.ELSE, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIfStatement" ):
                return visitor.visitIfStatement(self)
            else:
                return visitor.visitChildren(self)


    class SampleStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def lvalue(self):
            return self.getTypedRuleContext(SchemeParser.LvalueContext,0)

        def SAMPLES(self):
            return self.getToken(SchemeParser.SAMPLES, 0)
        def expression(self):
            return self.getTypedRuleContext(SchemeParser.ExpressionContext,0)

        def SEMI(self):
            return self.getToken(SchemeParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSampleStatement" ):
                return visitor.visitSampleStatement(self)
            else:
                return visitor.visitChildren(self)



    def statement(self):

        localctx = SchemeParser.StatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_statement)
        self._la = 0 # Token type
        try:
            self.state = 258
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,19,self._ctx)
            if la_ == 1:
                localctx = SchemeParser.VarDeclStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 179
                self.type_(0)
                self.state = 180
                self.id_()
                self.state = 181
                self.match(SchemeParser.SEMI)
                pass

            elif la_ == 2:
                localctx = SchemeParser.VarDeclWithValueStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 183
                self.type_(0)
                self.state = 184
                self.lvalue()
                self.state = 185
                self.match(SchemeParser.EQUALS)
                self.state = 186
                self.expression(0)
                self.state = 187
                self.match(SchemeParser.SEMI)
                pass

            elif la_ == 3:
                localctx = SchemeParser.VarDeclWithSampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 189
                self.type_(0)
                self.state = 190
                self.lvalue()
                self.state = 191
                self.match(SchemeParser.SAMPLES)
                self.state = 192
                self.expression(0)
                self.state = 193
                self.match(SchemeParser.SEMI)
                pass

            elif la_ == 4:
                localctx = SchemeParser.AssignmentStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 195
                self.lvalue()
                self.state = 196
                self.match(SchemeParser.EQUALS)
                self.state = 197
                self.expression(0)
                self.state = 198
                self.match(SchemeParser.SEMI)
                pass

            elif la_ == 5:
                localctx = SchemeParser.SampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 5)
                self.state = 200
                self.lvalue()
                self.state = 201
                self.match(SchemeParser.SAMPLES)
                self.state = 202
                self.expression(0)
                self.state = 203
                self.match(SchemeParser.SEMI)
                pass

            elif la_ == 6:
                localctx = SchemeParser.FunctionCallStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 6)
                self.state = 205
                self.expression(0)
                self.state = 206
                self.match(SchemeParser.L_PAREN)
                self.state = 208
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 567489629700227408) != 0):
                    self.state = 207
                    self.argList()


                self.state = 210
                self.match(SchemeParser.R_PAREN)
                self.state = 211
                self.match(SchemeParser.SEMI)
                pass

            elif la_ == 7:
                localctx = SchemeParser.ReturnStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 7)
                self.state = 213
                self.match(SchemeParser.RETURN)
                self.state = 214
                self.expression(0)
                self.state = 215
                self.match(SchemeParser.SEMI)
                pass

            elif la_ == 8:
                localctx = SchemeParser.IfStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 8)
                self.state = 217
                self.match(SchemeParser.IF)
                self.state = 218
                self.match(SchemeParser.L_PAREN)
                self.state = 219
                self.expression(0)
                self.state = 220
                self.match(SchemeParser.R_PAREN)
                self.state = 221
                self.block()
                self.state = 231
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,17,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 222
                        self.match(SchemeParser.ELSE)
                        self.state = 223
                        self.match(SchemeParser.IF)
                        self.state = 224
                        self.match(SchemeParser.L_PAREN)
                        self.state = 225
                        self.expression(0)
                        self.state = 226
                        self.match(SchemeParser.R_PAREN)
                        self.state = 227
                        self.block() 
                    self.state = 233
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,17,self._ctx)

                self.state = 236
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==52:
                    self.state = 234
                    self.match(SchemeParser.ELSE)
                    self.state = 235
                    self.block()


                pass

            elif la_ == 9:
                localctx = SchemeParser.NumericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 9)
                self.state = 238
                self.match(SchemeParser.FOR)
                self.state = 239
                self.match(SchemeParser.L_PAREN)
                self.state = 240
                self.match(SchemeParser.INTTYPE)
                self.state = 241
                self.id_()
                self.state = 242
                self.match(SchemeParser.EQUALS)
                self.state = 243
                self.expression(0)
                self.state = 244
                self.match(SchemeParser.TO)
                self.state = 245
                self.expression(0)
                self.state = 246
                self.match(SchemeParser.R_PAREN)
                self.state = 247
                self.block()
                pass

            elif la_ == 10:
                localctx = SchemeParser.GenericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 10)
                self.state = 249
                self.match(SchemeParser.FOR)
                self.state = 250
                self.match(SchemeParser.L_PAREN)
                self.state = 251
                self.type_(0)
                self.state = 252
                self.id_()
                self.state = 253
                self.match(SchemeParser.IN)
                self.state = 254
                self.expression(0)
                self.state = 255
                self.match(SchemeParser.R_PAREN)
                self.state = 256
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
                return self.getTypedRuleContexts(SchemeParser.IdContext)
            else:
                return self.getTypedRuleContext(SchemeParser.IdContext,i)


        def parameterizedGame(self):
            return self.getTypedRuleContext(SchemeParser.ParameterizedGameContext,0)


        def concreteGame(self):
            return self.getTypedRuleContext(SchemeParser.ConcreteGameContext,0)


        def PERIOD(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.PERIOD)
            else:
                return self.getToken(SchemeParser.PERIOD, i)

        def L_SQUARE(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.L_SQUARE)
            else:
                return self.getToken(SchemeParser.L_SQUARE, i)

        def integerExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.IntegerExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.IntegerExpressionContext,i)


        def R_SQUARE(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.R_SQUARE)
            else:
                return self.getToken(SchemeParser.R_SQUARE, i)

        def getRuleIndex(self):
            return SchemeParser.RULE_lvalue

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLvalue" ):
                return visitor.visitLvalue(self)
            else:
                return visitor.visitChildren(self)




    def lvalue(self):

        localctx = SchemeParser.LvalueContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_lvalue)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 263
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,20,self._ctx)
            if la_ == 1:
                self.state = 260
                self.id_()
                pass

            elif la_ == 2:
                self.state = 261
                self.parameterizedGame()
                pass

            elif la_ == 3:
                self.state = 262
                self.concreteGame()
                pass


            self.state = 273
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,22,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 271
                    self._errHandler.sync(self)
                    token = self._input.LA(1)
                    if token in [15]:
                        self.state = 265
                        self.match(SchemeParser.PERIOD)
                        self.state = 266
                        self.id_()
                        pass
                    elif token in [6]:
                        self.state = 267
                        self.match(SchemeParser.L_SQUARE)
                        self.state = 268
                        self.integerExpression(0)
                        self.state = 269
                        self.match(SchemeParser.R_SQUARE)
                        pass
                    else:
                        raise NoViableAltException(self)
             
                self.state = 275
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,22,self._ctx)

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
            return self.getTypedRuleContext(SchemeParser.TypeContext,0)


        def id_(self):
            return self.getTypedRuleContext(SchemeParser.IdContext,0)


        def L_PAREN(self):
            return self.getToken(SchemeParser.L_PAREN, 0)

        def R_PAREN(self):
            return self.getToken(SchemeParser.R_PAREN, 0)

        def paramList(self):
            return self.getTypedRuleContext(SchemeParser.ParamListContext,0)


        def getRuleIndex(self):
            return SchemeParser.RULE_methodSignature

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMethodSignature" ):
                return visitor.visitMethodSignature(self)
            else:
                return visitor.visitChildren(self)




    def methodSignature(self):

        localctx = SchemeParser.MethodSignatureContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_methodSignature)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 276
            self.type_(0)
            self.state = 277
            self.id_()
            self.state = 278
            self.match(SchemeParser.L_PAREN)
            self.state = 280
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 288266449582030848) != 0):
                self.state = 279
                self.paramList()


            self.state = 282
            self.match(SchemeParser.R_PAREN)
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
                return self.getTypedRuleContexts(SchemeParser.VariableContext)
            else:
                return self.getTypedRuleContext(SchemeParser.VariableContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.COMMA)
            else:
                return self.getToken(SchemeParser.COMMA, i)

        def getRuleIndex(self):
            return SchemeParser.RULE_paramList

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitParamList" ):
                return visitor.visitParamList(self)
            else:
                return visitor.visitChildren(self)




    def paramList(self):

        localctx = SchemeParser.ParamListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_paramList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 284
            self.variable()
            self.state = 289
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==14:
                self.state = 285
                self.match(SchemeParser.COMMA)
                self.state = 286
                self.variable()
                self.state = 291
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
            return SchemeParser.RULE_expression

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)


    class CreateSetExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def L_CURLY(self):
            return self.getToken(SchemeParser.L_CURLY, 0)
        def R_CURLY(self):
            return self.getToken(SchemeParser.R_CURLY, 0)
        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.COMMA)
            else:
                return self.getToken(SchemeParser.COMMA, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCreateSetExp" ):
                return visitor.visitCreateSetExp(self)
            else:
                return visitor.visitChildren(self)


    class InExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def IN(self):
            return self.getToken(SchemeParser.IN, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitInExp" ):
                return visitor.visitInExp(self)
            else:
                return visitor.visitChildren(self)


    class AndExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def AND(self):
            return self.getToken(SchemeParser.AND, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAndExp" ):
                return visitor.visitAndExp(self)
            else:
                return visitor.visitChildren(self)


    class FnCallExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self):
            return self.getTypedRuleContext(SchemeParser.ExpressionContext,0)

        def L_PAREN(self):
            return self.getToken(SchemeParser.L_PAREN, 0)
        def R_PAREN(self):
            return self.getToken(SchemeParser.R_PAREN, 0)
        def argList(self):
            return self.getTypedRuleContext(SchemeParser.ArgListContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFnCallExp" ):
                return visitor.visitFnCallExp(self)
            else:
                return visitor.visitChildren(self)


    class LvalueExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def lvalue(self):
            return self.getTypedRuleContext(SchemeParser.LvalueContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLvalueExp" ):
                return visitor.visitLvalueExp(self)
            else:
                return visitor.visitChildren(self)


    class BoolExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def bool_(self):
            return self.getTypedRuleContext(SchemeParser.BoolContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBoolExp" ):
                return visitor.visitBoolExp(self)
            else:
                return visitor.visitChildren(self)


    class NotEqualsExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def NOTEQUALS(self):
            return self.getToken(SchemeParser.NOTEQUALS, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNotEqualsExp" ):
                return visitor.visitNotEqualsExp(self)
            else:
                return visitor.visitChildren(self)


    class AddExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def PLUS(self):
            return self.getToken(SchemeParser.PLUS, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAddExp" ):
                return visitor.visitAddExp(self)
            else:
                return visitor.visitChildren(self)


    class GeqExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def GEQ(self):
            return self.getToken(SchemeParser.GEQ, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGeqExp" ):
                return visitor.visitGeqExp(self)
            else:
                return visitor.visitChildren(self)


    class NotExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def NOT(self):
            return self.getToken(SchemeParser.NOT, 0)
        def expression(self):
            return self.getTypedRuleContext(SchemeParser.ExpressionContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNotExp" ):
                return visitor.visitNotExp(self)
            else:
                return visitor.visitChildren(self)


    class NoneExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def NONE(self):
            return self.getToken(SchemeParser.NONE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNoneExp" ):
                return visitor.visitNoneExp(self)
            else:
                return visitor.visitChildren(self)


    class GtExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def R_ANGLE(self):
            return self.getToken(SchemeParser.R_ANGLE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGtExp" ):
                return visitor.visitGtExp(self)
            else:
                return visitor.visitChildren(self)


    class LtExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def L_ANGLE(self):
            return self.getToken(SchemeParser.L_ANGLE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLtExp" ):
                return visitor.visitLtExp(self)
            else:
                return visitor.visitChildren(self)


    class SubtractExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def SUBTRACT(self):
            return self.getToken(SchemeParser.SUBTRACT, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSubtractExp" ):
                return visitor.visitSubtractExp(self)
            else:
                return visitor.visitChildren(self)


    class EqualsExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def EQUALSCOMPARE(self):
            return self.getToken(SchemeParser.EQUALSCOMPARE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitEqualsExp" ):
                return visitor.visitEqualsExp(self)
            else:
                return visitor.visitChildren(self)


    class MultiplyExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def TIMES(self):
            return self.getToken(SchemeParser.TIMES, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMultiplyExp" ):
                return visitor.visitMultiplyExp(self)
            else:
                return visitor.visitChildren(self)


    class SubsetsExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def SUBSETS(self):
            return self.getToken(SchemeParser.SUBSETS, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSubsetsExp" ):
                return visitor.visitSubsetsExp(self)
            else:
                return visitor.visitChildren(self)


    class UnionExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def UNION(self):
            return self.getToken(SchemeParser.UNION, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitUnionExp" ):
                return visitor.visitUnionExp(self)
            else:
                return visitor.visitChildren(self)


    class IntExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def INT(self):
            return self.getToken(SchemeParser.INT, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIntExp" ):
                return visitor.visitIntExp(self)
            else:
                return visitor.visitChildren(self)


    class SizeExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def VBAR(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.VBAR)
            else:
                return self.getToken(SchemeParser.VBAR, i)
        def expression(self):
            return self.getTypedRuleContext(SchemeParser.ExpressionContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSizeExp" ):
                return visitor.visitSizeExp(self)
            else:
                return visitor.visitChildren(self)


    class TypeExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(SchemeParser.TypeContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTypeExp" ):
                return visitor.visitTypeExp(self)
            else:
                return visitor.visitChildren(self)


    class LeqExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def LEQ(self):
            return self.getToken(SchemeParser.LEQ, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLeqExp" ):
                return visitor.visitLeqExp(self)
            else:
                return visitor.visitChildren(self)


    class OrExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def OR(self):
            return self.getToken(SchemeParser.OR, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOrExp" ):
                return visitor.visitOrExp(self)
            else:
                return visitor.visitChildren(self)


    class CreateTupleExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def L_SQUARE(self):
            return self.getToken(SchemeParser.L_SQUARE, 0)
        def R_SQUARE(self):
            return self.getToken(SchemeParser.R_SQUARE, 0)
        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.COMMA)
            else:
                return self.getToken(SchemeParser.COMMA, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCreateTupleExp" ):
                return visitor.visitCreateTupleExp(self)
            else:
                return visitor.visitChildren(self)


    class SetMinusExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def BACKSLASH(self):
            return self.getToken(SchemeParser.BACKSLASH, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSetMinusExp" ):
                return visitor.visitSetMinusExp(self)
            else:
                return visitor.visitChildren(self)


    class DivideExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def DIVIDE(self):
            return self.getToken(SchemeParser.DIVIDE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDivideExp" ):
                return visitor.visitDivideExp(self)
            else:
                return visitor.visitChildren(self)


    class BinaryNumExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def BINARYNUM(self):
            return self.getToken(SchemeParser.BINARYNUM, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBinaryNumExp" ):
                return visitor.visitBinaryNumExp(self)
            else:
                return visitor.visitChildren(self)


    class ParenExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def L_PAREN(self):
            return self.getToken(SchemeParser.L_PAREN, 0)
        def expression(self):
            return self.getTypedRuleContext(SchemeParser.ExpressionContext,0)

        def R_PAREN(self):
            return self.getToken(SchemeParser.R_PAREN, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitParenExp" ):
                return visitor.visitParenExp(self)
            else:
                return visitor.visitChildren(self)


    class SliceExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self):
            return self.getTypedRuleContext(SchemeParser.ExpressionContext,0)

        def L_SQUARE(self):
            return self.getToken(SchemeParser.L_SQUARE, 0)
        def integerExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.IntegerExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.IntegerExpressionContext,i)

        def COLON(self):
            return self.getToken(SchemeParser.COLON, 0)
        def R_SQUARE(self):
            return self.getToken(SchemeParser.R_SQUARE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSliceExp" ):
                return visitor.visitSliceExp(self)
            else:
                return visitor.visitChildren(self)



    def expression(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = SchemeParser.ExpressionContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 28
        self.enterRecursionRule(localctx, 28, self.RULE_expression, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 333
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,29,self._ctx)
            if la_ == 1:
                localctx = SchemeParser.LvalueExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 293
                self.lvalue()
                pass

            elif la_ == 2:
                localctx = SchemeParser.NotExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 294
                self.match(SchemeParser.NOT)
                self.state = 295
                self.expression(12)
                pass

            elif la_ == 3:
                localctx = SchemeParser.SizeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 296
                self.match(SchemeParser.VBAR)
                self.state = 297
                self.expression(0)
                self.state = 298
                self.match(SchemeParser.VBAR)
                pass

            elif la_ == 4:
                localctx = SchemeParser.CreateTupleExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 300
                self.match(SchemeParser.L_SQUARE)
                self.state = 309
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 567489629700227408) != 0):
                    self.state = 301
                    self.expression(0)
                    self.state = 306
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==14:
                        self.state = 302
                        self.match(SchemeParser.COMMA)
                        self.state = 303
                        self.expression(0)
                        self.state = 308
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 311
                self.match(SchemeParser.R_SQUARE)
                pass

            elif la_ == 5:
                localctx = SchemeParser.CreateSetExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 312
                self.match(SchemeParser.L_CURLY)
                self.state = 321
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 567489629700227408) != 0):
                    self.state = 313
                    self.expression(0)
                    self.state = 318
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==14:
                        self.state = 314
                        self.match(SchemeParser.COMMA)
                        self.state = 315
                        self.expression(0)
                        self.state = 320
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 323
                self.match(SchemeParser.R_CURLY)
                pass

            elif la_ == 6:
                localctx = SchemeParser.TypeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 324
                self.type_(0)
                pass

            elif la_ == 7:
                localctx = SchemeParser.BinaryNumExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 325
                self.match(SchemeParser.BINARYNUM)
                pass

            elif la_ == 8:
                localctx = SchemeParser.IntExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 326
                self.match(SchemeParser.INT)
                pass

            elif la_ == 9:
                localctx = SchemeParser.BoolExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 327
                self.bool_()
                pass

            elif la_ == 10:
                localctx = SchemeParser.NoneExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 328
                self.match(SchemeParser.NONE)
                pass

            elif la_ == 11:
                localctx = SchemeParser.ParenExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 329
                self.match(SchemeParser.L_PAREN)
                self.state = 330
                self.expression(0)
                self.state = 331
                self.match(SchemeParser.R_PAREN)
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 398
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,32,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 396
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,31,self._ctx)
                    if la_ == 1:
                        localctx = SchemeParser.EqualsExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 335
                        if not self.precpred(self._ctx, 29):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 29)")
                        self.state = 336
                        self.match(SchemeParser.EQUALSCOMPARE)
                        self.state = 337
                        self.expression(30)
                        pass

                    elif la_ == 2:
                        localctx = SchemeParser.NotEqualsExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 338
                        if not self.precpred(self._ctx, 28):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 28)")
                        self.state = 339
                        self.match(SchemeParser.NOTEQUALS)
                        self.state = 340
                        self.expression(29)
                        pass

                    elif la_ == 3:
                        localctx = SchemeParser.GtExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 341
                        if not self.precpred(self._ctx, 27):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 27)")
                        self.state = 342
                        self.match(SchemeParser.R_ANGLE)
                        self.state = 343
                        self.expression(28)
                        pass

                    elif la_ == 4:
                        localctx = SchemeParser.LtExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 344
                        if not self.precpred(self._ctx, 26):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 26)")
                        self.state = 345
                        self.match(SchemeParser.L_ANGLE)
                        self.state = 346
                        self.expression(27)
                        pass

                    elif la_ == 5:
                        localctx = SchemeParser.GeqExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 347
                        if not self.precpred(self._ctx, 25):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 25)")
                        self.state = 348
                        self.match(SchemeParser.GEQ)
                        self.state = 349
                        self.expression(26)
                        pass

                    elif la_ == 6:
                        localctx = SchemeParser.LeqExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 350
                        if not self.precpred(self._ctx, 24):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 24)")
                        self.state = 351
                        self.match(SchemeParser.LEQ)
                        self.state = 352
                        self.expression(25)
                        pass

                    elif la_ == 7:
                        localctx = SchemeParser.AndExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 353
                        if not self.precpred(self._ctx, 23):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 23)")
                        self.state = 354
                        self.match(SchemeParser.AND)
                        self.state = 355
                        self.expression(24)
                        pass

                    elif la_ == 8:
                        localctx = SchemeParser.SubsetsExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 356
                        if not self.precpred(self._ctx, 22):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 22)")
                        self.state = 357
                        self.match(SchemeParser.SUBSETS)
                        self.state = 358
                        self.expression(23)
                        pass

                    elif la_ == 9:
                        localctx = SchemeParser.InExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 359
                        if not self.precpred(self._ctx, 21):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 21)")
                        self.state = 360
                        self.match(SchemeParser.IN)
                        self.state = 361
                        self.expression(22)
                        pass

                    elif la_ == 10:
                        localctx = SchemeParser.OrExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 362
                        if not self.precpred(self._ctx, 20):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 20)")
                        self.state = 363
                        self.match(SchemeParser.OR)
                        self.state = 364
                        self.expression(21)
                        pass

                    elif la_ == 11:
                        localctx = SchemeParser.UnionExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 365
                        if not self.precpred(self._ctx, 19):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 19)")
                        self.state = 366
                        self.match(SchemeParser.UNION)
                        self.state = 367
                        self.expression(20)
                        pass

                    elif la_ == 12:
                        localctx = SchemeParser.SetMinusExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 368
                        if not self.precpred(self._ctx, 18):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 18)")
                        self.state = 369
                        self.match(SchemeParser.BACKSLASH)
                        self.state = 370
                        self.expression(19)
                        pass

                    elif la_ == 13:
                        localctx = SchemeParser.AddExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 371
                        if not self.precpred(self._ctx, 17):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 17)")
                        self.state = 372
                        self.match(SchemeParser.PLUS)
                        self.state = 373
                        self.expression(18)
                        pass

                    elif la_ == 14:
                        localctx = SchemeParser.SubtractExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 374
                        if not self.precpred(self._ctx, 16):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 16)")
                        self.state = 375
                        self.match(SchemeParser.SUBTRACT)
                        self.state = 376
                        self.expression(17)
                        pass

                    elif la_ == 15:
                        localctx = SchemeParser.MultiplyExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 377
                        if not self.precpred(self._ctx, 15):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 15)")
                        self.state = 378
                        self.match(SchemeParser.TIMES)
                        self.state = 379
                        self.expression(16)
                        pass

                    elif la_ == 16:
                        localctx = SchemeParser.DivideExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 380
                        if not self.precpred(self._ctx, 14):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 14)")
                        self.state = 381
                        self.match(SchemeParser.DIVIDE)
                        self.state = 382
                        self.expression(15)
                        pass

                    elif la_ == 17:
                        localctx = SchemeParser.FnCallExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 383
                        if not self.precpred(self._ctx, 10):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 10)")
                        self.state = 384
                        self.match(SchemeParser.L_PAREN)
                        self.state = 386
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)
                        if (((_la) & ~0x3f) == 0 and ((1 << _la) & 567489629700227408) != 0):
                            self.state = 385
                            self.argList()


                        self.state = 388
                        self.match(SchemeParser.R_PAREN)
                        pass

                    elif la_ == 18:
                        localctx = SchemeParser.SliceExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 389
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 9)")
                        self.state = 390
                        self.match(SchemeParser.L_SQUARE)
                        self.state = 391
                        self.integerExpression(0)
                        self.state = 392
                        self.match(SchemeParser.COLON)
                        self.state = 393
                        self.integerExpression(0)
                        self.state = 394
                        self.match(SchemeParser.R_SQUARE)
                        pass

             
                self.state = 400
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,32,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class ParameterizedGameContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(SchemeParser.ID, 0)

        def L_PAREN(self):
            return self.getToken(SchemeParser.L_PAREN, 0)

        def R_PAREN(self):
            return self.getToken(SchemeParser.R_PAREN, 0)

        def argList(self):
            return self.getTypedRuleContext(SchemeParser.ArgListContext,0)


        def getRuleIndex(self):
            return SchemeParser.RULE_parameterizedGame

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitParameterizedGame" ):
                return visitor.visitParameterizedGame(self)
            else:
                return visitor.visitChildren(self)




    def parameterizedGame(self):

        localctx = SchemeParser.ParameterizedGameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 30, self.RULE_parameterizedGame)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 401
            self.match(SchemeParser.ID)
            self.state = 402
            self.match(SchemeParser.L_PAREN)
            self.state = 404
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 567489629700227408) != 0):
                self.state = 403
                self.argList()


            self.state = 406
            self.match(SchemeParser.R_PAREN)
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

        def parameterizedGame(self):
            return self.getTypedRuleContext(SchemeParser.ParameterizedGameContext,0)


        def PERIOD(self):
            return self.getToken(SchemeParser.PERIOD, 0)

        def ID(self):
            return self.getToken(SchemeParser.ID, 0)

        def getRuleIndex(self):
            return SchemeParser.RULE_concreteGame

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConcreteGame" ):
                return visitor.visitConcreteGame(self)
            else:
                return visitor.visitChildren(self)




    def concreteGame(self):

        localctx = SchemeParser.ConcreteGameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_concreteGame)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 408
            self.parameterizedGame()
            self.state = 409
            self.match(SchemeParser.PERIOD)
            self.state = 410
            self.match(SchemeParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ArgListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.COMMA)
            else:
                return self.getToken(SchemeParser.COMMA, i)

        def getRuleIndex(self):
            return SchemeParser.RULE_argList

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitArgList" ):
                return visitor.visitArgList(self)
            else:
                return visitor.visitChildren(self)




    def argList(self):

        localctx = SchemeParser.ArgListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_argList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 412
            self.expression(0)
            self.state = 417
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==14:
                self.state = 413
                self.match(SchemeParser.COMMA)
                self.state = 414
                self.expression(0)
                self.state = 419
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
            return self.getTypedRuleContext(SchemeParser.TypeContext,0)


        def id_(self):
            return self.getTypedRuleContext(SchemeParser.IdContext,0)


        def getRuleIndex(self):
            return SchemeParser.RULE_variable

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVariable" ):
                return visitor.visitVariable(self)
            else:
                return visitor.visitChildren(self)




    def variable(self):

        localctx = SchemeParser.VariableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_variable)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 420
            self.type_(0)
            self.state = 421
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
            return SchemeParser.RULE_type

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)


    class ArrayTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def ARRAY(self):
            return self.getToken(SchemeParser.ARRAY, 0)
        def L_ANGLE(self):
            return self.getToken(SchemeParser.L_ANGLE, 0)
        def type_(self):
            return self.getTypedRuleContext(SchemeParser.TypeContext,0)

        def COMMA(self):
            return self.getToken(SchemeParser.COMMA, 0)
        def integerExpression(self):
            return self.getTypedRuleContext(SchemeParser.IntegerExpressionContext,0)

        def R_ANGLE(self):
            return self.getToken(SchemeParser.R_ANGLE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitArrayType" ):
                return visitor.visitArrayType(self)
            else:
                return visitor.visitChildren(self)


    class IntTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def INTTYPE(self):
            return self.getToken(SchemeParser.INTTYPE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIntType" ):
                return visitor.visitIntType(self)
            else:
                return visitor.visitChildren(self)


    class LvalueTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def lvalue(self):
            return self.getTypedRuleContext(SchemeParser.LvalueContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLvalueType" ):
                return visitor.visitLvalueType(self)
            else:
                return visitor.visitChildren(self)


    class OptionalTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(SchemeParser.TypeContext,0)

        def QUESTION(self):
            return self.getToken(SchemeParser.QUESTION, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOptionalType" ):
                return visitor.visitOptionalType(self)
            else:
                return visitor.visitChildren(self)


    class MapTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def MAP(self):
            return self.getToken(SchemeParser.MAP, 0)
        def L_ANGLE(self):
            return self.getToken(SchemeParser.L_ANGLE, 0)
        def type_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.TypeContext)
            else:
                return self.getTypedRuleContext(SchemeParser.TypeContext,i)

        def COMMA(self):
            return self.getToken(SchemeParser.COMMA, 0)
        def R_ANGLE(self):
            return self.getToken(SchemeParser.R_ANGLE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMapType" ):
                return visitor.visitMapType(self)
            else:
                return visitor.visitChildren(self)


    class SetTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def set_(self):
            return self.getTypedRuleContext(SchemeParser.SetContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSetType" ):
                return visitor.visitSetType(self)
            else:
                return visitor.visitChildren(self)


    class BitStringTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def bitstring(self):
            return self.getTypedRuleContext(SchemeParser.BitstringContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBitStringType" ):
                return visitor.visitBitStringType(self)
            else:
                return visitor.visitChildren(self)


    class BoolTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def BOOL(self):
            return self.getToken(SchemeParser.BOOL, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBoolType" ):
                return visitor.visitBoolType(self)
            else:
                return visitor.visitChildren(self)


    class ProductTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.TypeContext)
            else:
                return self.getTypedRuleContext(SchemeParser.TypeContext,i)

        def TIMES(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.TIMES)
            else:
                return self.getToken(SchemeParser.TIMES, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitProductType" ):
                return visitor.visitProductType(self)
            else:
                return visitor.visitChildren(self)



    def type_(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = SchemeParser.TypeContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 38
        self.enterRecursionRule(localctx, 38, self.RULE_type, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 443
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [32]:
                localctx = SchemeParser.SetTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 424
                self.set_()
                pass
            elif token in [33]:
                localctx = SchemeParser.BoolTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 425
                self.match(SchemeParser.BOOL)
                pass
            elif token in [35]:
                localctx = SchemeParser.MapTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 426
                self.match(SchemeParser.MAP)
                self.state = 427
                self.match(SchemeParser.L_ANGLE)
                self.state = 428
                self.type_(0)
                self.state = 429
                self.match(SchemeParser.COMMA)
                self.state = 430
                self.type_(0)
                self.state = 431
                self.match(SchemeParser.R_ANGLE)
                pass
            elif token in [39]:
                localctx = SchemeParser.ArrayTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 433
                self.match(SchemeParser.ARRAY)
                self.state = 434
                self.match(SchemeParser.L_ANGLE)
                self.state = 435
                self.type_(0)
                self.state = 436
                self.match(SchemeParser.COMMA)
                self.state = 437
                self.integerExpression(0)
                self.state = 438
                self.match(SchemeParser.R_ANGLE)
                pass
            elif token in [34]:
                localctx = SchemeParser.IntTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 440
                self.match(SchemeParser.INTTYPE)
                pass
            elif token in [38]:
                localctx = SchemeParser.BitStringTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 441
                self.bitstring()
                pass
            elif token in [45, 58]:
                localctx = SchemeParser.LvalueTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 442
                self.lvalue()
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 456
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,38,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 454
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,37,self._ctx)
                    if la_ == 1:
                        localctx = SchemeParser.OptionalTypeContext(self, SchemeParser.TypeContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_type)
                        self.state = 445
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 9)")
                        self.state = 446
                        self.match(SchemeParser.QUESTION)
                        pass

                    elif la_ == 2:
                        localctx = SchemeParser.ProductTypeContext(self, SchemeParser.TypeContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_type)
                        self.state = 447
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 3)")
                        self.state = 450 
                        self._errHandler.sync(self)
                        _alt = 1
                        while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                            if _alt == 1:
                                self.state = 448
                                self.match(SchemeParser.TIMES)
                                self.state = 449
                                self.type_(0)

                            else:
                                raise NoViableAltException(self)
                            self.state = 452 
                            self._errHandler.sync(self)
                            _alt = self._interp.adaptivePredict(self._input,36,self._ctx)

                        pass

             
                self.state = 458
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,38,self._ctx)

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
            return self.getTypedRuleContext(SchemeParser.LvalueContext,0)


        def INT(self):
            return self.getToken(SchemeParser.INT, 0)

        def BINARYNUM(self):
            return self.getToken(SchemeParser.BINARYNUM, 0)

        def integerExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.IntegerExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.IntegerExpressionContext,i)


        def TIMES(self):
            return self.getToken(SchemeParser.TIMES, 0)

        def DIVIDE(self):
            return self.getToken(SchemeParser.DIVIDE, 0)

        def PLUS(self):
            return self.getToken(SchemeParser.PLUS, 0)

        def SUBTRACT(self):
            return self.getToken(SchemeParser.SUBTRACT, 0)

        def getRuleIndex(self):
            return SchemeParser.RULE_integerExpression

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIntegerExpression" ):
                return visitor.visitIntegerExpression(self)
            else:
                return visitor.visitChildren(self)



    def integerExpression(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = SchemeParser.IntegerExpressionContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 40
        self.enterRecursionRule(localctx, 40, self.RULE_integerExpression, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 463
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [45, 58]:
                self.state = 460
                self.lvalue()
                pass
            elif token in [57]:
                self.state = 461
                self.match(SchemeParser.INT)
                pass
            elif token in [56]:
                self.state = 462
                self.match(SchemeParser.BINARYNUM)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 479
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,41,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 477
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,40,self._ctx)
                    if la_ == 1:
                        localctx = SchemeParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 465
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 7)")
                        self.state = 466
                        self.match(SchemeParser.TIMES)
                        self.state = 467
                        self.integerExpression(8)
                        pass

                    elif la_ == 2:
                        localctx = SchemeParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 468
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 6)")
                        self.state = 469
                        self.match(SchemeParser.DIVIDE)
                        self.state = 470
                        self.integerExpression(7)
                        pass

                    elif la_ == 3:
                        localctx = SchemeParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 471
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 5)")
                        self.state = 472
                        self.match(SchemeParser.PLUS)
                        self.state = 473
                        self.integerExpression(6)
                        pass

                    elif la_ == 4:
                        localctx = SchemeParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 474
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 4)")
                        self.state = 475
                        self.match(SchemeParser.SUBTRACT)
                        self.state = 476
                        self.integerExpression(5)
                        pass

             
                self.state = 481
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,41,self._ctx)

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
            return self.getToken(SchemeParser.BITSTRING, 0)

        def L_ANGLE(self):
            return self.getToken(SchemeParser.L_ANGLE, 0)

        def integerExpression(self):
            return self.getTypedRuleContext(SchemeParser.IntegerExpressionContext,0)


        def R_ANGLE(self):
            return self.getToken(SchemeParser.R_ANGLE, 0)

        def getRuleIndex(self):
            return SchemeParser.RULE_bitstring

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBitstring" ):
                return visitor.visitBitstring(self)
            else:
                return visitor.visitChildren(self)




    def bitstring(self):

        localctx = SchemeParser.BitstringContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_bitstring)
        try:
            self.state = 488
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,42,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 482
                self.match(SchemeParser.BITSTRING)
                self.state = 483
                self.match(SchemeParser.L_ANGLE)
                self.state = 484
                self.integerExpression(0)
                self.state = 485
                self.match(SchemeParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 487
                self.match(SchemeParser.BITSTRING)
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
            return self.getToken(SchemeParser.SET, 0)

        def L_ANGLE(self):
            return self.getToken(SchemeParser.L_ANGLE, 0)

        def type_(self):
            return self.getTypedRuleContext(SchemeParser.TypeContext,0)


        def R_ANGLE(self):
            return self.getToken(SchemeParser.R_ANGLE, 0)

        def getRuleIndex(self):
            return SchemeParser.RULE_set

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSet" ):
                return visitor.visitSet(self)
            else:
                return visitor.visitChildren(self)




    def set_(self):

        localctx = SchemeParser.SetContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_set)
        try:
            self.state = 496
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,43,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 490
                self.match(SchemeParser.SET)
                self.state = 491
                self.match(SchemeParser.L_ANGLE)
                self.state = 492
                self.type_(0)
                self.state = 493
                self.match(SchemeParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 495
                self.match(SchemeParser.SET)
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
            return self.getToken(SchemeParser.TRUE, 0)

        def FALSE(self):
            return self.getToken(SchemeParser.FALSE, 0)

        def getRuleIndex(self):
            return SchemeParser.RULE_bool

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBool" ):
                return visitor.visitBool(self)
            else:
                return visitor.visitChildren(self)




    def bool_(self):

        localctx = SchemeParser.BoolContext(self, self._ctx, self.state)
        self.enterRule(localctx, 46, self.RULE_bool)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 498
            _la = self._input.LA(1)
            if not(_la==54 or _la==55):
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
            return self.getToken(SchemeParser.IMPORT, 0)

        def FILESTRING(self):
            return self.getToken(SchemeParser.FILESTRING, 0)

        def SEMI(self):
            return self.getToken(SchemeParser.SEMI, 0)

        def AS(self):
            return self.getToken(SchemeParser.AS, 0)

        def ID(self):
            return self.getToken(SchemeParser.ID, 0)

        def getRuleIndex(self):
            return SchemeParser.RULE_moduleImport

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitModuleImport" ):
                return visitor.visitModuleImport(self)
            else:
                return visitor.visitChildren(self)




    def moduleImport(self):

        localctx = SchemeParser.ModuleImportContext(self, self._ctx, self.state)
        self.enterRule(localctx, 48, self.RULE_moduleImport)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 500
            self.match(SchemeParser.IMPORT)
            self.state = 501
            self.match(SchemeParser.FILESTRING)
            self.state = 504
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==49:
                self.state = 502
                self.match(SchemeParser.AS)
                self.state = 503
                self.match(SchemeParser.ID)


            self.state = 506
            self.match(SchemeParser.SEMI)
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
            return self.getToken(SchemeParser.ID, 0)

        def IN(self):
            return self.getToken(SchemeParser.IN, 0)

        def getRuleIndex(self):
            return SchemeParser.RULE_id

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitId" ):
                return visitor.visitId(self)
            else:
                return visitor.visitChildren(self)




    def id_(self):

        localctx = SchemeParser.IdContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_id)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 508
            _la = self._input.LA(1)
            if not(_la==45 or _la==58):
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
        self._predicates[19] = self.type_sempred
        self._predicates[20] = self.integerExpression_sempred
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
                return self.precpred(self._ctx, 26)
         

            if predIndex == 4:
                return self.precpred(self._ctx, 25)
         

            if predIndex == 5:
                return self.precpred(self._ctx, 24)
         

            if predIndex == 6:
                return self.precpred(self._ctx, 23)
         

            if predIndex == 7:
                return self.precpred(self._ctx, 22)
         

            if predIndex == 8:
                return self.precpred(self._ctx, 21)
         

            if predIndex == 9:
                return self.precpred(self._ctx, 20)
         

            if predIndex == 10:
                return self.precpred(self._ctx, 19)
         

            if predIndex == 11:
                return self.precpred(self._ctx, 18)
         

            if predIndex == 12:
                return self.precpred(self._ctx, 17)
         

            if predIndex == 13:
                return self.precpred(self._ctx, 16)
         

            if predIndex == 14:
                return self.precpred(self._ctx, 15)
         

            if predIndex == 15:
                return self.precpred(self._ctx, 14)
         

            if predIndex == 16:
                return self.precpred(self._ctx, 10)
         

            if predIndex == 17:
                return self.precpred(self._ctx, 9)
         

    def type_sempred(self, localctx:TypeContext, predIndex:int):
            if predIndex == 18:
                return self.precpred(self._ctx, 9)
         

            if predIndex == 19:
                return self.precpred(self._ctx, 3)
         

    def integerExpression_sempred(self, localctx:IntegerExpressionContext, predIndex:int):
            if predIndex == 20:
                return self.precpred(self._ctx, 7)
         

            if predIndex == 21:
                return self.precpred(self._ctx, 6)
         

            if predIndex == 22:
                return self.precpred(self._ctx, 5)
         

            if predIndex == 23:
                return self.precpred(self._ctx, 4)
         




