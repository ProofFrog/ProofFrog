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
        4,1,69,572,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        1,0,5,0,56,8,0,10,0,12,0,59,9,0,1,0,1,0,1,0,1,0,1,0,1,1,1,1,1,1,
        1,1,1,1,1,2,1,2,1,2,1,2,3,2,75,8,2,1,2,1,2,1,2,1,2,1,2,1,3,1,3,1,
        3,5,3,85,8,3,10,3,12,3,88,9,3,1,3,4,3,91,8,3,11,3,12,3,92,1,4,1,
        4,1,4,3,4,98,8,4,1,5,1,5,1,5,1,5,1,6,1,6,1,6,1,7,1,7,5,7,109,8,7,
        10,7,12,7,112,9,7,1,7,1,7,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,
        8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,
        8,1,8,1,8,1,8,4,8,145,8,8,11,8,12,8,146,1,8,1,8,1,8,1,8,1,8,1,8,
        1,8,1,8,1,8,1,8,4,8,159,8,8,11,8,12,8,160,1,8,1,8,1,8,1,8,1,8,1,
        8,1,8,1,8,1,8,1,8,1,8,1,8,4,8,175,8,8,11,8,12,8,176,1,8,1,8,1,8,
        1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,
        1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,
        1,8,1,8,1,8,1,8,1,8,1,8,1,8,3,8,221,8,8,1,8,1,8,1,8,1,8,1,8,1,8,
        1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,5,8,242,8,8,
        10,8,12,8,245,9,8,1,8,1,8,3,8,249,8,8,1,8,1,8,1,8,1,8,1,8,1,8,1,
        8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,3,8,271,8,
        8,1,9,1,9,1,9,3,9,276,8,9,1,9,1,9,1,9,1,9,1,9,1,9,5,9,284,8,9,10,
        9,12,9,287,9,9,1,10,1,10,1,11,5,11,292,8,11,10,11,12,11,295,9,11,
        1,11,1,11,1,11,1,11,3,11,301,8,11,1,11,1,11,1,12,1,12,1,12,5,12,
        308,8,12,10,12,12,12,311,9,12,1,13,1,13,1,13,1,13,1,13,1,13,1,13,
        1,13,1,13,1,13,1,13,1,13,1,13,1,13,5,13,327,8,13,10,13,12,13,330,
        9,13,3,13,332,8,13,1,13,1,13,1,13,1,13,1,13,5,13,339,8,13,10,13,
        12,13,342,9,13,3,13,344,8,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,
        1,13,1,13,1,13,1,13,1,13,1,13,1,13,3,13,360,8,13,1,13,1,13,1,13,
        1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,
        1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,
        1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,
        1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,3,13,
        416,8,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,1,13,5,13,426,8,13,10,
        13,12,13,429,9,13,1,14,1,14,1,14,5,14,434,8,14,10,14,12,14,437,9,
        14,1,15,1,15,1,15,1,16,1,16,1,16,3,16,445,8,16,1,16,1,16,1,17,1,
        17,1,17,1,17,1,17,1,17,1,17,1,17,1,17,1,17,1,17,1,17,1,17,1,17,1,
        17,1,17,1,17,1,17,1,17,1,17,1,17,1,17,1,17,1,17,1,17,1,17,1,17,1,
        17,1,17,1,17,4,17,479,8,17,11,17,12,17,480,1,17,1,17,1,17,1,17,1,
        17,1,17,1,17,3,17,490,8,17,1,17,1,17,5,17,494,8,17,10,17,12,17,497,
        9,17,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,3,18,507,8,18,1,18,
        1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,5,18,521,
        8,18,10,18,12,18,524,9,18,1,19,1,19,1,19,1,19,1,19,1,19,3,19,532,
        8,19,1,20,1,20,1,20,1,20,1,20,1,20,3,20,540,8,20,1,21,1,21,1,21,
        1,21,1,21,1,22,1,22,1,22,1,22,1,22,1,23,1,23,1,23,1,23,1,23,1,23,
        3,23,558,8,23,1,24,1,24,1,25,1,25,1,25,1,25,3,25,566,8,25,1,25,1,
        25,1,26,1,26,1,26,0,3,26,34,36,27,0,2,4,6,8,10,12,14,16,18,20,22,
        24,26,28,30,32,34,36,38,40,42,44,46,48,50,52,0,3,1,0,57,58,1,0,59,
        60,3,0,40,41,49,49,65,65,644,0,57,1,0,0,0,2,65,1,0,0,0,4,70,1,0,
        0,0,6,86,1,0,0,0,8,94,1,0,0,0,10,99,1,0,0,0,12,103,1,0,0,0,14,106,
        1,0,0,0,16,270,1,0,0,0,18,275,1,0,0,0,20,288,1,0,0,0,22,293,1,0,
        0,0,24,304,1,0,0,0,26,359,1,0,0,0,28,430,1,0,0,0,30,438,1,0,0,0,
        32,441,1,0,0,0,34,489,1,0,0,0,36,506,1,0,0,0,38,531,1,0,0,0,40,539,
        1,0,0,0,42,541,1,0,0,0,44,546,1,0,0,0,46,557,1,0,0,0,48,559,1,0,
        0,0,50,561,1,0,0,0,52,569,1,0,0,0,54,56,3,50,25,0,55,54,1,0,0,0,
        56,59,1,0,0,0,57,55,1,0,0,0,57,58,1,0,0,0,58,60,1,0,0,0,59,57,1,
        0,0,0,60,61,3,4,2,0,61,62,3,4,2,0,62,63,3,2,1,0,63,64,5,0,0,1,64,
        1,1,0,0,0,65,66,5,52,0,0,66,67,5,53,0,0,67,68,3,52,26,0,68,69,5,
        9,0,0,69,3,1,0,0,0,70,71,5,51,0,0,71,72,3,52,26,0,72,74,5,5,0,0,
        73,75,3,24,12,0,74,73,1,0,0,0,74,75,1,0,0,0,75,76,1,0,0,0,76,77,
        5,6,0,0,77,78,5,1,0,0,78,79,3,6,3,0,79,80,5,2,0,0,80,5,1,0,0,0,81,
        82,3,8,4,0,82,83,5,9,0,0,83,85,1,0,0,0,84,81,1,0,0,0,85,88,1,0,0,
        0,86,84,1,0,0,0,86,87,1,0,0,0,87,90,1,0,0,0,88,86,1,0,0,0,89,91,
        3,12,6,0,90,89,1,0,0,0,91,92,1,0,0,0,92,90,1,0,0,0,92,93,1,0,0,0,
        93,7,1,0,0,0,94,97,3,30,15,0,95,96,5,14,0,0,96,98,3,26,13,0,97,95,
        1,0,0,0,97,98,1,0,0,0,98,9,1,0,0,0,99,100,3,30,15,0,100,101,5,14,
        0,0,101,102,3,26,13,0,102,11,1,0,0,0,103,104,3,22,11,0,104,105,3,
        14,7,0,105,13,1,0,0,0,106,110,5,1,0,0,107,109,3,16,8,0,108,107,1,
        0,0,0,109,112,1,0,0,0,110,108,1,0,0,0,110,111,1,0,0,0,111,113,1,
        0,0,0,112,110,1,0,0,0,113,114,5,2,0,0,114,15,1,0,0,0,115,116,3,34,
        17,0,116,117,3,52,26,0,117,118,5,9,0,0,118,271,1,0,0,0,119,120,3,
        34,17,0,120,121,3,18,9,0,121,122,5,14,0,0,122,123,3,26,13,0,123,
        124,5,9,0,0,124,271,1,0,0,0,125,126,3,34,17,0,126,127,3,18,9,0,127,
        128,5,25,0,0,128,129,3,26,13,0,129,130,5,27,0,0,130,131,3,26,13,
        0,131,132,5,9,0,0,132,271,1,0,0,0,133,134,3,34,17,0,134,135,3,18,
        9,0,135,136,5,25,0,0,136,137,3,26,13,0,137,138,5,9,0,0,138,271,1,
        0,0,0,139,140,3,34,17,0,140,141,5,3,0,0,141,144,3,52,26,0,142,143,
        5,11,0,0,143,145,3,52,26,0,144,142,1,0,0,0,145,146,1,0,0,0,146,144,
        1,0,0,0,146,147,1,0,0,0,147,148,1,0,0,0,148,149,5,4,0,0,149,150,
        5,14,0,0,150,151,3,26,13,0,151,152,5,9,0,0,152,271,1,0,0,0,153,154,
        3,34,17,0,154,155,5,3,0,0,155,158,3,52,26,0,156,157,5,11,0,0,157,
        159,3,52,26,0,158,156,1,0,0,0,159,160,1,0,0,0,160,158,1,0,0,0,160,
        161,1,0,0,0,161,162,1,0,0,0,162,163,5,4,0,0,163,164,5,25,0,0,164,
        165,3,26,13,0,165,166,5,27,0,0,166,167,3,26,13,0,167,168,5,9,0,0,
        168,271,1,0,0,0,169,170,3,34,17,0,170,171,5,3,0,0,171,174,3,52,26,
        0,172,173,5,11,0,0,173,175,3,52,26,0,174,172,1,0,0,0,175,176,1,0,
        0,0,176,174,1,0,0,0,176,177,1,0,0,0,177,178,1,0,0,0,178,179,5,4,
        0,0,179,180,5,25,0,0,180,181,3,26,13,0,181,182,5,9,0,0,182,271,1,
        0,0,0,183,184,3,18,9,0,184,185,5,14,0,0,185,186,3,26,13,0,186,187,
        5,9,0,0,187,271,1,0,0,0,188,189,3,18,9,0,189,190,5,25,0,0,190,191,
        3,26,13,0,191,192,5,27,0,0,192,193,3,26,13,0,193,194,5,9,0,0,194,
        271,1,0,0,0,195,196,3,18,9,0,196,197,5,25,0,0,197,198,3,26,13,0,
        198,199,5,9,0,0,199,271,1,0,0,0,200,201,3,34,17,0,201,202,3,18,9,
        0,202,203,5,24,0,0,203,204,5,3,0,0,204,205,3,26,13,0,205,206,5,4,
        0,0,206,207,3,34,17,0,207,208,5,9,0,0,208,271,1,0,0,0,209,210,3,
        18,9,0,210,211,5,24,0,0,211,212,5,3,0,0,212,213,3,26,13,0,213,214,
        5,4,0,0,214,215,3,34,17,0,215,216,5,9,0,0,216,271,1,0,0,0,217,218,
        3,26,13,0,218,220,5,5,0,0,219,221,3,28,14,0,220,219,1,0,0,0,220,
        221,1,0,0,0,221,222,1,0,0,0,222,223,5,6,0,0,223,224,5,9,0,0,224,
        271,1,0,0,0,225,226,5,36,0,0,226,227,3,26,13,0,227,228,5,9,0,0,228,
        271,1,0,0,0,229,230,5,46,0,0,230,231,5,5,0,0,231,232,3,26,13,0,232,
        233,5,6,0,0,233,243,3,14,7,0,234,235,5,54,0,0,235,236,5,46,0,0,236,
        237,5,5,0,0,237,238,3,26,13,0,238,239,5,6,0,0,239,240,3,14,7,0,240,
        242,1,0,0,0,241,234,1,0,0,0,242,245,1,0,0,0,243,241,1,0,0,0,243,
        244,1,0,0,0,244,248,1,0,0,0,245,243,1,0,0,0,246,247,5,54,0,0,247,
        249,3,14,7,0,248,246,1,0,0,0,248,249,1,0,0,0,249,271,1,0,0,0,250,
        251,5,47,0,0,251,252,5,5,0,0,252,253,5,34,0,0,253,254,3,52,26,0,
        254,255,5,14,0,0,255,256,3,26,13,0,256,257,5,48,0,0,257,258,3,26,
        13,0,258,259,5,6,0,0,259,260,3,14,7,0,260,271,1,0,0,0,261,262,5,
        47,0,0,262,263,5,5,0,0,263,264,3,34,17,0,264,265,3,52,26,0,265,266,
        5,49,0,0,266,267,3,26,13,0,267,268,5,6,0,0,268,269,3,14,7,0,269,
        271,1,0,0,0,270,115,1,0,0,0,270,119,1,0,0,0,270,125,1,0,0,0,270,
        133,1,0,0,0,270,139,1,0,0,0,270,153,1,0,0,0,270,169,1,0,0,0,270,
        183,1,0,0,0,270,188,1,0,0,0,270,195,1,0,0,0,270,200,1,0,0,0,270,
        209,1,0,0,0,270,217,1,0,0,0,270,225,1,0,0,0,270,229,1,0,0,0,270,
        250,1,0,0,0,270,261,1,0,0,0,271,17,1,0,0,0,272,276,3,52,26,0,273,
        276,3,32,16,0,274,276,5,56,0,0,275,272,1,0,0,0,275,273,1,0,0,0,275,
        274,1,0,0,0,276,285,1,0,0,0,277,278,5,12,0,0,278,284,3,52,26,0,279,
        280,5,3,0,0,280,281,3,26,13,0,281,282,5,4,0,0,282,284,1,0,0,0,283,
        277,1,0,0,0,283,279,1,0,0,0,284,287,1,0,0,0,285,283,1,0,0,0,285,
        286,1,0,0,0,286,19,1,0,0,0,287,285,1,0,0,0,288,289,7,0,0,0,289,21,
        1,0,0,0,290,292,3,20,10,0,291,290,1,0,0,0,292,295,1,0,0,0,293,291,
        1,0,0,0,293,294,1,0,0,0,294,296,1,0,0,0,295,293,1,0,0,0,296,297,
        3,34,17,0,297,298,3,52,26,0,298,300,5,5,0,0,299,301,3,24,12,0,300,
        299,1,0,0,0,300,301,1,0,0,0,301,302,1,0,0,0,302,303,5,6,0,0,303,
        23,1,0,0,0,304,309,3,30,15,0,305,306,5,11,0,0,306,308,3,30,15,0,
        307,305,1,0,0,0,308,311,1,0,0,0,309,307,1,0,0,0,309,310,1,0,0,0,
        310,25,1,0,0,0,311,309,1,0,0,0,312,313,6,13,-1,0,313,314,5,28,0,
        0,314,360,3,26,13,31,315,316,5,30,0,0,316,317,3,26,13,0,317,318,
        5,30,0,0,318,360,1,0,0,0,319,320,5,16,0,0,320,360,3,26,13,26,321,
        360,3,18,9,0,322,331,5,3,0,0,323,328,3,26,13,0,324,325,5,11,0,0,
        325,327,3,26,13,0,326,324,1,0,0,0,327,330,1,0,0,0,328,326,1,0,0,
        0,328,329,1,0,0,0,329,332,1,0,0,0,330,328,1,0,0,0,331,323,1,0,0,
        0,331,332,1,0,0,0,332,333,1,0,0,0,333,360,5,4,0,0,334,343,5,1,0,
        0,335,340,3,26,13,0,336,337,5,11,0,0,337,339,3,26,13,0,338,336,1,
        0,0,0,339,342,1,0,0,0,340,338,1,0,0,0,340,341,1,0,0,0,341,344,1,
        0,0,0,342,340,1,0,0,0,343,335,1,0,0,0,343,344,1,0,0,0,344,345,1,
        0,0,0,345,360,5,2,0,0,346,360,3,34,17,0,347,348,5,62,0,0,348,360,
        3,38,19,0,349,350,5,63,0,0,350,360,3,38,19,0,351,360,5,61,0,0,352,
        360,5,64,0,0,353,360,3,48,24,0,354,360,5,55,0,0,355,356,5,5,0,0,
        356,357,3,26,13,0,357,358,5,6,0,0,358,360,1,0,0,0,359,312,1,0,0,
        0,359,315,1,0,0,0,359,319,1,0,0,0,359,321,1,0,0,0,359,322,1,0,0,
        0,359,334,1,0,0,0,359,346,1,0,0,0,359,347,1,0,0,0,359,349,1,0,0,
        0,359,351,1,0,0,0,359,352,1,0,0,0,359,353,1,0,0,0,359,354,1,0,0,
        0,359,355,1,0,0,0,360,427,1,0,0,0,361,362,10,29,0,0,362,363,5,29,
        0,0,363,426,3,26,13,29,364,365,10,28,0,0,365,366,5,13,0,0,366,426,
        3,26,13,29,367,368,10,27,0,0,368,369,5,17,0,0,369,426,3,26,13,28,
        370,371,10,25,0,0,371,372,5,15,0,0,372,426,3,26,13,26,373,374,10,
        24,0,0,374,375,5,16,0,0,375,426,3,26,13,25,376,377,10,23,0,0,377,
        378,5,19,0,0,378,426,3,26,13,24,379,380,10,22,0,0,380,381,5,20,0,
        0,381,426,3,26,13,23,382,383,10,21,0,0,383,384,5,8,0,0,384,426,3,
        26,13,22,385,386,10,20,0,0,386,387,5,7,0,0,387,426,3,26,13,21,388,
        389,10,19,0,0,389,390,5,21,0,0,390,426,3,26,13,20,391,392,10,18,
        0,0,392,393,5,22,0,0,393,426,3,26,13,19,394,395,10,17,0,0,395,396,
        5,49,0,0,396,426,3,26,13,18,397,398,10,16,0,0,398,399,5,45,0,0,399,
        426,3,26,13,17,400,401,10,15,0,0,401,402,5,26,0,0,402,426,3,26,13,
        16,403,404,10,14,0,0,404,405,5,23,0,0,405,426,3,26,13,15,406,407,
        10,13,0,0,407,408,5,50,0,0,408,426,3,26,13,14,409,410,10,12,0,0,
        410,411,5,27,0,0,411,426,3,26,13,13,412,413,10,33,0,0,413,415,5,
        5,0,0,414,416,3,28,14,0,415,414,1,0,0,0,415,416,1,0,0,0,416,417,
        1,0,0,0,417,426,5,6,0,0,418,419,10,32,0,0,419,420,5,3,0,0,420,421,
        3,36,18,0,421,422,5,10,0,0,422,423,3,36,18,0,423,424,5,4,0,0,424,
        426,1,0,0,0,425,361,1,0,0,0,425,364,1,0,0,0,425,367,1,0,0,0,425,
        370,1,0,0,0,425,373,1,0,0,0,425,376,1,0,0,0,425,379,1,0,0,0,425,
        382,1,0,0,0,425,385,1,0,0,0,425,388,1,0,0,0,425,391,1,0,0,0,425,
        394,1,0,0,0,425,397,1,0,0,0,425,400,1,0,0,0,425,403,1,0,0,0,425,
        406,1,0,0,0,425,409,1,0,0,0,425,412,1,0,0,0,425,418,1,0,0,0,426,
        429,1,0,0,0,427,425,1,0,0,0,427,428,1,0,0,0,428,27,1,0,0,0,429,427,
        1,0,0,0,430,435,3,26,13,0,431,432,5,11,0,0,432,434,3,26,13,0,433,
        431,1,0,0,0,434,437,1,0,0,0,435,433,1,0,0,0,435,436,1,0,0,0,436,
        29,1,0,0,0,437,435,1,0,0,0,438,439,3,34,17,0,439,440,3,52,26,0,440,
        31,1,0,0,0,441,442,3,52,26,0,442,444,5,5,0,0,443,445,3,28,14,0,444,
        443,1,0,0,0,444,445,1,0,0,0,445,446,1,0,0,0,446,447,5,6,0,0,447,
        33,1,0,0,0,448,449,6,17,-1,0,449,490,3,46,23,0,450,490,5,32,0,0,
        451,490,5,33,0,0,452,453,5,35,0,0,453,454,5,7,0,0,454,455,3,34,17,
        0,455,456,5,11,0,0,456,457,3,34,17,0,457,458,5,8,0,0,458,490,1,0,
        0,0,459,460,5,42,0,0,460,461,5,7,0,0,461,462,3,34,17,0,462,463,5,
        11,0,0,463,464,3,36,18,0,464,465,5,8,0,0,465,490,1,0,0,0,466,467,
        5,43,0,0,467,468,5,7,0,0,468,469,3,34,17,0,469,470,5,11,0,0,470,
        471,3,34,17,0,471,472,5,8,0,0,472,490,1,0,0,0,473,490,5,34,0,0,474,
        475,5,3,0,0,475,478,3,34,17,0,476,477,5,11,0,0,477,479,3,34,17,0,
        478,476,1,0,0,0,479,480,1,0,0,0,480,478,1,0,0,0,480,481,1,0,0,0,
        481,482,1,0,0,0,482,483,5,4,0,0,483,490,1,0,0,0,484,490,3,40,20,
        0,485,490,3,42,21,0,486,490,3,44,22,0,487,490,5,40,0,0,488,490,3,
        18,9,0,489,448,1,0,0,0,489,450,1,0,0,0,489,451,1,0,0,0,489,452,1,
        0,0,0,489,459,1,0,0,0,489,466,1,0,0,0,489,473,1,0,0,0,489,474,1,
        0,0,0,489,484,1,0,0,0,489,485,1,0,0,0,489,486,1,0,0,0,489,487,1,
        0,0,0,489,488,1,0,0,0,490,495,1,0,0,0,491,492,10,14,0,0,492,494,
        5,18,0,0,493,491,1,0,0,0,494,497,1,0,0,0,495,493,1,0,0,0,495,496,
        1,0,0,0,496,35,1,0,0,0,497,495,1,0,0,0,498,499,6,18,-1,0,499,507,
        3,18,9,0,500,507,5,64,0,0,501,507,5,61,0,0,502,503,5,5,0,0,503,504,
        3,36,18,0,504,505,5,6,0,0,505,507,1,0,0,0,506,498,1,0,0,0,506,500,
        1,0,0,0,506,501,1,0,0,0,506,502,1,0,0,0,507,522,1,0,0,0,508,509,
        10,8,0,0,509,510,5,13,0,0,510,521,3,36,18,9,511,512,10,7,0,0,512,
        513,5,17,0,0,513,521,3,36,18,8,514,515,10,6,0,0,515,516,5,15,0,0,
        516,521,3,36,18,7,517,518,10,5,0,0,518,519,5,16,0,0,519,521,3,36,
        18,6,520,508,1,0,0,0,520,511,1,0,0,0,520,514,1,0,0,0,520,517,1,0,
        0,0,521,524,1,0,0,0,522,520,1,0,0,0,522,523,1,0,0,0,523,37,1,0,0,
        0,524,522,1,0,0,0,525,532,3,18,9,0,526,532,5,64,0,0,527,528,5,5,
        0,0,528,529,3,36,18,0,529,530,5,6,0,0,530,532,1,0,0,0,531,525,1,
        0,0,0,531,526,1,0,0,0,531,527,1,0,0,0,532,39,1,0,0,0,533,534,5,38,
        0,0,534,535,5,7,0,0,535,536,3,36,18,0,536,537,5,8,0,0,537,540,1,
        0,0,0,538,540,5,38,0,0,539,533,1,0,0,0,539,538,1,0,0,0,540,41,1,
        0,0,0,541,542,5,39,0,0,542,543,5,7,0,0,543,544,3,36,18,0,544,545,
        5,8,0,0,545,43,1,0,0,0,546,547,5,41,0,0,547,548,5,7,0,0,548,549,
        3,18,9,0,549,550,5,8,0,0,550,45,1,0,0,0,551,552,5,31,0,0,552,553,
        5,7,0,0,553,554,3,34,17,0,554,555,5,8,0,0,555,558,1,0,0,0,556,558,
        5,31,0,0,557,551,1,0,0,0,557,556,1,0,0,0,558,47,1,0,0,0,559,560,
        7,1,0,0,560,49,1,0,0,0,561,562,5,37,0,0,562,565,5,69,0,0,563,564,
        5,53,0,0,564,566,5,65,0,0,565,563,1,0,0,0,565,566,1,0,0,0,566,567,
        1,0,0,0,567,568,5,9,0,0,568,51,1,0,0,0,569,570,7,2,0,0,570,53,1,
        0,0,0,39,57,74,86,92,97,110,146,160,176,220,243,248,270,275,283,
        285,293,300,309,328,331,340,343,359,415,425,427,435,444,480,489,
        495,506,520,522,531,539,557,565
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
                     "'Group'", "'GroupElem'", "'Array'", "'Function'", 
                     "'Primitive'", "'subsets'", "'if'", "'for'", "'to'", 
                     "'in'", "'union'", "'Game'", "'export'", "'as'", "'else'", 
                     "'None'", "'this'", "'deterministic'", "'injective'", 
                     "'true'", "'false'", "<INVALID>", "'0^'", "'1^'" ]

    symbolicNames = [ "<INVALID>", "L_CURLY", "R_CURLY", "L_SQUARE", "R_SQUARE", 
                      "L_PAREN", "R_PAREN", "L_ANGLE", "R_ANGLE", "SEMI", 
                      "COLON", "COMMA", "PERIOD", "TIMES", "EQUALS", "PLUS", 
                      "SUBTRACT", "DIVIDE", "QUESTION", "EQUALSCOMPARE", 
                      "NOTEQUALS", "GEQ", "LEQ", "OR", "SAMPUNIQ", "SAMPLES", 
                      "AND", "BACKSLASH", "NOT", "CARET", "VBAR", "SET", 
                      "BOOL", "VOID", "INTTYPE", "MAP", "RETURN", "IMPORT", 
                      "BITSTRING", "MODINT", "GROUP", "GROUPELEM", "ARRAY", 
                      "FUNCTION", "PRIMITIVE", "SUBSETS", "IF", "FOR", "TO", 
                      "IN", "UNION", "GAME", "EXPORT", "AS", "ELSE", "NONE", 
                      "THIS", "DETERMINISTIC", "INJECTIVE", "TRUE", "FALSE", 
                      "BINARYNUM", "ZEROS_CARET", "ONES_CARET", "INT", "ID", 
                      "WS", "LINE_COMMENT", "BLOCK_COMMENT", "FILESTRING" ]

    RULE_program = 0
    RULE_gameExport = 1
    RULE_game = 2
    RULE_gameBody = 3
    RULE_field = 4
    RULE_initializedField = 5
    RULE_method = 6
    RULE_block = 7
    RULE_statement = 8
    RULE_lvalue = 9
    RULE_methodModifier = 10
    RULE_methodSignature = 11
    RULE_paramList = 12
    RULE_expression = 13
    RULE_argList = 14
    RULE_variable = 15
    RULE_parameterizedGame = 16
    RULE_type = 17
    RULE_integerExpression = 18
    RULE_integerAtom = 19
    RULE_bitstring = 20
    RULE_modint = 21
    RULE_groupelem = 22
    RULE_set = 23
    RULE_bool = 24
    RULE_moduleImport = 25
    RULE_id = 26

    ruleNames =  [ "program", "gameExport", "game", "gameBody", "field", 
                   "initializedField", "method", "block", "statement", "lvalue", 
                   "methodModifier", "methodSignature", "paramList", "expression", 
                   "argList", "variable", "parameterizedGame", "type", "integerExpression", 
                   "integerAtom", "bitstring", "modint", "groupelem", "set", 
                   "bool", "moduleImport", "id" ]

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
    GROUP=40
    GROUPELEM=41
    ARRAY=42
    FUNCTION=43
    PRIMITIVE=44
    SUBSETS=45
    IF=46
    FOR=47
    TO=48
    IN=49
    UNION=50
    GAME=51
    EXPORT=52
    AS=53
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
    BLOCK_COMMENT=68
    FILESTRING=69

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

        def id_(self):
            return self.getTypedRuleContext(GameParser.IdContext,0)


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
            self.id_()
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

        def id_(self):
            return self.getTypedRuleContext(GameParser.IdContext,0)


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
            self.id_()
            self.state = 72
            self.match(GameParser.L_PAREN)
            self.state = 74
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 3)) & ~0x3f) == 0 and ((1 << (_la - 3)) & 4620765759411322881) != 0):
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
                if not (((((_la - 3)) & ~0x3f) == 0 and ((1 << (_la - 3)) & 4674808954939768833) != 0)):
                    break

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
        self.enterRule(localctx, 8, self.RULE_field)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 94
            self.variable()
            self.state = 97
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==14:
                self.state = 95
                self.match(GameParser.EQUALS)
                self.state = 96
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
        self.enterRule(localctx, 10, self.RULE_initializedField)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 99
            self.variable()
            self.state = 100
            self.match(GameParser.EQUALS)
            self.state = 101
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
        self.enterRule(localctx, 12, self.RULE_method)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 103
            self.methodSignature()
            self.state = 104
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
        self.enterRule(localctx, 14, self.RULE_block)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 106
            self.match(GameParser.L_CURLY)
            self.state = 110
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & -467582851118727126) != 0) or _la==64 or _la==65:
                self.state = 107
                self.statement()
                self.state = 112
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 113
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

        def lvalue(self):
            return self.getTypedRuleContext(GameParser.LvalueContext,0)

        def SAMPUNIQ(self):
            return self.getToken(GameParser.SAMPUNIQ, 0)
        def L_SQUARE(self):
            return self.getToken(GameParser.L_SQUARE, 0)
        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)

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


    class DestructuringSampleStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(GameParser.TypeContext,0)

        def L_SQUARE(self):
            return self.getToken(GameParser.L_SQUARE, 0)
        def id_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.IdContext)
            else:
                return self.getTypedRuleContext(GameParser.IdContext,i)

        def R_SQUARE(self):
            return self.getToken(GameParser.R_SQUARE, 0)
        def SAMPLES(self):
            return self.getToken(GameParser.SAMPLES, 0)
        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)

        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)
        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.COMMA)
            else:
                return self.getToken(GameParser.COMMA, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDestructuringSampleStatement" ):
                return visitor.visitDestructuringSampleStatement(self)
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


    class DestructuringSampleMinusStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(GameParser.TypeContext,0)

        def L_SQUARE(self):
            return self.getToken(GameParser.L_SQUARE, 0)
        def id_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.IdContext)
            else:
                return self.getTypedRuleContext(GameParser.IdContext,i)

        def R_SQUARE(self):
            return self.getToken(GameParser.R_SQUARE, 0)
        def SAMPLES(self):
            return self.getToken(GameParser.SAMPLES, 0)
        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def BACKSLASH(self):
            return self.getToken(GameParser.BACKSLASH, 0)
        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)
        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.COMMA)
            else:
                return self.getToken(GameParser.COMMA, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDestructuringSampleMinusStatement" ):
                return visitor.visitDestructuringSampleMinusStatement(self)
            else:
                return visitor.visitChildren(self)


    class SampleMinusStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def lvalue(self):
            return self.getTypedRuleContext(GameParser.LvalueContext,0)

        def SAMPLES(self):
            return self.getToken(GameParser.SAMPLES, 0)
        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def BACKSLASH(self):
            return self.getToken(GameParser.BACKSLASH, 0)
        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSampleMinusStatement" ):
                return visitor.visitSampleMinusStatement(self)
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


    class VarDeclWithSampleMinusStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(GameParser.TypeContext,0)

        def lvalue(self):
            return self.getTypedRuleContext(GameParser.LvalueContext,0)

        def SAMPLES(self):
            return self.getToken(GameParser.SAMPLES, 0)
        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def BACKSLASH(self):
            return self.getToken(GameParser.BACKSLASH, 0)
        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVarDeclWithSampleMinusStatement" ):
                return visitor.visitVarDeclWithSampleMinusStatement(self)
            else:
                return visitor.visitChildren(self)


    class UniqueSampleNoTypeStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def lvalue(self):
            return self.getTypedRuleContext(GameParser.LvalueContext,0)

        def SAMPUNIQ(self):
            return self.getToken(GameParser.SAMPUNIQ, 0)
        def L_SQUARE(self):
            return self.getToken(GameParser.L_SQUARE, 0)
        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)

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


    class DestructuringAssignStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self):
            return self.getTypedRuleContext(GameParser.TypeContext,0)

        def L_SQUARE(self):
            return self.getToken(GameParser.L_SQUARE, 0)
        def id_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.IdContext)
            else:
                return self.getTypedRuleContext(GameParser.IdContext,i)

        def R_SQUARE(self):
            return self.getToken(GameParser.R_SQUARE, 0)
        def EQUALS(self):
            return self.getToken(GameParser.EQUALS, 0)
        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)

        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)
        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.COMMA)
            else:
                return self.getToken(GameParser.COMMA, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDestructuringAssignStatement" ):
                return visitor.visitDestructuringAssignStatement(self)
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
        self.enterRule(localctx, 16, self.RULE_statement)
        self._la = 0 # Token type
        try:
            self.state = 270
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,12,self._ctx)
            if la_ == 1:
                localctx = GameParser.VarDeclStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 115
                self.type_(0)
                self.state = 116
                self.id_()
                self.state = 117
                self.match(GameParser.SEMI)
                pass

            elif la_ == 2:
                localctx = GameParser.VarDeclWithValueStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 119
                self.type_(0)
                self.state = 120
                self.lvalue()
                self.state = 121
                self.match(GameParser.EQUALS)
                self.state = 122
                self.expression(0)
                self.state = 123
                self.match(GameParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GameParser.VarDeclWithSampleMinusStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 125
                self.type_(0)
                self.state = 126
                self.lvalue()
                self.state = 127
                self.match(GameParser.SAMPLES)
                self.state = 128
                self.expression(0)
                self.state = 129
                self.match(GameParser.BACKSLASH)
                self.state = 130
                self.expression(0)
                self.state = 131
                self.match(GameParser.SEMI)
                pass

            elif la_ == 4:
                localctx = GameParser.VarDeclWithSampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 133
                self.type_(0)
                self.state = 134
                self.lvalue()
                self.state = 135
                self.match(GameParser.SAMPLES)
                self.state = 136
                self.expression(0)
                self.state = 137
                self.match(GameParser.SEMI)
                pass

            elif la_ == 5:
                localctx = GameParser.DestructuringAssignStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 5)
                self.state = 139
                self.type_(0)
                self.state = 140
                self.match(GameParser.L_SQUARE)
                self.state = 141
                self.id_()
                self.state = 144 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 142
                    self.match(GameParser.COMMA)
                    self.state = 143
                    self.id_()
                    self.state = 146 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==11):
                        break

                self.state = 148
                self.match(GameParser.R_SQUARE)
                self.state = 149
                self.match(GameParser.EQUALS)
                self.state = 150
                self.expression(0)
                self.state = 151
                self.match(GameParser.SEMI)
                pass

            elif la_ == 6:
                localctx = GameParser.DestructuringSampleMinusStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 6)
                self.state = 153
                self.type_(0)
                self.state = 154
                self.match(GameParser.L_SQUARE)
                self.state = 155
                self.id_()
                self.state = 158 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 156
                    self.match(GameParser.COMMA)
                    self.state = 157
                    self.id_()
                    self.state = 160 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==11):
                        break

                self.state = 162
                self.match(GameParser.R_SQUARE)
                self.state = 163
                self.match(GameParser.SAMPLES)
                self.state = 164
                self.expression(0)
                self.state = 165
                self.match(GameParser.BACKSLASH)
                self.state = 166
                self.expression(0)
                self.state = 167
                self.match(GameParser.SEMI)
                pass

            elif la_ == 7:
                localctx = GameParser.DestructuringSampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 7)
                self.state = 169
                self.type_(0)
                self.state = 170
                self.match(GameParser.L_SQUARE)
                self.state = 171
                self.id_()
                self.state = 174 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 172
                    self.match(GameParser.COMMA)
                    self.state = 173
                    self.id_()
                    self.state = 176 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==11):
                        break

                self.state = 178
                self.match(GameParser.R_SQUARE)
                self.state = 179
                self.match(GameParser.SAMPLES)
                self.state = 180
                self.expression(0)
                self.state = 181
                self.match(GameParser.SEMI)
                pass

            elif la_ == 8:
                localctx = GameParser.AssignmentStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 8)
                self.state = 183
                self.lvalue()
                self.state = 184
                self.match(GameParser.EQUALS)
                self.state = 185
                self.expression(0)
                self.state = 186
                self.match(GameParser.SEMI)
                pass

            elif la_ == 9:
                localctx = GameParser.SampleMinusStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 9)
                self.state = 188
                self.lvalue()
                self.state = 189
                self.match(GameParser.SAMPLES)
                self.state = 190
                self.expression(0)
                self.state = 191
                self.match(GameParser.BACKSLASH)
                self.state = 192
                self.expression(0)
                self.state = 193
                self.match(GameParser.SEMI)
                pass

            elif la_ == 10:
                localctx = GameParser.SampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 10)
                self.state = 195
                self.lvalue()
                self.state = 196
                self.match(GameParser.SAMPLES)
                self.state = 197
                self.expression(0)
                self.state = 198
                self.match(GameParser.SEMI)
                pass

            elif la_ == 11:
                localctx = GameParser.UniqueSampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 11)
                self.state = 200
                self.type_(0)
                self.state = 201
                self.lvalue()
                self.state = 202
                self.match(GameParser.SAMPUNIQ)
                self.state = 203
                self.match(GameParser.L_SQUARE)
                self.state = 204
                self.expression(0)
                self.state = 205
                self.match(GameParser.R_SQUARE)
                self.state = 206
                self.type_(0)
                self.state = 207
                self.match(GameParser.SEMI)
                pass

            elif la_ == 12:
                localctx = GameParser.UniqueSampleNoTypeStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 12)
                self.state = 209
                self.lvalue()
                self.state = 210
                self.match(GameParser.SAMPUNIQ)
                self.state = 211
                self.match(GameParser.L_SQUARE)
                self.state = 212
                self.expression(0)
                self.state = 213
                self.match(GameParser.R_SQUARE)
                self.state = 214
                self.type_(0)
                self.state = 215
                self.match(GameParser.SEMI)
                pass

            elif la_ == 13:
                localctx = GameParser.FunctionCallStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 13)
                self.state = 217
                self.expression(0)
                self.state = 218
                self.match(GameParser.L_PAREN)
                self.state = 220
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & -467794026070736854) != 0) or _la==64 or _la==65:
                    self.state = 219
                    self.argList()


                self.state = 222
                self.match(GameParser.R_PAREN)
                self.state = 223
                self.match(GameParser.SEMI)
                pass

            elif la_ == 14:
                localctx = GameParser.ReturnStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 14)
                self.state = 225
                self.match(GameParser.RETURN)
                self.state = 226
                self.expression(0)
                self.state = 227
                self.match(GameParser.SEMI)
                pass

            elif la_ == 15:
                localctx = GameParser.IfStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 15)
                self.state = 229
                self.match(GameParser.IF)
                self.state = 230
                self.match(GameParser.L_PAREN)
                self.state = 231
                self.expression(0)
                self.state = 232
                self.match(GameParser.R_PAREN)
                self.state = 233
                self.block()
                self.state = 243
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,10,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 234
                        self.match(GameParser.ELSE)
                        self.state = 235
                        self.match(GameParser.IF)
                        self.state = 236
                        self.match(GameParser.L_PAREN)
                        self.state = 237
                        self.expression(0)
                        self.state = 238
                        self.match(GameParser.R_PAREN)
                        self.state = 239
                        self.block() 
                    self.state = 245
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,10,self._ctx)

                self.state = 248
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==54:
                    self.state = 246
                    self.match(GameParser.ELSE)
                    self.state = 247
                    self.block()


                pass

            elif la_ == 16:
                localctx = GameParser.NumericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 16)
                self.state = 250
                self.match(GameParser.FOR)
                self.state = 251
                self.match(GameParser.L_PAREN)
                self.state = 252
                self.match(GameParser.INTTYPE)
                self.state = 253
                self.id_()
                self.state = 254
                self.match(GameParser.EQUALS)
                self.state = 255
                self.expression(0)
                self.state = 256
                self.match(GameParser.TO)
                self.state = 257
                self.expression(0)
                self.state = 258
                self.match(GameParser.R_PAREN)
                self.state = 259
                self.block()
                pass

            elif la_ == 17:
                localctx = GameParser.GenericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 17)
                self.state = 261
                self.match(GameParser.FOR)
                self.state = 262
                self.match(GameParser.L_PAREN)
                self.state = 263
                self.type_(0)
                self.state = 264
                self.id_()
                self.state = 265
                self.match(GameParser.IN)
                self.state = 266
                self.expression(0)
                self.state = 267
                self.match(GameParser.R_PAREN)
                self.state = 268
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
        self.enterRule(localctx, 18, self.RULE_lvalue)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 275
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,13,self._ctx)
            if la_ == 1:
                self.state = 272
                self.id_()
                pass

            elif la_ == 2:
                self.state = 273
                self.parameterizedGame()
                pass

            elif la_ == 3:
                self.state = 274
                self.match(GameParser.THIS)
                pass


            self.state = 285
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,15,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 283
                    self._errHandler.sync(self)
                    token = self._input.LA(1)
                    if token in [12]:
                        self.state = 277
                        self.match(GameParser.PERIOD)
                        self.state = 278
                        self.id_()
                        pass
                    elif token in [3]:
                        self.state = 279
                        self.match(GameParser.L_SQUARE)
                        self.state = 280
                        self.expression(0)
                        self.state = 281
                        self.match(GameParser.R_SQUARE)
                        pass
                    else:
                        raise NoViableAltException(self)
             
                self.state = 287
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,15,self._ctx)

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
        self.enterRule(localctx, 20, self.RULE_methodModifier)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 288
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
        self.enterRule(localctx, 22, self.RULE_methodSignature)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 293
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==57 or _la==58:
                self.state = 290
                self.methodModifier()
                self.state = 295
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 296
            self.type_(0)
            self.state = 297
            self.id_()
            self.state = 298
            self.match(GameParser.L_PAREN)
            self.state = 300
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 3)) & ~0x3f) == 0 and ((1 << (_la - 3)) & 4620765759411322881) != 0):
                self.state = 299
                self.paramList()


            self.state = 302
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
            self.state = 304
            self.variable()
            self.state = 309
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==11:
                self.state = 305
                self.match(GameParser.COMMA)
                self.state = 306
                self.variable()
                self.state = 311
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
        _startState = 26
        self.enterRecursionRule(localctx, 26, self.RULE_expression, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 359
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,23,self._ctx)
            if la_ == 1:
                localctx = GameParser.NotExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 313
                self.match(GameParser.NOT)
                self.state = 314
                self.expression(31)
                pass

            elif la_ == 2:
                localctx = GameParser.SizeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 315
                self.match(GameParser.VBAR)
                self.state = 316
                self.expression(0)
                self.state = 317
                self.match(GameParser.VBAR)
                pass

            elif la_ == 3:
                localctx = GameParser.MinusExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 319
                self.match(GameParser.SUBTRACT)
                self.state = 320
                self.expression(26)
                pass

            elif la_ == 4:
                localctx = GameParser.LvalueExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 321
                self.lvalue()
                pass

            elif la_ == 5:
                localctx = GameParser.CreateTupleExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 322
                self.match(GameParser.L_SQUARE)
                self.state = 331
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & -467794026070736854) != 0) or _la==64 or _la==65:
                    self.state = 323
                    self.expression(0)
                    self.state = 328
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==11:
                        self.state = 324
                        self.match(GameParser.COMMA)
                        self.state = 325
                        self.expression(0)
                        self.state = 330
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 333
                self.match(GameParser.R_SQUARE)
                pass

            elif la_ == 6:
                localctx = GameParser.CreateSetExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 334
                self.match(GameParser.L_CURLY)
                self.state = 343
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & -467794026070736854) != 0) or _la==64 or _la==65:
                    self.state = 335
                    self.expression(0)
                    self.state = 340
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==11:
                        self.state = 336
                        self.match(GameParser.COMMA)
                        self.state = 337
                        self.expression(0)
                        self.state = 342
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 345
                self.match(GameParser.R_CURLY)
                pass

            elif la_ == 7:
                localctx = GameParser.TypeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 346
                self.type_(0)
                pass

            elif la_ == 8:
                localctx = GameParser.ZerosExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 347
                self.match(GameParser.ZEROS_CARET)
                self.state = 348
                self.integerAtom()
                pass

            elif la_ == 9:
                localctx = GameParser.OnesExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 349
                self.match(GameParser.ONES_CARET)
                self.state = 350
                self.integerAtom()
                pass

            elif la_ == 10:
                localctx = GameParser.BinaryNumExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 351
                self.match(GameParser.BINARYNUM)
                pass

            elif la_ == 11:
                localctx = GameParser.IntExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 352
                self.match(GameParser.INT)
                pass

            elif la_ == 12:
                localctx = GameParser.BoolExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 353
                self.bool_()
                pass

            elif la_ == 13:
                localctx = GameParser.NoneExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 354
                self.match(GameParser.NONE)
                pass

            elif la_ == 14:
                localctx = GameParser.ParenExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 355
                self.match(GameParser.L_PAREN)
                self.state = 356
                self.expression(0)
                self.state = 357
                self.match(GameParser.R_PAREN)
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 427
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,26,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 425
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,25,self._ctx)
                    if la_ == 1:
                        localctx = GameParser.ExponentiationExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 361
                        if not self.precpred(self._ctx, 29):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 29)")
                        self.state = 362
                        self.match(GameParser.CARET)
                        self.state = 363
                        self.expression(29)
                        pass

                    elif la_ == 2:
                        localctx = GameParser.MultiplyExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 364
                        if not self.precpred(self._ctx, 28):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 28)")
                        self.state = 365
                        self.match(GameParser.TIMES)
                        self.state = 366
                        self.expression(29)
                        pass

                    elif la_ == 3:
                        localctx = GameParser.DivideExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 367
                        if not self.precpred(self._ctx, 27):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 27)")
                        self.state = 368
                        self.match(GameParser.DIVIDE)
                        self.state = 369
                        self.expression(28)
                        pass

                    elif la_ == 4:
                        localctx = GameParser.AddExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 370
                        if not self.precpred(self._ctx, 25):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 25)")
                        self.state = 371
                        self.match(GameParser.PLUS)
                        self.state = 372
                        self.expression(26)
                        pass

                    elif la_ == 5:
                        localctx = GameParser.SubtractExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 373
                        if not self.precpred(self._ctx, 24):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 24)")
                        self.state = 374
                        self.match(GameParser.SUBTRACT)
                        self.state = 375
                        self.expression(25)
                        pass

                    elif la_ == 6:
                        localctx = GameParser.EqualsExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 376
                        if not self.precpred(self._ctx, 23):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 23)")
                        self.state = 377
                        self.match(GameParser.EQUALSCOMPARE)
                        self.state = 378
                        self.expression(24)
                        pass

                    elif la_ == 7:
                        localctx = GameParser.NotEqualsExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 379
                        if not self.precpred(self._ctx, 22):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 22)")
                        self.state = 380
                        self.match(GameParser.NOTEQUALS)
                        self.state = 381
                        self.expression(23)
                        pass

                    elif la_ == 8:
                        localctx = GameParser.GtExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 382
                        if not self.precpred(self._ctx, 21):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 21)")
                        self.state = 383
                        self.match(GameParser.R_ANGLE)
                        self.state = 384
                        self.expression(22)
                        pass

                    elif la_ == 9:
                        localctx = GameParser.LtExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 385
                        if not self.precpred(self._ctx, 20):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 20)")
                        self.state = 386
                        self.match(GameParser.L_ANGLE)
                        self.state = 387
                        self.expression(21)
                        pass

                    elif la_ == 10:
                        localctx = GameParser.GeqExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 388
                        if not self.precpred(self._ctx, 19):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 19)")
                        self.state = 389
                        self.match(GameParser.GEQ)
                        self.state = 390
                        self.expression(20)
                        pass

                    elif la_ == 11:
                        localctx = GameParser.LeqExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 391
                        if not self.precpred(self._ctx, 18):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 18)")
                        self.state = 392
                        self.match(GameParser.LEQ)
                        self.state = 393
                        self.expression(19)
                        pass

                    elif la_ == 12:
                        localctx = GameParser.InExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 394
                        if not self.precpred(self._ctx, 17):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 17)")
                        self.state = 395
                        self.match(GameParser.IN)
                        self.state = 396
                        self.expression(18)
                        pass

                    elif la_ == 13:
                        localctx = GameParser.SubsetsExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 397
                        if not self.precpred(self._ctx, 16):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 16)")
                        self.state = 398
                        self.match(GameParser.SUBSETS)
                        self.state = 399
                        self.expression(17)
                        pass

                    elif la_ == 14:
                        localctx = GameParser.AndExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 400
                        if not self.precpred(self._ctx, 15):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 15)")
                        self.state = 401
                        self.match(GameParser.AND)
                        self.state = 402
                        self.expression(16)
                        pass

                    elif la_ == 15:
                        localctx = GameParser.OrExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 403
                        if not self.precpred(self._ctx, 14):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 14)")
                        self.state = 404
                        self.match(GameParser.OR)
                        self.state = 405
                        self.expression(15)
                        pass

                    elif la_ == 16:
                        localctx = GameParser.UnionExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 406
                        if not self.precpred(self._ctx, 13):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 13)")
                        self.state = 407
                        self.match(GameParser.UNION)
                        self.state = 408
                        self.expression(14)
                        pass

                    elif la_ == 17:
                        localctx = GameParser.SetMinusExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 409
                        if not self.precpred(self._ctx, 12):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 12)")
                        self.state = 410
                        self.match(GameParser.BACKSLASH)
                        self.state = 411
                        self.expression(13)
                        pass

                    elif la_ == 18:
                        localctx = GameParser.FnCallExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 412
                        if not self.precpred(self._ctx, 33):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 33)")
                        self.state = 413
                        self.match(GameParser.L_PAREN)
                        self.state = 415
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)
                        if (((_la) & ~0x3f) == 0 and ((1 << _la) & -467794026070736854) != 0) or _la==64 or _la==65:
                            self.state = 414
                            self.argList()


                        self.state = 417
                        self.match(GameParser.R_PAREN)
                        pass

                    elif la_ == 19:
                        localctx = GameParser.SliceExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 418
                        if not self.precpred(self._ctx, 32):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 32)")
                        self.state = 419
                        self.match(GameParser.L_SQUARE)
                        self.state = 420
                        self.integerExpression(0)
                        self.state = 421
                        self.match(GameParser.COLON)
                        self.state = 422
                        self.integerExpression(0)
                        self.state = 423
                        self.match(GameParser.R_SQUARE)
                        pass

             
                self.state = 429
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,26,self._ctx)

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
            self.state = 430
            self.expression(0)
            self.state = 435
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==11:
                self.state = 431
                self.match(GameParser.COMMA)
                self.state = 432
                self.expression(0)
                self.state = 437
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
            self.state = 438
            self.type_(0)
            self.state = 439
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

        def id_(self):
            return self.getTypedRuleContext(GameParser.IdContext,0)


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
        self.enterRule(localctx, 32, self.RULE_parameterizedGame)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 441
            self.id_()
            self.state = 442
            self.match(GameParser.L_PAREN)
            self.state = 444
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & -467794026070736854) != 0) or _la==64 or _la==65:
                self.state = 443
                self.argList()


            self.state = 446
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


    class GroupTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def GROUP(self):
            return self.getToken(GameParser.GROUP, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGroupType" ):
                return visitor.visitGroupType(self)
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


    class GroupElemTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def groupelem(self):
            return self.getTypedRuleContext(GameParser.GroupelemContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGroupElemType" ):
                return visitor.visitGroupElemType(self)
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


    class FunctionTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def FUNCTION(self):
            return self.getToken(GameParser.FUNCTION, 0)
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
            if hasattr( visitor, "visitFunctionType" ):
                return visitor.visitFunctionType(self)
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
        _startState = 34
        self.enterRecursionRule(localctx, 34, self.RULE_type, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 489
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,30,self._ctx)
            if la_ == 1:
                localctx = GameParser.SetTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 449
                self.set_()
                pass

            elif la_ == 2:
                localctx = GameParser.BoolTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 450
                self.match(GameParser.BOOL)
                pass

            elif la_ == 3:
                localctx = GameParser.VoidTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 451
                self.match(GameParser.VOID)
                pass

            elif la_ == 4:
                localctx = GameParser.MapTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 452
                self.match(GameParser.MAP)
                self.state = 453
                self.match(GameParser.L_ANGLE)
                self.state = 454
                self.type_(0)
                self.state = 455
                self.match(GameParser.COMMA)
                self.state = 456
                self.type_(0)
                self.state = 457
                self.match(GameParser.R_ANGLE)
                pass

            elif la_ == 5:
                localctx = GameParser.ArrayTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 459
                self.match(GameParser.ARRAY)
                self.state = 460
                self.match(GameParser.L_ANGLE)
                self.state = 461
                self.type_(0)
                self.state = 462
                self.match(GameParser.COMMA)
                self.state = 463
                self.integerExpression(0)
                self.state = 464
                self.match(GameParser.R_ANGLE)
                pass

            elif la_ == 6:
                localctx = GameParser.FunctionTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 466
                self.match(GameParser.FUNCTION)
                self.state = 467
                self.match(GameParser.L_ANGLE)
                self.state = 468
                self.type_(0)
                self.state = 469
                self.match(GameParser.COMMA)
                self.state = 470
                self.type_(0)
                self.state = 471
                self.match(GameParser.R_ANGLE)
                pass

            elif la_ == 7:
                localctx = GameParser.IntTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 473
                self.match(GameParser.INTTYPE)
                pass

            elif la_ == 8:
                localctx = GameParser.ProductTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 474
                self.match(GameParser.L_SQUARE)
                self.state = 475
                self.type_(0)
                self.state = 478 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 476
                    self.match(GameParser.COMMA)
                    self.state = 477
                    self.type_(0)
                    self.state = 480 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==11):
                        break

                self.state = 482
                self.match(GameParser.R_SQUARE)
                pass

            elif la_ == 9:
                localctx = GameParser.BitStringTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 484
                self.bitstring()
                pass

            elif la_ == 10:
                localctx = GameParser.ModIntTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 485
                self.modint()
                pass

            elif la_ == 11:
                localctx = GameParser.GroupElemTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 486
                self.groupelem()
                pass

            elif la_ == 12:
                localctx = GameParser.GroupTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 487
                self.match(GameParser.GROUP)
                pass

            elif la_ == 13:
                localctx = GameParser.LvalueTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 488
                self.lvalue()
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 495
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,31,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = GameParser.OptionalTypeContext(self, GameParser.TypeContext(self, _parentctx, _parentState))
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_type)
                    self.state = 491
                    if not self.precpred(self._ctx, 14):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 14)")
                    self.state = 492
                    self.match(GameParser.QUESTION) 
                self.state = 497
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,31,self._ctx)

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
        _startState = 36
        self.enterRecursionRule(localctx, 36, self.RULE_integerExpression, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 506
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [40, 41, 49, 56, 65]:
                self.state = 499
                self.lvalue()
                pass
            elif token in [64]:
                self.state = 500
                self.match(GameParser.INT)
                pass
            elif token in [61]:
                self.state = 501
                self.match(GameParser.BINARYNUM)
                pass
            elif token in [5]:
                self.state = 502
                self.match(GameParser.L_PAREN)
                self.state = 503
                self.integerExpression(0)
                self.state = 504
                self.match(GameParser.R_PAREN)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 522
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,34,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 520
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,33,self._ctx)
                    if la_ == 1:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 508
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 8)")
                        self.state = 509
                        self.match(GameParser.TIMES)
                        self.state = 510
                        self.integerExpression(9)
                        pass

                    elif la_ == 2:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 511
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 7)")
                        self.state = 512
                        self.match(GameParser.DIVIDE)
                        self.state = 513
                        self.integerExpression(8)
                        pass

                    elif la_ == 3:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 514
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 6)")
                        self.state = 515
                        self.match(GameParser.PLUS)
                        self.state = 516
                        self.integerExpression(7)
                        pass

                    elif la_ == 4:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 517
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 5)")
                        self.state = 518
                        self.match(GameParser.SUBTRACT)
                        self.state = 519
                        self.integerExpression(6)
                        pass

             
                self.state = 524
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,34,self._ctx)

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
        self.enterRule(localctx, 38, self.RULE_integerAtom)
        try:
            self.state = 531
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [40, 41, 49, 56, 65]:
                self.enterOuterAlt(localctx, 1)
                self.state = 525
                self.lvalue()
                pass
            elif token in [64]:
                self.enterOuterAlt(localctx, 2)
                self.state = 526
                self.match(GameParser.INT)
                pass
            elif token in [5]:
                self.enterOuterAlt(localctx, 3)
                self.state = 527
                self.match(GameParser.L_PAREN)
                self.state = 528
                self.integerExpression(0)
                self.state = 529
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
        self.enterRule(localctx, 40, self.RULE_bitstring)
        try:
            self.state = 539
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,36,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 533
                self.match(GameParser.BITSTRING)
                self.state = 534
                self.match(GameParser.L_ANGLE)
                self.state = 535
                self.integerExpression(0)
                self.state = 536
                self.match(GameParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 538
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
        self.enterRule(localctx, 42, self.RULE_modint)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 541
            self.match(GameParser.MODINT)
            self.state = 542
            self.match(GameParser.L_ANGLE)
            self.state = 543
            self.integerExpression(0)
            self.state = 544
            self.match(GameParser.R_ANGLE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class GroupelemContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def GROUPELEM(self):
            return self.getToken(GameParser.GROUPELEM, 0)

        def L_ANGLE(self):
            return self.getToken(GameParser.L_ANGLE, 0)

        def lvalue(self):
            return self.getTypedRuleContext(GameParser.LvalueContext,0)


        def R_ANGLE(self):
            return self.getToken(GameParser.R_ANGLE, 0)

        def getRuleIndex(self):
            return GameParser.RULE_groupelem

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGroupelem" ):
                return visitor.visitGroupelem(self)
            else:
                return visitor.visitChildren(self)




    def groupelem(self):

        localctx = GameParser.GroupelemContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_groupelem)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 546
            self.match(GameParser.GROUPELEM)
            self.state = 547
            self.match(GameParser.L_ANGLE)
            self.state = 548
            self.lvalue()
            self.state = 549
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
            self.state = 557
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,37,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 551
                self.match(GameParser.SET)
                self.state = 552
                self.match(GameParser.L_ANGLE)
                self.state = 553
                self.type_(0)
                self.state = 554
                self.match(GameParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 556
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
            self.state = 559
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
            self.state = 561
            self.match(GameParser.IMPORT)
            self.state = 562
            self.match(GameParser.FILESTRING)
            self.state = 565
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==53:
                self.state = 563
                self.match(GameParser.AS)
                self.state = 564
                self.match(GameParser.ID)


            self.state = 567
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

        def GROUP(self):
            return self.getToken(GameParser.GROUP, 0)

        def GROUPELEM(self):
            return self.getToken(GameParser.GROUPELEM, 0)

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
            self.state = 569
            _la = self._input.LA(1)
            if not(((((_la - 40)) & ~0x3f) == 0 and ((1 << (_la - 40)) & 33554947) != 0)):
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
        self._predicates[17] = self.type_sempred
        self._predicates[18] = self.integerExpression_sempred
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
                return self.precpred(self._ctx, 14)
         

    def integerExpression_sempred(self, localctx:IntegerExpressionContext, predIndex:int):
            if predIndex == 20:
                return self.precpred(self._ctx, 8)
         

            if predIndex == 21:
                return self.precpred(self._ctx, 7)
         

            if predIndex == 22:
                return self.precpred(self._ctx, 6)
         

            if predIndex == 23:
                return self.precpred(self._ctx, 5)
         




