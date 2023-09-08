# Generated from src/antlr/Game.g4 by ANTLR 4.13.0
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
        4,1,55,518,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,1,0,5,0,46,8,0,10,0,12,0,49,9,0,1,0,1,0,1,0,1,0,1,
        0,1,1,1,1,1,1,1,1,3,1,60,8,1,1,1,1,1,1,1,1,1,1,1,1,2,1,2,1,2,5,2,
        70,8,2,10,2,12,2,73,9,2,1,2,1,2,1,2,4,2,78,8,2,11,2,12,2,79,1,2,
        1,2,1,2,5,2,85,8,2,10,2,12,2,88,9,2,1,2,1,2,1,2,5,2,93,8,2,10,2,
        12,2,96,9,2,1,2,4,2,99,8,2,11,2,12,2,100,3,2,103,8,2,1,3,1,3,1,3,
        1,3,1,3,4,3,110,8,3,11,3,12,3,111,1,3,1,3,1,3,1,3,1,3,1,3,5,3,120,
        8,3,10,3,12,3,123,9,3,1,3,1,3,1,3,1,3,1,4,1,4,1,4,1,4,1,4,1,4,1,
        4,1,4,1,4,1,4,1,5,1,5,1,5,3,5,142,8,5,1,6,1,6,1,6,1,6,1,7,1,7,1,
        7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,
        7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,1,7,3,7,177,8,7,1,7,1,7,1,
        7,3,7,182,8,7,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,5,8,195,
        8,8,10,8,12,8,198,9,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,5,8,208,8,
        8,10,8,12,8,211,9,8,1,8,1,8,5,8,215,8,8,10,8,12,8,218,9,8,1,8,1,
        8,1,8,5,8,223,8,8,10,8,12,8,226,9,8,1,8,3,8,229,8,8,1,8,1,8,1,8,
        1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,5,8,242,8,8,10,8,12,8,245,9,8,1,
        8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,5,8,258,8,8,10,8,12,8,
        261,9,8,1,8,1,8,3,8,265,8,8,1,9,1,9,1,9,1,9,1,9,1,9,1,9,5,9,274,
        8,9,10,9,12,9,277,9,9,1,10,1,10,1,10,1,10,3,10,283,8,10,1,10,1,10,
        1,11,1,11,1,11,5,11,290,8,11,10,11,12,11,293,9,11,1,12,1,12,1,12,
        1,12,5,12,299,8,12,10,12,12,12,302,9,12,1,12,1,12,1,12,1,12,1,12,
        1,12,1,12,1,12,5,12,312,8,12,10,12,12,12,315,9,12,3,12,317,8,12,
        1,12,1,12,1,12,1,12,1,12,5,12,324,8,12,10,12,12,12,327,9,12,3,12,
        329,8,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,3,12,
        341,8,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,
        1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,
        1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,
        1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,
        1,12,3,12,394,8,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,
        1,12,1,12,1,12,1,12,5,12,409,8,12,10,12,12,12,412,9,12,1,13,1,13,
        1,13,5,13,417,8,13,10,13,12,13,420,9,13,1,14,1,14,1,14,1,15,1,15,
        1,15,1,15,1,15,1,15,1,15,1,15,1,15,1,15,1,15,1,15,1,15,1,15,1,15,
        1,15,1,15,1,15,1,15,1,15,3,15,445,8,15,1,15,1,15,1,15,1,15,1,15,
        4,15,452,8,15,11,15,12,15,453,5,15,456,8,15,10,15,12,15,459,9,15,
        1,16,1,16,1,16,1,16,3,16,465,8,16,1,16,1,16,1,16,1,16,1,16,1,16,
        1,16,1,16,1,16,1,16,1,16,1,16,5,16,479,8,16,10,16,12,16,482,9,16,
        1,17,1,17,1,17,1,17,1,17,1,17,3,17,490,8,17,1,18,1,18,1,18,1,18,
        1,18,1,18,3,18,498,8,18,1,19,1,19,1,19,1,19,3,19,504,8,19,1,19,1,
        19,1,20,1,20,4,20,510,8,20,11,20,12,20,511,1,20,1,20,1,21,1,21,1,
        21,0,3,24,30,32,22,0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,
        34,36,38,40,42,0,1,2,0,42,42,52,52,580,0,47,1,0,0,0,2,55,1,0,0,0,
        4,102,1,0,0,0,6,104,1,0,0,0,8,128,1,0,0,0,10,138,1,0,0,0,12,143,
        1,0,0,0,14,181,1,0,0,0,16,264,1,0,0,0,18,266,1,0,0,0,20,278,1,0,
        0,0,22,286,1,0,0,0,24,340,1,0,0,0,26,413,1,0,0,0,28,421,1,0,0,0,
        30,444,1,0,0,0,32,464,1,0,0,0,34,489,1,0,0,0,36,497,1,0,0,0,38,499,
        1,0,0,0,40,507,1,0,0,0,42,515,1,0,0,0,44,46,3,38,19,0,45,44,1,0,
        0,0,46,49,1,0,0,0,47,45,1,0,0,0,47,48,1,0,0,0,48,50,1,0,0,0,49,47,
        1,0,0,0,50,51,3,2,1,0,51,52,3,2,1,0,52,53,3,8,4,0,53,54,5,0,0,1,
        54,1,1,0,0,0,55,56,5,44,0,0,56,57,5,52,0,0,57,59,5,5,0,0,58,60,3,
        22,11,0,59,58,1,0,0,0,59,60,1,0,0,0,60,61,1,0,0,0,61,62,5,6,0,0,
        62,63,5,1,0,0,63,64,3,4,2,0,64,65,5,2,0,0,65,3,1,0,0,0,66,67,3,10,
        5,0,67,68,5,9,0,0,68,70,1,0,0,0,69,66,1,0,0,0,70,73,1,0,0,0,71,69,
        1,0,0,0,71,72,1,0,0,0,72,77,1,0,0,0,73,71,1,0,0,0,74,75,3,20,10,
        0,75,76,3,40,20,0,76,78,1,0,0,0,77,74,1,0,0,0,78,79,1,0,0,0,79,77,
        1,0,0,0,79,80,1,0,0,0,80,103,1,0,0,0,81,82,3,10,5,0,82,83,5,9,0,
        0,83,85,1,0,0,0,84,81,1,0,0,0,85,88,1,0,0,0,86,84,1,0,0,0,86,87,
        1,0,0,0,87,94,1,0,0,0,88,86,1,0,0,0,89,90,3,20,10,0,90,91,3,40,20,
        0,91,93,1,0,0,0,92,89,1,0,0,0,93,96,1,0,0,0,94,92,1,0,0,0,94,95,
        1,0,0,0,95,98,1,0,0,0,96,94,1,0,0,0,97,99,3,6,3,0,98,97,1,0,0,0,
        99,100,1,0,0,0,100,98,1,0,0,0,100,101,1,0,0,0,101,103,1,0,0,0,102,
        71,1,0,0,0,102,86,1,0,0,0,103,5,1,0,0,0,104,105,5,47,0,0,105,109,
        5,1,0,0,106,107,3,20,10,0,107,108,3,40,20,0,108,110,1,0,0,0,109,
        106,1,0,0,0,110,111,1,0,0,0,111,109,1,0,0,0,111,112,1,0,0,0,112,
        113,1,0,0,0,113,114,5,48,0,0,114,115,5,10,0,0,115,116,5,3,0,0,116,
        121,3,42,21,0,117,118,5,11,0,0,118,120,3,42,21,0,119,117,1,0,0,0,
        120,123,1,0,0,0,121,119,1,0,0,0,121,122,1,0,0,0,122,124,1,0,0,0,
        123,121,1,0,0,0,124,125,5,4,0,0,125,126,5,9,0,0,126,127,5,2,0,0,
        127,7,1,0,0,0,128,129,5,45,0,0,129,130,5,5,0,0,130,131,5,52,0,0,
        131,132,5,11,0,0,132,133,5,52,0,0,133,134,5,6,0,0,134,135,5,46,0,
        0,135,136,5,52,0,0,136,137,5,9,0,0,137,9,1,0,0,0,138,141,3,28,14,
        0,139,140,5,14,0,0,140,142,3,24,12,0,141,139,1,0,0,0,141,142,1,0,
        0,0,142,11,1,0,0,0,143,144,3,28,14,0,144,145,5,14,0,0,145,146,3,
        24,12,0,146,13,1,0,0,0,147,148,3,30,15,0,148,149,3,42,21,0,149,150,
        5,9,0,0,150,182,1,0,0,0,151,152,3,30,15,0,152,153,3,18,9,0,153,154,
        5,14,0,0,154,155,3,24,12,0,155,156,5,9,0,0,156,182,1,0,0,0,157,158,
        3,30,15,0,158,159,3,18,9,0,159,160,5,24,0,0,160,161,3,24,12,0,161,
        162,5,9,0,0,162,182,1,0,0,0,163,164,3,18,9,0,164,165,5,14,0,0,165,
        166,3,24,12,0,166,167,5,9,0,0,167,182,1,0,0,0,168,169,3,18,9,0,169,
        170,5,24,0,0,170,171,3,24,12,0,171,172,5,9,0,0,172,182,1,0,0,0,173,
        174,3,24,12,0,174,176,5,5,0,0,175,177,3,26,13,0,176,175,1,0,0,0,
        176,177,1,0,0,0,177,178,1,0,0,0,178,179,5,6,0,0,179,180,5,9,0,0,
        180,182,1,0,0,0,181,147,1,0,0,0,181,151,1,0,0,0,181,157,1,0,0,0,
        181,163,1,0,0,0,181,168,1,0,0,0,181,173,1,0,0,0,182,15,1,0,0,0,183,
        265,3,14,7,0,184,185,5,33,0,0,185,186,3,24,12,0,186,187,5,9,0,0,
        187,265,1,0,0,0,188,189,5,39,0,0,189,190,5,5,0,0,190,191,3,24,12,
        0,191,192,5,6,0,0,192,196,5,1,0,0,193,195,3,16,8,0,194,193,1,0,0,
        0,195,198,1,0,0,0,196,194,1,0,0,0,196,197,1,0,0,0,197,199,1,0,0,
        0,198,196,1,0,0,0,199,216,5,2,0,0,200,201,5,49,0,0,201,202,5,39,
        0,0,202,203,5,5,0,0,203,204,3,24,12,0,204,205,5,6,0,0,205,209,5,
        1,0,0,206,208,3,16,8,0,207,206,1,0,0,0,208,211,1,0,0,0,209,207,1,
        0,0,0,209,210,1,0,0,0,210,212,1,0,0,0,211,209,1,0,0,0,212,213,5,
        2,0,0,213,215,1,0,0,0,214,200,1,0,0,0,215,218,1,0,0,0,216,214,1,
        0,0,0,216,217,1,0,0,0,217,228,1,0,0,0,218,216,1,0,0,0,219,220,5,
        49,0,0,220,224,5,1,0,0,221,223,3,16,8,0,222,221,1,0,0,0,223,226,
        1,0,0,0,224,222,1,0,0,0,224,225,1,0,0,0,225,227,1,0,0,0,226,224,
        1,0,0,0,227,229,5,2,0,0,228,219,1,0,0,0,228,229,1,0,0,0,229,265,
        1,0,0,0,230,231,5,40,0,0,231,232,5,5,0,0,232,233,5,31,0,0,233,234,
        3,42,21,0,234,235,5,14,0,0,235,236,3,24,12,0,236,237,5,41,0,0,237,
        238,3,24,12,0,238,239,5,6,0,0,239,243,5,1,0,0,240,242,3,16,8,0,241,
        240,1,0,0,0,242,245,1,0,0,0,243,241,1,0,0,0,243,244,1,0,0,0,244,
        246,1,0,0,0,245,243,1,0,0,0,246,247,5,2,0,0,247,265,1,0,0,0,248,
        249,5,40,0,0,249,250,5,5,0,0,250,251,3,30,15,0,251,252,3,42,21,0,
        252,253,5,42,0,0,253,254,3,24,12,0,254,255,5,6,0,0,255,259,5,1,0,
        0,256,258,3,16,8,0,257,256,1,0,0,0,258,261,1,0,0,0,259,257,1,0,0,
        0,259,260,1,0,0,0,260,262,1,0,0,0,261,259,1,0,0,0,262,263,5,2,0,
        0,263,265,1,0,0,0,264,183,1,0,0,0,264,184,1,0,0,0,264,188,1,0,0,
        0,264,230,1,0,0,0,264,248,1,0,0,0,265,17,1,0,0,0,266,275,3,42,21,
        0,267,268,5,12,0,0,268,274,3,42,21,0,269,270,5,3,0,0,270,271,3,32,
        16,0,271,272,5,4,0,0,272,274,1,0,0,0,273,267,1,0,0,0,273,269,1,0,
        0,0,274,277,1,0,0,0,275,273,1,0,0,0,275,276,1,0,0,0,276,19,1,0,0,
        0,277,275,1,0,0,0,278,279,3,30,15,0,279,280,3,42,21,0,280,282,5,
        5,0,0,281,283,3,22,11,0,282,281,1,0,0,0,282,283,1,0,0,0,283,284,
        1,0,0,0,284,285,5,6,0,0,285,21,1,0,0,0,286,291,3,28,14,0,287,288,
        5,11,0,0,288,290,3,28,14,0,289,287,1,0,0,0,290,293,1,0,0,0,291,289,
        1,0,0,0,291,292,1,0,0,0,292,23,1,0,0,0,293,291,1,0,0,0,294,295,6,
        12,-1,0,295,300,5,52,0,0,296,297,5,12,0,0,297,299,5,52,0,0,298,296,
        1,0,0,0,299,302,1,0,0,0,300,298,1,0,0,0,300,301,1,0,0,0,301,341,
        1,0,0,0,302,300,1,0,0,0,303,304,5,28,0,0,304,305,3,24,12,0,305,306,
        5,28,0,0,306,341,1,0,0,0,307,316,5,3,0,0,308,313,3,24,12,0,309,310,
        5,11,0,0,310,312,3,24,12,0,311,309,1,0,0,0,312,315,1,0,0,0,313,311,
        1,0,0,0,313,314,1,0,0,0,314,317,1,0,0,0,315,313,1,0,0,0,316,308,
        1,0,0,0,316,317,1,0,0,0,317,318,1,0,0,0,318,341,5,4,0,0,319,328,
        5,1,0,0,320,325,3,24,12,0,321,322,5,11,0,0,322,324,3,24,12,0,323,
        321,1,0,0,0,324,327,1,0,0,0,325,323,1,0,0,0,325,326,1,0,0,0,326,
        329,1,0,0,0,327,325,1,0,0,0,328,320,1,0,0,0,328,329,1,0,0,0,329,
        330,1,0,0,0,330,341,5,2,0,0,331,341,3,30,15,0,332,341,5,50,0,0,333,
        341,5,51,0,0,334,335,5,27,0,0,335,341,3,24,12,2,336,337,5,5,0,0,
        337,338,3,24,12,0,338,339,5,6,0,0,339,341,1,0,0,0,340,294,1,0,0,
        0,340,303,1,0,0,0,340,307,1,0,0,0,340,319,1,0,0,0,340,331,1,0,0,
        0,340,332,1,0,0,0,340,333,1,0,0,0,340,334,1,0,0,0,340,336,1,0,0,
        0,341,410,1,0,0,0,342,343,10,28,0,0,343,344,5,19,0,0,344,409,3,24,
        12,29,345,346,10,27,0,0,346,347,5,20,0,0,347,409,3,24,12,28,348,
        349,10,26,0,0,349,350,5,8,0,0,350,409,3,24,12,27,351,352,10,25,0,
        0,352,353,5,7,0,0,353,409,3,24,12,26,354,355,10,24,0,0,355,356,5,
        21,0,0,356,409,3,24,12,25,357,358,10,23,0,0,358,359,5,22,0,0,359,
        409,3,24,12,24,360,361,10,22,0,0,361,362,5,25,0,0,362,409,3,24,12,
        23,363,364,10,21,0,0,364,365,5,38,0,0,365,409,3,24,12,22,366,367,
        10,20,0,0,367,368,5,42,0,0,368,409,3,24,12,21,369,370,10,19,0,0,
        370,371,5,23,0,0,371,409,3,24,12,20,372,373,10,18,0,0,373,374,5,
        43,0,0,374,409,3,24,12,19,375,376,10,17,0,0,376,377,5,26,0,0,377,
        409,3,24,12,18,378,379,10,16,0,0,379,380,5,15,0,0,380,409,3,24,12,
        17,381,382,10,15,0,0,382,383,5,16,0,0,383,409,3,24,12,16,384,385,
        10,14,0,0,385,386,5,13,0,0,386,409,3,24,12,15,387,388,10,13,0,0,
        388,389,5,17,0,0,389,409,3,24,12,14,390,391,10,10,0,0,391,393,5,
        5,0,0,392,394,3,26,13,0,393,392,1,0,0,0,393,394,1,0,0,0,394,395,
        1,0,0,0,395,409,5,6,0,0,396,397,10,9,0,0,397,398,5,3,0,0,398,399,
        3,32,16,0,399,400,5,10,0,0,400,401,3,32,16,0,401,402,5,4,0,0,402,
        409,1,0,0,0,403,404,10,8,0,0,404,405,5,3,0,0,405,406,3,32,16,0,406,
        407,5,4,0,0,407,409,1,0,0,0,408,342,1,0,0,0,408,345,1,0,0,0,408,
        348,1,0,0,0,408,351,1,0,0,0,408,354,1,0,0,0,408,357,1,0,0,0,408,
        360,1,0,0,0,408,363,1,0,0,0,408,366,1,0,0,0,408,369,1,0,0,0,408,
        372,1,0,0,0,408,375,1,0,0,0,408,378,1,0,0,0,408,381,1,0,0,0,408,
        384,1,0,0,0,408,387,1,0,0,0,408,390,1,0,0,0,408,396,1,0,0,0,408,
        403,1,0,0,0,409,412,1,0,0,0,410,408,1,0,0,0,410,411,1,0,0,0,411,
        25,1,0,0,0,412,410,1,0,0,0,413,418,3,24,12,0,414,415,5,11,0,0,415,
        417,3,24,12,0,416,414,1,0,0,0,417,420,1,0,0,0,418,416,1,0,0,0,418,
        419,1,0,0,0,419,27,1,0,0,0,420,418,1,0,0,0,421,422,3,30,15,0,422,
        423,3,42,21,0,423,29,1,0,0,0,424,425,6,15,-1,0,425,445,3,36,18,0,
        426,445,5,30,0,0,427,428,5,32,0,0,428,429,5,7,0,0,429,430,3,30,15,
        0,430,431,5,11,0,0,431,432,3,30,15,0,432,433,5,8,0,0,433,445,1,0,
        0,0,434,435,5,36,0,0,435,436,5,7,0,0,436,437,3,30,15,0,437,438,5,
        11,0,0,438,439,3,32,16,0,439,440,5,8,0,0,440,445,1,0,0,0,441,445,
        5,31,0,0,442,445,3,18,9,0,443,445,3,34,17,0,444,424,1,0,0,0,444,
        426,1,0,0,0,444,427,1,0,0,0,444,434,1,0,0,0,444,441,1,0,0,0,444,
        442,1,0,0,0,444,443,1,0,0,0,445,457,1,0,0,0,446,447,10,9,0,0,447,
        456,5,18,0,0,448,451,10,3,0,0,449,450,5,13,0,0,450,452,3,30,15,0,
        451,449,1,0,0,0,452,453,1,0,0,0,453,451,1,0,0,0,453,454,1,0,0,0,
        454,456,1,0,0,0,455,446,1,0,0,0,455,448,1,0,0,0,456,459,1,0,0,0,
        457,455,1,0,0,0,457,458,1,0,0,0,458,31,1,0,0,0,459,457,1,0,0,0,460,
        461,6,16,-1,0,461,465,3,18,9,0,462,465,5,50,0,0,463,465,5,51,0,0,
        464,460,1,0,0,0,464,462,1,0,0,0,464,463,1,0,0,0,465,480,1,0,0,0,
        466,467,10,4,0,0,467,468,5,15,0,0,468,479,3,32,16,5,469,470,10,3,
        0,0,470,471,5,13,0,0,471,479,3,32,16,4,472,473,10,2,0,0,473,474,
        5,16,0,0,474,479,3,32,16,3,475,476,10,1,0,0,476,477,5,17,0,0,477,
        479,3,32,16,2,478,466,1,0,0,0,478,469,1,0,0,0,478,472,1,0,0,0,478,
        475,1,0,0,0,479,482,1,0,0,0,480,478,1,0,0,0,480,481,1,0,0,0,481,
        33,1,0,0,0,482,480,1,0,0,0,483,490,5,35,0,0,484,485,5,35,0,0,485,
        486,5,7,0,0,486,487,3,32,16,0,487,488,5,8,0,0,488,490,1,0,0,0,489,
        483,1,0,0,0,489,484,1,0,0,0,490,35,1,0,0,0,491,492,5,29,0,0,492,
        493,5,7,0,0,493,494,3,30,15,0,494,495,5,8,0,0,495,498,1,0,0,0,496,
        498,5,29,0,0,497,491,1,0,0,0,497,496,1,0,0,0,498,37,1,0,0,0,499,
        500,5,34,0,0,500,503,5,55,0,0,501,502,5,46,0,0,502,504,5,52,0,0,
        503,501,1,0,0,0,503,504,1,0,0,0,504,505,1,0,0,0,505,506,5,9,0,0,
        506,39,1,0,0,0,507,509,5,1,0,0,508,510,3,16,8,0,509,508,1,0,0,0,
        510,511,1,0,0,0,511,509,1,0,0,0,511,512,1,0,0,0,512,513,1,0,0,0,
        513,514,5,2,0,0,514,41,1,0,0,0,515,516,7,0,0,0,516,43,1,0,0,0,46,
        47,59,71,79,86,94,100,102,111,121,141,176,181,196,209,216,224,228,
        243,259,264,273,275,282,291,300,313,316,325,328,340,393,408,410,
        418,444,453,455,457,464,478,480,489,497,503,511
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
                     "'export'", "'as'", "'Phase'", "'oracles'", "'else'" ]

    symbolicNames = [ "<INVALID>", "L_CURLY", "R_CURLY", "L_SQUARE", "R_SQUARE", 
                      "L_PAREN", "R_PAREN", "L_ANGLE", "R_ANGLE", "SEMI", 
                      "COLON", "COMMA", "PERIOD", "TIMES", "EQUALS", "PLUS", 
                      "SUBTRACT", "DIVIDE", "QUESTION", "EQUALSCOMPARE", 
                      "NOTEQUALS", "GEQ", "LEQ", "CONCATENATE", "SAMPLES", 
                      "AND", "BACKSLASH", "NOT", "VBAR", "SET", "BOOL", 
                      "INTTYPE", "MAP", "RETURN", "IMPORT", "BITSTRING", 
                      "ARRAY", "PRIMITIVE", "SUBSETS", "IF", "FOR", "TO", 
                      "IN", "UNION", "GAME", "EXPORT", "AS", "PHASE", "ORACLES", 
                      "ELSE", "BINARYNUM", "INT", "ID", "WS", "LINE_COMMENT", 
                      "FILESTRING" ]

    RULE_program = 0
    RULE_game = 1
    RULE_gameBody = 2
    RULE_gamePhase = 3
    RULE_gameExport = 4
    RULE_field = 5
    RULE_initializedField = 6
    RULE_simpleStatement = 7
    RULE_statement = 8
    RULE_lvalue = 9
    RULE_methodSignature = 10
    RULE_paramList = 11
    RULE_expression = 12
    RULE_argList = 13
    RULE_variable = 14
    RULE_type = 15
    RULE_integerExpression = 16
    RULE_bitstring = 17
    RULE_set = 18
    RULE_moduleImport = 19
    RULE_methodBody = 20
    RULE_id = 21

    ruleNames =  [ "program", "game", "gameBody", "gamePhase", "gameExport", 
                   "field", "initializedField", "simpleStatement", "statement", 
                   "lvalue", "methodSignature", "paramList", "expression", 
                   "argList", "variable", "type", "integerExpression", "bitstring", 
                   "set", "moduleImport", "methodBody", "id" ]

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
    CONCATENATE=23
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
    BINARYNUM=50
    INT=51
    ID=52
    WS=53
    LINE_COMMENT=54
    FILESTRING=55

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.0")
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
        self.enterRule(localctx, 2, self.RULE_game)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 55
            self.match(GameParser.GAME)
            self.state = 56
            self.match(GameParser.ID)
            self.state = 57
            self.match(GameParser.L_PAREN)
            self.state = 59
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 4508108806160384) != 0):
                self.state = 58
                self.paramList()


            self.state = 61
            self.match(GameParser.R_PAREN)
            self.state = 62
            self.match(GameParser.L_CURLY)
            self.state = 63
            self.gameBody()
            self.state = 64
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

        def methodSignature(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.MethodSignatureContext)
            else:
                return self.getTypedRuleContext(GameParser.MethodSignatureContext,i)


        def methodBody(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.MethodBodyContext)
            else:
                return self.getTypedRuleContext(GameParser.MethodBodyContext,i)


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
        self.enterRule(localctx, 4, self.RULE_gameBody)
        self._la = 0 # Token type
        try:
            self.state = 102
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,7,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 71
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,2,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 66
                        self.field()
                        self.state = 67
                        self.match(GameParser.SEMI) 
                    self.state = 73
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,2,self._ctx)

                self.state = 77 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 74
                    self.methodSignature()
                    self.state = 75
                    self.methodBody()
                    self.state = 79 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 4508108806160384) != 0)):
                        break

                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 86
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,4,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 81
                        self.field()
                        self.state = 82
                        self.match(GameParser.SEMI) 
                    self.state = 88
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,4,self._ctx)

                self.state = 94
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while (((_la) & ~0x3f) == 0 and ((1 << _la) & 4508108806160384) != 0):
                    self.state = 89
                    self.methodSignature()
                    self.state = 90
                    self.methodBody()
                    self.state = 96
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 98 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 97
                    self.gamePhase()
                    self.state = 100 
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

        def methodSignature(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.MethodSignatureContext)
            else:
                return self.getTypedRuleContext(GameParser.MethodSignatureContext,i)


        def methodBody(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.MethodBodyContext)
            else:
                return self.getTypedRuleContext(GameParser.MethodBodyContext,i)


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
        self.enterRule(localctx, 6, self.RULE_gamePhase)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 104
            self.match(GameParser.PHASE)
            self.state = 105
            self.match(GameParser.L_CURLY)
            self.state = 109 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 106
                self.methodSignature()
                self.state = 107
                self.methodBody()
                self.state = 111 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 4508108806160384) != 0)):
                    break

            self.state = 113
            self.match(GameParser.ORACLES)
            self.state = 114
            self.match(GameParser.COLON)
            self.state = 115
            self.match(GameParser.L_SQUARE)
            self.state = 116
            self.id_()
            self.state = 121
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==11:
                self.state = 117
                self.match(GameParser.COMMA)
                self.state = 118
                self.id_()
                self.state = 123
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 124
            self.match(GameParser.R_SQUARE)
            self.state = 125
            self.match(GameParser.SEMI)
            self.state = 126
            self.match(GameParser.R_CURLY)
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

        def L_PAREN(self):
            return self.getToken(GameParser.L_PAREN, 0)

        def ID(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.ID)
            else:
                return self.getToken(GameParser.ID, i)

        def COMMA(self):
            return self.getToken(GameParser.COMMA, 0)

        def R_PAREN(self):
            return self.getToken(GameParser.R_PAREN, 0)

        def AS(self):
            return self.getToken(GameParser.AS, 0)

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
        self.enterRule(localctx, 8, self.RULE_gameExport)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 128
            self.match(GameParser.EXPORT)
            self.state = 129
            self.match(GameParser.L_PAREN)
            self.state = 130
            self.match(GameParser.ID)
            self.state = 131
            self.match(GameParser.COMMA)
            self.state = 132
            self.match(GameParser.ID)
            self.state = 133
            self.match(GameParser.R_PAREN)
            self.state = 134
            self.match(GameParser.AS)
            self.state = 135
            self.match(GameParser.ID)
            self.state = 136
            self.match(GameParser.SEMI)
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
            self.state = 138
            self.variable()
            self.state = 141
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==14:
                self.state = 139
                self.match(GameParser.EQUALS)
                self.state = 140
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
            self.state = 143
            self.variable()
            self.state = 144
            self.match(GameParser.EQUALS)
            self.state = 145
            self.expression(0)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SimpleStatementContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def type_(self):
            return self.getTypedRuleContext(GameParser.TypeContext,0)


        def id_(self):
            return self.getTypedRuleContext(GameParser.IdContext,0)


        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)

        def lvalue(self):
            return self.getTypedRuleContext(GameParser.LvalueContext,0)


        def EQUALS(self):
            return self.getToken(GameParser.EQUALS, 0)

        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)


        def SAMPLES(self):
            return self.getToken(GameParser.SAMPLES, 0)

        def L_PAREN(self):
            return self.getToken(GameParser.L_PAREN, 0)

        def R_PAREN(self):
            return self.getToken(GameParser.R_PAREN, 0)

        def argList(self):
            return self.getTypedRuleContext(GameParser.ArgListContext,0)


        def getRuleIndex(self):
            return GameParser.RULE_simpleStatement

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSimpleStatement" ):
                return visitor.visitSimpleStatement(self)
            else:
                return visitor.visitChildren(self)




    def simpleStatement(self):

        localctx = GameParser.SimpleStatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_simpleStatement)
        self._la = 0 # Token type
        try:
            self.state = 181
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,12,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 147
                self.type_(0)
                self.state = 148
                self.id_()
                self.state = 149
                self.match(GameParser.SEMI)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 151
                self.type_(0)
                self.state = 152
                self.lvalue()
                self.state = 153
                self.match(GameParser.EQUALS)
                self.state = 154
                self.expression(0)
                self.state = 155
                self.match(GameParser.SEMI)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 157
                self.type_(0)
                self.state = 158
                self.lvalue()
                self.state = 159
                self.match(GameParser.SAMPLES)
                self.state = 160
                self.expression(0)
                self.state = 161
                self.match(GameParser.SEMI)
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 163
                self.lvalue()
                self.state = 164
                self.match(GameParser.EQUALS)
                self.state = 165
                self.expression(0)
                self.state = 166
                self.match(GameParser.SEMI)
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 168
                self.lvalue()
                self.state = 169
                self.match(GameParser.SAMPLES)
                self.state = 170
                self.expression(0)
                self.state = 171
                self.match(GameParser.SEMI)
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 173
                self.expression(0)
                self.state = 174
                self.match(GameParser.L_PAREN)
                self.state = 176
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 7885808929341482) != 0):
                    self.state = 175
                    self.argList()


                self.state = 178
                self.match(GameParser.R_PAREN)
                self.state = 179
                self.match(GameParser.SEMI)
                pass


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

        def simpleStatement(self):
            return self.getTypedRuleContext(GameParser.SimpleStatementContext,0)


        def RETURN(self):
            return self.getToken(GameParser.RETURN, 0)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)


        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)

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

        def R_PAREN(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.R_PAREN)
            else:
                return self.getToken(GameParser.R_PAREN, i)

        def L_CURLY(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.L_CURLY)
            else:
                return self.getToken(GameParser.L_CURLY, i)

        def R_CURLY(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.R_CURLY)
            else:
                return self.getToken(GameParser.R_CURLY, i)

        def statement(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.StatementContext)
            else:
                return self.getTypedRuleContext(GameParser.StatementContext,i)


        def ELSE(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.ELSE)
            else:
                return self.getToken(GameParser.ELSE, i)

        def FOR(self):
            return self.getToken(GameParser.FOR, 0)

        def INTTYPE(self):
            return self.getToken(GameParser.INTTYPE, 0)

        def id_(self):
            return self.getTypedRuleContext(GameParser.IdContext,0)


        def EQUALS(self):
            return self.getToken(GameParser.EQUALS, 0)

        def TO(self):
            return self.getToken(GameParser.TO, 0)

        def type_(self):
            return self.getTypedRuleContext(GameParser.TypeContext,0)


        def IN(self):
            return self.getToken(GameParser.IN, 0)

        def getRuleIndex(self):
            return GameParser.RULE_statement

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitStatement" ):
                return visitor.visitStatement(self)
            else:
                return visitor.visitChildren(self)




    def statement(self):

        localctx = GameParser.StatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_statement)
        self._la = 0 # Token type
        try:
            self.state = 264
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,20,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 183
                self.simpleStatement()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 184
                self.match(GameParser.RETURN)
                self.state = 185
                self.expression(0)
                self.state = 186
                self.match(GameParser.SEMI)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 188
                self.match(GameParser.IF)
                self.state = 189
                self.match(GameParser.L_PAREN)
                self.state = 190
                self.expression(0)
                self.state = 191
                self.match(GameParser.R_PAREN)
                self.state = 192
                self.match(GameParser.L_CURLY)
                self.state = 196
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while (((_la) & ~0x3f) == 0 and ((1 << _la) & 7887466786717738) != 0):
                    self.state = 193
                    self.statement()
                    self.state = 198
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 199
                self.match(GameParser.R_CURLY)
                self.state = 216
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,15,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 200
                        self.match(GameParser.ELSE)
                        self.state = 201
                        self.match(GameParser.IF)
                        self.state = 202
                        self.match(GameParser.L_PAREN)
                        self.state = 203
                        self.expression(0)
                        self.state = 204
                        self.match(GameParser.R_PAREN)
                        self.state = 205
                        self.match(GameParser.L_CURLY)
                        self.state = 209
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)
                        while (((_la) & ~0x3f) == 0 and ((1 << _la) & 7887466786717738) != 0):
                            self.state = 206
                            self.statement()
                            self.state = 211
                            self._errHandler.sync(self)
                            _la = self._input.LA(1)

                        self.state = 212
                        self.match(GameParser.R_CURLY) 
                    self.state = 218
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,15,self._ctx)

                self.state = 228
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==49:
                    self.state = 219
                    self.match(GameParser.ELSE)
                    self.state = 220
                    self.match(GameParser.L_CURLY)
                    self.state = 224
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while (((_la) & ~0x3f) == 0 and ((1 << _la) & 7887466786717738) != 0):
                        self.state = 221
                        self.statement()
                        self.state = 226
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)

                    self.state = 227
                    self.match(GameParser.R_CURLY)


                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 230
                self.match(GameParser.FOR)
                self.state = 231
                self.match(GameParser.L_PAREN)
                self.state = 232
                self.match(GameParser.INTTYPE)
                self.state = 233
                self.id_()
                self.state = 234
                self.match(GameParser.EQUALS)
                self.state = 235
                self.expression(0)
                self.state = 236
                self.match(GameParser.TO)
                self.state = 237
                self.expression(0)
                self.state = 238
                self.match(GameParser.R_PAREN)
                self.state = 239
                self.match(GameParser.L_CURLY)
                self.state = 243
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while (((_la) & ~0x3f) == 0 and ((1 << _la) & 7887466786717738) != 0):
                    self.state = 240
                    self.statement()
                    self.state = 245
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 246
                self.match(GameParser.R_CURLY)
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 248
                self.match(GameParser.FOR)
                self.state = 249
                self.match(GameParser.L_PAREN)
                self.state = 250
                self.type_(0)
                self.state = 251
                self.id_()
                self.state = 252
                self.match(GameParser.IN)
                self.state = 253
                self.expression(0)
                self.state = 254
                self.match(GameParser.R_PAREN)
                self.state = 255
                self.match(GameParser.L_CURLY)
                self.state = 259
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while (((_la) & ~0x3f) == 0 and ((1 << _la) & 7887466786717738) != 0):
                    self.state = 256
                    self.statement()
                    self.state = 261
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 262
                self.match(GameParser.R_CURLY)
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
        self.enterRule(localctx, 18, self.RULE_lvalue)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 266
            self.id_()
            self.state = 275
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,22,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 273
                    self._errHandler.sync(self)
                    token = self._input.LA(1)
                    if token in [12]:
                        self.state = 267
                        self.match(GameParser.PERIOD)
                        self.state = 268
                        self.id_()
                        pass
                    elif token in [3]:
                        self.state = 269
                        self.match(GameParser.L_SQUARE)
                        self.state = 270
                        self.integerExpression(0)
                        self.state = 271
                        self.match(GameParser.R_SQUARE)
                        pass
                    else:
                        raise NoViableAltException(self)
             
                self.state = 277
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
        self.enterRule(localctx, 20, self.RULE_methodSignature)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 278
            self.type_(0)
            self.state = 279
            self.id_()
            self.state = 280
            self.match(GameParser.L_PAREN)
            self.state = 282
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 4508108806160384) != 0):
                self.state = 281
                self.paramList()


            self.state = 284
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
        self.enterRule(localctx, 22, self.RULE_paramList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 286
            self.variable()
            self.state = 291
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==11:
                self.state = 287
                self.match(GameParser.COMMA)
                self.state = 288
                self.variable()
                self.state = 293
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


    class CreateArrayExpContext(ExpressionContext):

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
            if hasattr( visitor, "visitCreateArrayExp" ):
                return visitor.visitCreateArrayExp(self)
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


    class ConcatenateExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def CONCATENATE(self):
            return self.getToken(GameParser.CONCATENATE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConcatenateExp" ):
                return visitor.visitConcatenateExp(self)
            else:
                return visitor.visitChildren(self)


    class VariableExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def ID(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.ID)
            else:
                return self.getToken(GameParser.ID, i)
        def PERIOD(self, i:int=None):
            if i is None:
                return self.getTokens(GameParser.PERIOD)
            else:
                return self.getToken(GameParser.PERIOD, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVariableExp" ):
                return visitor.visitVariableExp(self)
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


    class ArrayAccessExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)

        def L_SQUARE(self):
            return self.getToken(GameParser.L_SQUARE, 0)
        def integerExpression(self):
            return self.getTypedRuleContext(GameParser.IntegerExpressionContext,0)

        def R_SQUARE(self):
            return self.getToken(GameParser.R_SQUARE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitArrayAccessExp" ):
                return visitor.visitArrayAccessExp(self)
            else:
                return visitor.visitChildren(self)



    def expression(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = GameParser.ExpressionContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 24
        self.enterRecursionRule(localctx, 24, self.RULE_expression, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 340
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,30,self._ctx)
            if la_ == 1:
                localctx = GameParser.VariableExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 295
                self.match(GameParser.ID)
                self.state = 300
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,25,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 296
                        self.match(GameParser.PERIOD)
                        self.state = 297
                        self.match(GameParser.ID) 
                    self.state = 302
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,25,self._ctx)

                pass

            elif la_ == 2:
                localctx = GameParser.SizeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 303
                self.match(GameParser.VBAR)
                self.state = 304
                self.expression(0)
                self.state = 305
                self.match(GameParser.VBAR)
                pass

            elif la_ == 3:
                localctx = GameParser.CreateArrayExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 307
                self.match(GameParser.L_SQUARE)
                self.state = 316
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 7885808929341482) != 0):
                    self.state = 308
                    self.expression(0)
                    self.state = 313
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==11:
                        self.state = 309
                        self.match(GameParser.COMMA)
                        self.state = 310
                        self.expression(0)
                        self.state = 315
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 318
                self.match(GameParser.R_SQUARE)
                pass

            elif la_ == 4:
                localctx = GameParser.CreateSetExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 319
                self.match(GameParser.L_CURLY)
                self.state = 328
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 7885808929341482) != 0):
                    self.state = 320
                    self.expression(0)
                    self.state = 325
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==11:
                        self.state = 321
                        self.match(GameParser.COMMA)
                        self.state = 322
                        self.expression(0)
                        self.state = 327
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 330
                self.match(GameParser.R_CURLY)
                pass

            elif la_ == 5:
                localctx = GameParser.TypeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 331
                self.type_(0)
                pass

            elif la_ == 6:
                localctx = GameParser.BinaryNumExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 332
                self.match(GameParser.BINARYNUM)
                pass

            elif la_ == 7:
                localctx = GameParser.IntExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 333
                self.match(GameParser.INT)
                pass

            elif la_ == 8:
                localctx = GameParser.NotExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 334
                self.match(GameParser.NOT)
                self.state = 335
                self.expression(2)
                pass

            elif la_ == 9:
                localctx = GameParser.ParenExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 336
                self.match(GameParser.L_PAREN)
                self.state = 337
                self.expression(0)
                self.state = 338
                self.match(GameParser.R_PAREN)
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 410
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,33,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 408
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,32,self._ctx)
                    if la_ == 1:
                        localctx = GameParser.EqualsExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 342
                        if not self.precpred(self._ctx, 28):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 28)")
                        self.state = 343
                        self.match(GameParser.EQUALSCOMPARE)
                        self.state = 344
                        self.expression(29)
                        pass

                    elif la_ == 2:
                        localctx = GameParser.NotEqualsExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 345
                        if not self.precpred(self._ctx, 27):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 27)")
                        self.state = 346
                        self.match(GameParser.NOTEQUALS)
                        self.state = 347
                        self.expression(28)
                        pass

                    elif la_ == 3:
                        localctx = GameParser.GtExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 348
                        if not self.precpred(self._ctx, 26):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 26)")
                        self.state = 349
                        self.match(GameParser.R_ANGLE)
                        self.state = 350
                        self.expression(27)
                        pass

                    elif la_ == 4:
                        localctx = GameParser.LtExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 351
                        if not self.precpred(self._ctx, 25):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 25)")
                        self.state = 352
                        self.match(GameParser.L_ANGLE)
                        self.state = 353
                        self.expression(26)
                        pass

                    elif la_ == 5:
                        localctx = GameParser.GeqExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 354
                        if not self.precpred(self._ctx, 24):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 24)")
                        self.state = 355
                        self.match(GameParser.GEQ)
                        self.state = 356
                        self.expression(25)
                        pass

                    elif la_ == 6:
                        localctx = GameParser.LeqExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 357
                        if not self.precpred(self._ctx, 23):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 23)")
                        self.state = 358
                        self.match(GameParser.LEQ)
                        self.state = 359
                        self.expression(24)
                        pass

                    elif la_ == 7:
                        localctx = GameParser.AndExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 360
                        if not self.precpred(self._ctx, 22):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 22)")
                        self.state = 361
                        self.match(GameParser.AND)
                        self.state = 362
                        self.expression(23)
                        pass

                    elif la_ == 8:
                        localctx = GameParser.SubsetsExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 363
                        if not self.precpred(self._ctx, 21):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 21)")
                        self.state = 364
                        self.match(GameParser.SUBSETS)
                        self.state = 365
                        self.expression(22)
                        pass

                    elif la_ == 9:
                        localctx = GameParser.InExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 366
                        if not self.precpred(self._ctx, 20):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 20)")
                        self.state = 367
                        self.match(GameParser.IN)
                        self.state = 368
                        self.expression(21)
                        pass

                    elif la_ == 10:
                        localctx = GameParser.ConcatenateExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 369
                        if not self.precpred(self._ctx, 19):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 19)")
                        self.state = 370
                        self.match(GameParser.CONCATENATE)
                        self.state = 371
                        self.expression(20)
                        pass

                    elif la_ == 11:
                        localctx = GameParser.UnionExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 372
                        if not self.precpred(self._ctx, 18):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 18)")
                        self.state = 373
                        self.match(GameParser.UNION)
                        self.state = 374
                        self.expression(19)
                        pass

                    elif la_ == 12:
                        localctx = GameParser.SetMinusExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 375
                        if not self.precpred(self._ctx, 17):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 17)")
                        self.state = 376
                        self.match(GameParser.BACKSLASH)
                        self.state = 377
                        self.expression(18)
                        pass

                    elif la_ == 13:
                        localctx = GameParser.AddExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 378
                        if not self.precpred(self._ctx, 16):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 16)")
                        self.state = 379
                        self.match(GameParser.PLUS)
                        self.state = 380
                        self.expression(17)
                        pass

                    elif la_ == 14:
                        localctx = GameParser.SubtractExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 381
                        if not self.precpred(self._ctx, 15):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 15)")
                        self.state = 382
                        self.match(GameParser.SUBTRACT)
                        self.state = 383
                        self.expression(16)
                        pass

                    elif la_ == 15:
                        localctx = GameParser.MultiplyExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 384
                        if not self.precpred(self._ctx, 14):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 14)")
                        self.state = 385
                        self.match(GameParser.TIMES)
                        self.state = 386
                        self.expression(15)
                        pass

                    elif la_ == 16:
                        localctx = GameParser.DivideExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 387
                        if not self.precpred(self._ctx, 13):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 13)")
                        self.state = 388
                        self.match(GameParser.DIVIDE)
                        self.state = 389
                        self.expression(14)
                        pass

                    elif la_ == 17:
                        localctx = GameParser.FnCallExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 390
                        if not self.precpred(self._ctx, 10):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 10)")
                        self.state = 391
                        self.match(GameParser.L_PAREN)
                        self.state = 393
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)
                        if (((_la) & ~0x3f) == 0 and ((1 << _la) & 7885808929341482) != 0):
                            self.state = 392
                            self.argList()


                        self.state = 395
                        self.match(GameParser.R_PAREN)
                        pass

                    elif la_ == 18:
                        localctx = GameParser.SliceExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 396
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 9)")
                        self.state = 397
                        self.match(GameParser.L_SQUARE)
                        self.state = 398
                        self.integerExpression(0)
                        self.state = 399
                        self.match(GameParser.COLON)
                        self.state = 400
                        self.integerExpression(0)
                        self.state = 401
                        self.match(GameParser.R_SQUARE)
                        pass

                    elif la_ == 19:
                        localctx = GameParser.ArrayAccessExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 403
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 8)")
                        self.state = 404
                        self.match(GameParser.L_SQUARE)
                        self.state = 405
                        self.integerExpression(0)
                        self.state = 406
                        self.match(GameParser.R_SQUARE)
                        pass

             
                self.state = 412
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,33,self._ctx)

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
        self.enterRule(localctx, 26, self.RULE_argList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 413
            self.expression(0)
            self.state = 418
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==11:
                self.state = 414
                self.match(GameParser.COMMA)
                self.state = 415
                self.expression(0)
                self.state = 420
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
        self.enterRule(localctx, 28, self.RULE_variable)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 421
            self.type_(0)
            self.state = 422
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
        _startState = 30
        self.enterRecursionRule(localctx, 30, self.RULE_type, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 444
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [29]:
                localctx = GameParser.SetTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 425
                self.set_()
                pass
            elif token in [30]:
                localctx = GameParser.BoolTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 426
                self.match(GameParser.BOOL)
                pass
            elif token in [32]:
                localctx = GameParser.MapTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 427
                self.match(GameParser.MAP)
                self.state = 428
                self.match(GameParser.L_ANGLE)
                self.state = 429
                self.type_(0)
                self.state = 430
                self.match(GameParser.COMMA)
                self.state = 431
                self.type_(0)
                self.state = 432
                self.match(GameParser.R_ANGLE)
                pass
            elif token in [36]:
                localctx = GameParser.ArrayTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 434
                self.match(GameParser.ARRAY)
                self.state = 435
                self.match(GameParser.L_ANGLE)
                self.state = 436
                self.type_(0)
                self.state = 437
                self.match(GameParser.COMMA)
                self.state = 438
                self.integerExpression(0)
                self.state = 439
                self.match(GameParser.R_ANGLE)
                pass
            elif token in [31]:
                localctx = GameParser.IntTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 441
                self.match(GameParser.INTTYPE)
                pass
            elif token in [42, 52]:
                localctx = GameParser.LvalueTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 442
                self.lvalue()
                pass
            elif token in [35]:
                localctx = GameParser.BitStringTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 443
                self.bitstring()
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 457
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,38,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 455
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,37,self._ctx)
                    if la_ == 1:
                        localctx = GameParser.OptionalTypeContext(self, GameParser.TypeContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_type)
                        self.state = 446
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 9)")
                        self.state = 447
                        self.match(GameParser.QUESTION)
                        pass

                    elif la_ == 2:
                        localctx = GameParser.ProductTypeContext(self, GameParser.TypeContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_type)
                        self.state = 448
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 3)")
                        self.state = 451 
                        self._errHandler.sync(self)
                        _alt = 1
                        while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                            if _alt == 1:
                                self.state = 449
                                self.match(GameParser.TIMES)
                                self.state = 450
                                self.type_(0)

                            else:
                                raise NoViableAltException(self)
                            self.state = 453 
                            self._errHandler.sync(self)
                            _alt = self._interp.adaptivePredict(self._input,36,self._ctx)

                        pass

             
                self.state = 459
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
        _startState = 32
        self.enterRecursionRule(localctx, 32, self.RULE_integerExpression, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 464
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [42, 52]:
                self.state = 461
                self.lvalue()
                pass
            elif token in [50]:
                self.state = 462
                self.match(GameParser.BINARYNUM)
                pass
            elif token in [51]:
                self.state = 463
                self.match(GameParser.INT)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 480
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,41,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 478
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,40,self._ctx)
                    if la_ == 1:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 466
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 4)")
                        self.state = 467
                        self.match(GameParser.PLUS)
                        self.state = 468
                        self.integerExpression(5)
                        pass

                    elif la_ == 2:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 469
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 3)")
                        self.state = 470
                        self.match(GameParser.TIMES)
                        self.state = 471
                        self.integerExpression(4)
                        pass

                    elif la_ == 3:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 472
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                        self.state = 473
                        self.match(GameParser.SUBTRACT)
                        self.state = 474
                        self.integerExpression(3)
                        pass

                    elif la_ == 4:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 475
                        if not self.precpred(self._ctx, 1):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 1)")
                        self.state = 476
                        self.match(GameParser.DIVIDE)
                        self.state = 477
                        self.integerExpression(2)
                        pass

             
                self.state = 482
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
        self.enterRule(localctx, 34, self.RULE_bitstring)
        try:
            self.state = 489
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,42,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 483
                self.match(GameParser.BITSTRING)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 484
                self.match(GameParser.BITSTRING)
                self.state = 485
                self.match(GameParser.L_ANGLE)
                self.state = 486
                self.integerExpression(0)
                self.state = 487
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
        self.enterRule(localctx, 36, self.RULE_set)
        try:
            self.state = 497
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,43,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 491
                self.match(GameParser.SET)
                self.state = 492
                self.match(GameParser.L_ANGLE)
                self.state = 493
                self.type_(0)
                self.state = 494
                self.match(GameParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 496
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
        self.enterRule(localctx, 38, self.RULE_moduleImport)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 499
            self.match(GameParser.IMPORT)
            self.state = 500
            self.match(GameParser.FILESTRING)
            self.state = 503
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==46:
                self.state = 501
                self.match(GameParser.AS)
                self.state = 502
                self.match(GameParser.ID)


            self.state = 505
            self.match(GameParser.SEMI)
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
            return self.getToken(GameParser.L_CURLY, 0)

        def R_CURLY(self):
            return self.getToken(GameParser.R_CURLY, 0)

        def statement(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.StatementContext)
            else:
                return self.getTypedRuleContext(GameParser.StatementContext,i)


        def getRuleIndex(self):
            return GameParser.RULE_methodBody

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMethodBody" ):
                return visitor.visitMethodBody(self)
            else:
                return visitor.visitChildren(self)




    def methodBody(self):

        localctx = GameParser.MethodBodyContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_methodBody)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 507
            self.match(GameParser.L_CURLY)
            self.state = 509 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 508
                self.statement()
                self.state = 511 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 7887466786717738) != 0)):
                    break

            self.state = 513
            self.match(GameParser.R_CURLY)
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
            self.state = 515
            _la = self._input.LA(1)
            if not(_la==42 or _la==52):
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
        self._predicates[12] = self.expression_sempred
        self._predicates[15] = self.type_sempred
        self._predicates[16] = self.integerExpression_sempred
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
                return self.precpred(self._ctx, 10)
         

            if predIndex == 17:
                return self.precpred(self._ctx, 9)
         

            if predIndex == 18:
                return self.precpred(self._ctx, 8)
         

    def type_sempred(self, localctx:TypeContext, predIndex:int):
            if predIndex == 19:
                return self.precpred(self._ctx, 9)
         

            if predIndex == 20:
                return self.precpred(self._ctx, 3)
         

    def integerExpression_sempred(self, localctx:IntegerExpressionContext, predIndex:int):
            if predIndex == 21:
                return self.precpred(self._ctx, 4)
         

            if predIndex == 22:
                return self.precpred(self._ctx, 3)
         

            if predIndex == 23:
                return self.precpred(self._ctx, 2)
         

            if predIndex == 24:
                return self.precpred(self._ctx, 1)
         




