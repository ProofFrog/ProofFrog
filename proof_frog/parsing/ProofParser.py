# Generated from proof_frog/antlr/Proof.g4 by ANTLR 4.13.2
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
        4,1,82,712,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,2,33,
        7,33,2,34,7,34,2,35,7,35,2,36,7,36,2,37,7,37,2,38,7,38,2,39,7,39,
        2,40,7,40,1,0,5,0,84,8,0,10,0,12,0,87,9,0,1,0,1,0,1,0,1,0,1,1,1,
        1,5,1,95,8,1,10,1,12,1,98,9,1,1,2,1,2,1,2,1,2,3,2,104,8,2,1,2,1,
        2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,3,1,3,1,3,1,3,1,3,3,3,120,8,3,1,
        3,1,3,1,3,3,3,125,8,3,1,3,1,3,1,3,3,3,130,8,3,1,3,1,3,1,3,1,3,1,
        3,1,3,1,3,1,4,1,4,1,4,5,4,142,8,4,10,4,12,4,145,9,4,1,5,1,5,1,5,
        5,5,150,8,5,10,5,12,5,153,9,5,1,5,1,5,1,5,1,5,1,5,3,5,160,8,5,1,
        6,5,6,163,8,6,10,6,12,6,166,9,6,1,7,1,7,1,7,1,7,1,7,1,8,1,8,1,8,
        1,9,1,9,1,9,1,9,1,9,1,9,1,9,5,9,183,8,9,10,9,12,9,186,9,9,1,10,1,
        10,1,10,1,10,1,10,1,10,1,10,1,10,3,10,196,8,10,1,10,1,10,1,10,3,
        10,201,8,10,1,11,1,11,1,11,1,11,1,11,1,11,1,11,1,11,1,11,1,11,1,
        11,1,11,1,12,1,12,1,12,1,12,1,13,1,13,3,13,221,8,13,1,13,1,13,1,
        13,1,14,1,14,1,14,1,14,1,15,1,15,1,15,1,15,1,16,1,16,1,16,1,16,3,
        16,238,8,16,1,16,1,16,1,16,1,16,1,16,1,17,1,17,1,17,5,17,248,8,17,
        10,17,12,17,251,9,17,1,17,4,17,254,8,17,11,17,12,17,255,1,17,1,17,
        1,17,5,17,261,8,17,10,17,12,17,264,9,17,1,17,5,17,267,8,17,10,17,
        12,17,270,9,17,1,17,4,17,273,8,17,11,17,12,17,274,3,17,277,8,17,
        1,18,1,18,1,18,4,18,282,8,18,11,18,12,18,283,1,18,1,18,1,18,1,18,
        1,18,1,18,5,18,292,8,18,10,18,12,18,295,9,18,1,18,1,18,1,18,1,18,
        1,19,1,19,1,19,3,19,304,8,19,1,20,1,20,1,20,1,20,1,21,1,21,1,21,
        1,22,1,22,5,22,315,8,22,10,22,12,22,318,9,22,1,22,1,22,1,23,1,23,
        1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,
        1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,
        1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,
        1,23,1,23,1,23,1,23,1,23,3,23,368,8,23,1,23,1,23,1,23,1,23,1,23,
        1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,
        1,23,5,23,389,8,23,10,23,12,23,392,9,23,1,23,1,23,3,23,396,8,23,
        1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,1,23,
        1,23,1,23,1,23,1,23,1,23,1,23,1,23,3,23,418,8,23,1,24,1,24,1,24,
        3,24,423,8,24,1,24,1,24,1,24,1,24,1,24,1,24,5,24,431,8,24,10,24,
        12,24,434,9,24,1,25,1,25,1,26,5,26,439,8,26,10,26,12,26,442,9,26,
        1,26,1,26,1,26,1,26,3,26,448,8,26,1,26,1,26,1,27,1,27,1,27,5,27,
        455,8,27,10,27,12,27,458,9,27,1,28,1,28,1,28,1,28,1,28,1,28,1,28,
        1,28,1,28,1,28,1,28,1,28,1,28,1,28,5,28,474,8,28,10,28,12,28,477,
        9,28,3,28,479,8,28,1,28,1,28,1,28,1,28,1,28,5,28,486,8,28,10,28,
        12,28,489,9,28,3,28,491,8,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,
        1,28,1,28,1,28,1,28,1,28,1,28,1,28,3,28,507,8,28,1,28,1,28,1,28,
        1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,
        1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,
        1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,
        1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,3,28,
        563,8,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,5,28,573,8,28,10,
        28,12,28,576,9,28,1,29,1,29,1,29,5,29,581,8,29,10,29,12,29,584,9,
        29,1,30,1,30,1,30,1,31,1,31,1,31,3,31,592,8,31,1,31,1,31,1,32,1,
        32,1,32,1,32,1,32,1,32,1,32,1,32,1,32,1,32,1,32,1,32,1,32,1,32,1,
        32,1,32,1,32,1,32,1,32,1,32,1,32,1,32,1,32,1,32,1,32,1,32,1,32,1,
        32,1,32,1,32,4,32,626,8,32,11,32,12,32,627,1,32,1,32,1,32,1,32,1,
        32,3,32,635,8,32,1,32,1,32,5,32,639,8,32,10,32,12,32,642,9,32,1,
        33,1,33,1,33,1,33,1,33,1,33,1,33,1,33,3,33,652,8,33,1,33,1,33,1,
        33,1,33,1,33,1,33,1,33,1,33,1,33,1,33,1,33,1,33,5,33,666,8,33,10,
        33,12,33,669,9,33,1,34,1,34,1,34,1,34,1,34,1,34,3,34,677,8,34,1,
        35,1,35,1,35,1,35,1,35,1,35,3,35,685,8,35,1,36,1,36,1,36,1,36,1,
        36,1,37,1,37,1,37,1,37,1,37,1,37,3,37,698,8,37,1,38,1,38,1,39,1,
        39,1,39,1,39,3,39,706,8,39,1,39,1,39,1,40,1,40,1,40,0,3,56,64,66,
        41,0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,
        44,46,48,50,52,54,56,58,60,62,64,66,68,70,72,74,76,78,80,0,4,2,0,
        21,21,36,36,1,0,71,72,1,0,73,74,2,0,61,61,79,79,782,0,85,1,0,0,0,
        2,96,1,0,0,0,4,99,1,0,0,0,6,114,1,0,0,0,8,143,1,0,0,0,10,151,1,0,
        0,0,12,164,1,0,0,0,14,167,1,0,0,0,16,172,1,0,0,0,18,175,1,0,0,0,
        20,200,1,0,0,0,22,202,1,0,0,0,24,214,1,0,0,0,26,220,1,0,0,0,28,225,
        1,0,0,0,30,229,1,0,0,0,32,233,1,0,0,0,34,276,1,0,0,0,36,278,1,0,
        0,0,38,300,1,0,0,0,40,305,1,0,0,0,42,309,1,0,0,0,44,312,1,0,0,0,
        46,417,1,0,0,0,48,422,1,0,0,0,50,435,1,0,0,0,52,440,1,0,0,0,54,451,
        1,0,0,0,56,506,1,0,0,0,58,577,1,0,0,0,60,585,1,0,0,0,62,588,1,0,
        0,0,64,634,1,0,0,0,66,651,1,0,0,0,68,676,1,0,0,0,70,684,1,0,0,0,
        72,686,1,0,0,0,74,697,1,0,0,0,76,699,1,0,0,0,78,701,1,0,0,0,80,709,
        1,0,0,0,82,84,3,78,39,0,83,82,1,0,0,0,84,87,1,0,0,0,85,83,1,0,0,
        0,85,86,1,0,0,0,86,88,1,0,0,0,87,85,1,0,0,0,88,89,3,2,1,0,89,90,
        3,6,3,0,90,91,5,0,0,1,91,1,1,0,0,0,92,95,3,4,2,0,93,95,3,32,16,0,
        94,92,1,0,0,0,94,93,1,0,0,0,95,98,1,0,0,0,96,94,1,0,0,0,96,97,1,
        0,0,0,97,3,1,0,0,0,98,96,1,0,0,0,99,100,5,1,0,0,100,101,5,79,0,0,
        101,103,5,19,0,0,102,104,3,54,27,0,103,102,1,0,0,0,103,104,1,0,0,
        0,104,105,1,0,0,0,105,106,5,20,0,0,106,107,5,4,0,0,107,108,3,62,
        31,0,108,109,5,2,0,0,109,110,3,30,15,0,110,111,5,15,0,0,111,112,
        3,34,17,0,112,113,5,16,0,0,113,5,1,0,0,0,114,115,5,5,0,0,115,119,
        5,24,0,0,116,117,5,9,0,0,117,118,5,24,0,0,118,120,3,8,4,0,119,116,
        1,0,0,0,119,120,1,0,0,0,120,124,1,0,0,0,121,122,5,6,0,0,122,123,
        5,24,0,0,123,125,3,10,5,0,124,121,1,0,0,0,124,125,1,0,0,0,125,129,
        1,0,0,0,126,127,5,12,0,0,127,128,5,24,0,0,128,130,3,12,6,0,129,126,
        1,0,0,0,129,130,1,0,0,0,130,131,1,0,0,0,131,132,5,7,0,0,132,133,
        5,24,0,0,133,134,3,16,8,0,134,135,5,8,0,0,135,136,5,24,0,0,136,137,
        3,18,9,0,137,7,1,0,0,0,138,139,3,38,19,0,139,140,5,23,0,0,140,142,
        1,0,0,0,141,138,1,0,0,0,142,145,1,0,0,0,143,141,1,0,0,0,143,144,
        1,0,0,0,144,9,1,0,0,0,145,143,1,0,0,0,146,147,3,62,31,0,147,148,
        5,23,0,0,148,150,1,0,0,0,149,146,1,0,0,0,150,153,1,0,0,0,151,149,
        1,0,0,0,151,152,1,0,0,0,152,159,1,0,0,0,153,151,1,0,0,0,154,155,
        5,10,0,0,155,156,7,0,0,0,156,157,3,56,28,0,157,158,5,23,0,0,158,
        160,1,0,0,0,159,154,1,0,0,0,159,160,1,0,0,0,160,11,1,0,0,0,161,163,
        3,14,7,0,162,161,1,0,0,0,163,166,1,0,0,0,164,162,1,0,0,0,164,165,
        1,0,0,0,165,13,1,0,0,0,166,164,1,0,0,0,167,168,3,62,31,0,168,169,
        5,13,0,0,169,170,5,82,0,0,170,171,5,23,0,0,171,15,1,0,0,0,172,173,
        3,62,31,0,173,174,5,23,0,0,174,17,1,0,0,0,175,176,3,20,10,0,176,
        184,5,23,0,0,177,178,3,20,10,0,178,179,5,23,0,0,179,183,1,0,0,0,
        180,183,3,22,11,0,181,183,3,24,12,0,182,177,1,0,0,0,182,180,1,0,
        0,0,182,181,1,0,0,0,183,186,1,0,0,0,184,182,1,0,0,0,184,185,1,0,
        0,0,185,19,1,0,0,0,186,184,1,0,0,0,187,188,3,28,14,0,188,189,5,4,
        0,0,189,190,3,62,31,0,190,191,5,2,0,0,191,192,3,30,15,0,192,201,
        1,0,0,0,193,196,3,28,14,0,194,196,3,62,31,0,195,193,1,0,0,0,195,
        194,1,0,0,0,196,197,1,0,0,0,197,198,5,2,0,0,198,199,3,30,15,0,199,
        201,1,0,0,0,200,187,1,0,0,0,200,195,1,0,0,0,201,21,1,0,0,0,202,203,
        5,11,0,0,203,204,5,19,0,0,204,205,5,79,0,0,205,206,5,14,0,0,206,
        207,3,66,33,0,207,208,5,60,0,0,208,209,3,66,33,0,209,210,5,20,0,
        0,210,211,5,15,0,0,211,212,3,18,9,0,212,213,5,16,0,0,213,23,1,0,
        0,0,214,215,5,6,0,0,215,216,3,56,28,0,216,217,5,23,0,0,217,25,1,
        0,0,0,218,221,3,28,14,0,219,221,3,62,31,0,220,218,1,0,0,0,220,219,
        1,0,0,0,221,222,1,0,0,0,222,223,5,26,0,0,223,224,5,79,0,0,224,27,
        1,0,0,0,225,226,3,62,31,0,226,227,5,26,0,0,227,228,5,79,0,0,228,
        29,1,0,0,0,229,230,3,62,31,0,230,231,5,26,0,0,231,232,5,3,0,0,232,
        31,1,0,0,0,233,234,5,63,0,0,234,235,5,79,0,0,235,237,5,19,0,0,236,
        238,3,54,27,0,237,236,1,0,0,0,237,238,1,0,0,0,238,239,1,0,0,0,239,
        240,5,20,0,0,240,241,5,15,0,0,241,242,3,34,17,0,242,243,5,16,0,0,
        243,33,1,0,0,0,244,245,3,38,19,0,245,246,5,23,0,0,246,248,1,0,0,
        0,247,244,1,0,0,0,248,251,1,0,0,0,249,247,1,0,0,0,249,250,1,0,0,
        0,250,253,1,0,0,0,251,249,1,0,0,0,252,254,3,42,21,0,253,252,1,0,
        0,0,254,255,1,0,0,0,255,253,1,0,0,0,255,256,1,0,0,0,256,277,1,0,
        0,0,257,258,3,38,19,0,258,259,5,23,0,0,259,261,1,0,0,0,260,257,1,
        0,0,0,261,264,1,0,0,0,262,260,1,0,0,0,262,263,1,0,0,0,263,268,1,
        0,0,0,264,262,1,0,0,0,265,267,3,42,21,0,266,265,1,0,0,0,267,270,
        1,0,0,0,268,266,1,0,0,0,268,269,1,0,0,0,269,272,1,0,0,0,270,268,
        1,0,0,0,271,273,3,36,18,0,272,271,1,0,0,0,273,274,1,0,0,0,274,272,
        1,0,0,0,274,275,1,0,0,0,275,277,1,0,0,0,276,249,1,0,0,0,276,262,
        1,0,0,0,277,35,1,0,0,0,278,279,5,66,0,0,279,281,5,15,0,0,280,282,
        3,42,21,0,281,280,1,0,0,0,282,283,1,0,0,0,283,281,1,0,0,0,283,284,
        1,0,0,0,284,285,1,0,0,0,285,286,5,67,0,0,286,287,5,24,0,0,287,288,
        5,17,0,0,288,293,3,80,40,0,289,290,5,25,0,0,290,292,3,80,40,0,291,
        289,1,0,0,0,292,295,1,0,0,0,293,291,1,0,0,0,293,294,1,0,0,0,294,
        296,1,0,0,0,295,293,1,0,0,0,296,297,5,18,0,0,297,298,5,23,0,0,298,
        299,5,16,0,0,299,37,1,0,0,0,300,303,3,60,30,0,301,302,5,28,0,0,302,
        304,3,56,28,0,303,301,1,0,0,0,303,304,1,0,0,0,304,39,1,0,0,0,305,
        306,3,60,30,0,306,307,5,28,0,0,307,308,3,56,28,0,308,41,1,0,0,0,
        309,310,3,52,26,0,310,311,3,44,22,0,311,43,1,0,0,0,312,316,5,15,
        0,0,313,315,3,46,23,0,314,313,1,0,0,0,315,318,1,0,0,0,316,314,1,
        0,0,0,316,317,1,0,0,0,317,319,1,0,0,0,318,316,1,0,0,0,319,320,5,
        16,0,0,320,45,1,0,0,0,321,322,3,64,32,0,322,323,3,80,40,0,323,324,
        5,23,0,0,324,418,1,0,0,0,325,326,3,64,32,0,326,327,3,48,24,0,327,
        328,5,28,0,0,328,329,3,56,28,0,329,330,5,23,0,0,330,418,1,0,0,0,
        331,332,3,64,32,0,332,333,3,48,24,0,333,334,5,39,0,0,334,335,3,56,
        28,0,335,336,5,23,0,0,336,418,1,0,0,0,337,338,3,48,24,0,338,339,
        5,28,0,0,339,340,3,56,28,0,340,341,5,23,0,0,341,418,1,0,0,0,342,
        343,3,48,24,0,343,344,5,39,0,0,344,345,3,56,28,0,345,346,5,23,0,
        0,346,418,1,0,0,0,347,348,3,64,32,0,348,349,3,48,24,0,349,350,5,
        38,0,0,350,351,5,17,0,0,351,352,3,48,24,0,352,353,5,18,0,0,353,354,
        3,64,32,0,354,355,5,23,0,0,355,418,1,0,0,0,356,357,3,48,24,0,357,
        358,5,38,0,0,358,359,5,17,0,0,359,360,3,48,24,0,360,361,5,18,0,0,
        361,362,3,64,32,0,362,363,5,23,0,0,363,418,1,0,0,0,364,365,3,56,
        28,0,365,367,5,19,0,0,366,368,3,58,29,0,367,366,1,0,0,0,367,368,
        1,0,0,0,368,369,1,0,0,0,369,370,5,20,0,0,370,371,5,23,0,0,371,418,
        1,0,0,0,372,373,5,50,0,0,373,374,3,56,28,0,374,375,5,23,0,0,375,
        418,1,0,0,0,376,377,5,58,0,0,377,378,5,19,0,0,378,379,3,56,28,0,
        379,380,5,20,0,0,380,390,3,44,22,0,381,382,5,68,0,0,382,383,5,58,
        0,0,383,384,5,19,0,0,384,385,3,56,28,0,385,386,5,20,0,0,386,387,
        3,44,22,0,387,389,1,0,0,0,388,381,1,0,0,0,389,392,1,0,0,0,390,388,
        1,0,0,0,390,391,1,0,0,0,391,395,1,0,0,0,392,390,1,0,0,0,393,394,
        5,68,0,0,394,396,3,44,22,0,395,393,1,0,0,0,395,396,1,0,0,0,396,418,
        1,0,0,0,397,398,5,59,0,0,398,399,5,19,0,0,399,400,5,48,0,0,400,401,
        3,80,40,0,401,402,5,28,0,0,402,403,3,56,28,0,403,404,5,60,0,0,404,
        405,3,56,28,0,405,406,5,20,0,0,406,407,3,44,22,0,407,418,1,0,0,0,
        408,409,5,59,0,0,409,410,5,19,0,0,410,411,3,64,32,0,411,412,3,80,
        40,0,412,413,5,61,0,0,413,414,3,56,28,0,414,415,5,20,0,0,415,416,
        3,44,22,0,416,418,1,0,0,0,417,321,1,0,0,0,417,325,1,0,0,0,417,331,
        1,0,0,0,417,337,1,0,0,0,417,342,1,0,0,0,417,347,1,0,0,0,417,356,
        1,0,0,0,417,364,1,0,0,0,417,372,1,0,0,0,417,376,1,0,0,0,417,397,
        1,0,0,0,417,408,1,0,0,0,418,47,1,0,0,0,419,423,3,80,40,0,420,423,
        3,62,31,0,421,423,5,70,0,0,422,419,1,0,0,0,422,420,1,0,0,0,422,421,
        1,0,0,0,423,432,1,0,0,0,424,425,5,26,0,0,425,431,3,80,40,0,426,427,
        5,17,0,0,427,428,3,56,28,0,428,429,5,18,0,0,429,431,1,0,0,0,430,
        424,1,0,0,0,430,426,1,0,0,0,431,434,1,0,0,0,432,430,1,0,0,0,432,
        433,1,0,0,0,433,49,1,0,0,0,434,432,1,0,0,0,435,436,7,1,0,0,436,51,
        1,0,0,0,437,439,3,50,25,0,438,437,1,0,0,0,439,442,1,0,0,0,440,438,
        1,0,0,0,440,441,1,0,0,0,441,443,1,0,0,0,442,440,1,0,0,0,443,444,
        3,64,32,0,444,445,3,80,40,0,445,447,5,19,0,0,446,448,3,54,27,0,447,
        446,1,0,0,0,447,448,1,0,0,0,448,449,1,0,0,0,449,450,5,20,0,0,450,
        53,1,0,0,0,451,456,3,60,30,0,452,453,5,25,0,0,453,455,3,60,30,0,
        454,452,1,0,0,0,455,458,1,0,0,0,456,454,1,0,0,0,456,457,1,0,0,0,
        457,55,1,0,0,0,458,456,1,0,0,0,459,460,6,28,-1,0,460,461,5,42,0,
        0,461,507,3,56,28,31,462,463,5,44,0,0,463,464,3,56,28,0,464,465,
        5,44,0,0,465,507,1,0,0,0,466,467,5,30,0,0,467,507,3,56,28,26,468,
        507,3,48,24,0,469,478,5,17,0,0,470,475,3,56,28,0,471,472,5,25,0,
        0,472,474,3,56,28,0,473,471,1,0,0,0,474,477,1,0,0,0,475,473,1,0,
        0,0,475,476,1,0,0,0,476,479,1,0,0,0,477,475,1,0,0,0,478,470,1,0,
        0,0,478,479,1,0,0,0,479,480,1,0,0,0,480,507,5,18,0,0,481,490,5,15,
        0,0,482,487,3,56,28,0,483,484,5,25,0,0,484,486,3,56,28,0,485,483,
        1,0,0,0,486,489,1,0,0,0,487,485,1,0,0,0,487,488,1,0,0,0,488,491,
        1,0,0,0,489,487,1,0,0,0,490,482,1,0,0,0,490,491,1,0,0,0,491,492,
        1,0,0,0,492,507,5,16,0,0,493,507,3,64,32,0,494,495,5,76,0,0,495,
        507,3,68,34,0,496,497,5,77,0,0,497,507,3,68,34,0,498,507,5,75,0,
        0,499,507,5,78,0,0,500,507,3,76,38,0,501,507,5,69,0,0,502,503,5,
        19,0,0,503,504,3,56,28,0,504,505,5,20,0,0,505,507,1,0,0,0,506,459,
        1,0,0,0,506,462,1,0,0,0,506,466,1,0,0,0,506,468,1,0,0,0,506,469,
        1,0,0,0,506,481,1,0,0,0,506,493,1,0,0,0,506,494,1,0,0,0,506,496,
        1,0,0,0,506,498,1,0,0,0,506,499,1,0,0,0,506,500,1,0,0,0,506,501,
        1,0,0,0,506,502,1,0,0,0,507,574,1,0,0,0,508,509,10,29,0,0,509,510,
        5,43,0,0,510,573,3,56,28,29,511,512,10,28,0,0,512,513,5,27,0,0,513,
        573,3,56,28,29,514,515,10,27,0,0,515,516,5,31,0,0,516,573,3,56,28,
        28,517,518,10,25,0,0,518,519,5,29,0,0,519,573,3,56,28,26,520,521,
        10,24,0,0,521,522,5,30,0,0,522,573,3,56,28,25,523,524,10,23,0,0,
        524,525,5,33,0,0,525,573,3,56,28,24,526,527,10,22,0,0,527,528,5,
        34,0,0,528,573,3,56,28,23,529,530,10,21,0,0,530,531,5,22,0,0,531,
        573,3,56,28,22,532,533,10,20,0,0,533,534,5,21,0,0,534,573,3,56,28,
        21,535,536,10,19,0,0,536,537,5,35,0,0,537,573,3,56,28,20,538,539,
        10,18,0,0,539,540,5,36,0,0,540,573,3,56,28,19,541,542,10,17,0,0,
        542,543,5,61,0,0,543,573,3,56,28,18,544,545,10,16,0,0,545,546,5,
        57,0,0,546,573,3,56,28,17,547,548,10,15,0,0,548,549,5,40,0,0,549,
        573,3,56,28,16,550,551,10,14,0,0,551,552,5,37,0,0,552,573,3,56,28,
        15,553,554,10,13,0,0,554,555,5,62,0,0,555,573,3,56,28,14,556,557,
        10,12,0,0,557,558,5,41,0,0,558,573,3,56,28,13,559,560,10,33,0,0,
        560,562,5,19,0,0,561,563,3,58,29,0,562,561,1,0,0,0,562,563,1,0,0,
        0,563,564,1,0,0,0,564,573,5,20,0,0,565,566,10,32,0,0,566,567,5,17,
        0,0,567,568,3,66,33,0,568,569,5,24,0,0,569,570,3,66,33,0,570,571,
        5,18,0,0,571,573,1,0,0,0,572,508,1,0,0,0,572,511,1,0,0,0,572,514,
        1,0,0,0,572,517,1,0,0,0,572,520,1,0,0,0,572,523,1,0,0,0,572,526,
        1,0,0,0,572,529,1,0,0,0,572,532,1,0,0,0,572,535,1,0,0,0,572,538,
        1,0,0,0,572,541,1,0,0,0,572,544,1,0,0,0,572,547,1,0,0,0,572,550,
        1,0,0,0,572,553,1,0,0,0,572,556,1,0,0,0,572,559,1,0,0,0,572,565,
        1,0,0,0,573,576,1,0,0,0,574,572,1,0,0,0,574,575,1,0,0,0,575,57,1,
        0,0,0,576,574,1,0,0,0,577,582,3,56,28,0,578,579,5,25,0,0,579,581,
        3,56,28,0,580,578,1,0,0,0,581,584,1,0,0,0,582,580,1,0,0,0,582,583,
        1,0,0,0,583,59,1,0,0,0,584,582,1,0,0,0,585,586,3,64,32,0,586,587,
        3,80,40,0,587,61,1,0,0,0,588,589,5,79,0,0,589,591,5,19,0,0,590,592,
        3,58,29,0,591,590,1,0,0,0,591,592,1,0,0,0,592,593,1,0,0,0,593,594,
        5,20,0,0,594,63,1,0,0,0,595,596,6,32,-1,0,596,635,3,74,37,0,597,
        635,5,46,0,0,598,635,5,47,0,0,599,600,5,49,0,0,600,601,5,21,0,0,
        601,602,3,64,32,0,602,603,5,25,0,0,603,604,3,64,32,0,604,605,5,22,
        0,0,605,635,1,0,0,0,606,607,5,54,0,0,607,608,5,21,0,0,608,609,3,
        64,32,0,609,610,5,25,0,0,610,611,3,66,33,0,611,612,5,22,0,0,612,
        635,1,0,0,0,613,614,5,55,0,0,614,615,5,21,0,0,615,616,3,64,32,0,
        616,617,5,25,0,0,617,618,3,64,32,0,618,619,5,22,0,0,619,635,1,0,
        0,0,620,635,5,48,0,0,621,622,5,17,0,0,622,625,3,64,32,0,623,624,
        5,25,0,0,624,626,3,64,32,0,625,623,1,0,0,0,626,627,1,0,0,0,627,625,
        1,0,0,0,627,628,1,0,0,0,628,629,1,0,0,0,629,630,5,18,0,0,630,635,
        1,0,0,0,631,635,3,70,35,0,632,635,3,72,36,0,633,635,3,48,24,0,634,
        595,1,0,0,0,634,597,1,0,0,0,634,598,1,0,0,0,634,599,1,0,0,0,634,
        606,1,0,0,0,634,613,1,0,0,0,634,620,1,0,0,0,634,621,1,0,0,0,634,
        631,1,0,0,0,634,632,1,0,0,0,634,633,1,0,0,0,635,640,1,0,0,0,636,
        637,10,12,0,0,637,639,5,32,0,0,638,636,1,0,0,0,639,642,1,0,0,0,640,
        638,1,0,0,0,640,641,1,0,0,0,641,65,1,0,0,0,642,640,1,0,0,0,643,644,
        6,33,-1,0,644,652,3,48,24,0,645,652,5,78,0,0,646,652,5,75,0,0,647,
        648,5,19,0,0,648,649,3,66,33,0,649,650,5,20,0,0,650,652,1,0,0,0,
        651,643,1,0,0,0,651,645,1,0,0,0,651,646,1,0,0,0,651,647,1,0,0,0,
        652,667,1,0,0,0,653,654,10,8,0,0,654,655,5,27,0,0,655,666,3,66,33,
        9,656,657,10,7,0,0,657,658,5,31,0,0,658,666,3,66,33,8,659,660,10,
        6,0,0,660,661,5,29,0,0,661,666,3,66,33,7,662,663,10,5,0,0,663,664,
        5,30,0,0,664,666,3,66,33,6,665,653,1,0,0,0,665,656,1,0,0,0,665,659,
        1,0,0,0,665,662,1,0,0,0,666,669,1,0,0,0,667,665,1,0,0,0,667,668,
        1,0,0,0,668,67,1,0,0,0,669,667,1,0,0,0,670,677,3,48,24,0,671,677,
        5,78,0,0,672,673,5,19,0,0,673,674,3,66,33,0,674,675,5,20,0,0,675,
        677,1,0,0,0,676,670,1,0,0,0,676,671,1,0,0,0,676,672,1,0,0,0,677,
        69,1,0,0,0,678,679,5,52,0,0,679,680,5,21,0,0,680,681,3,66,33,0,681,
        682,5,22,0,0,682,685,1,0,0,0,683,685,5,52,0,0,684,678,1,0,0,0,684,
        683,1,0,0,0,685,71,1,0,0,0,686,687,5,53,0,0,687,688,5,21,0,0,688,
        689,3,66,33,0,689,690,5,22,0,0,690,73,1,0,0,0,691,692,5,45,0,0,692,
        693,5,21,0,0,693,694,3,64,32,0,694,695,5,22,0,0,695,698,1,0,0,0,
        696,698,5,45,0,0,697,691,1,0,0,0,697,696,1,0,0,0,698,75,1,0,0,0,
        699,700,7,2,0,0,700,77,1,0,0,0,701,702,5,51,0,0,702,705,5,82,0,0,
        703,704,5,65,0,0,704,706,5,79,0,0,705,703,1,0,0,0,705,706,1,0,0,
        0,706,707,1,0,0,0,707,708,5,23,0,0,708,79,1,0,0,0,709,710,7,3,0,
        0,710,81,1,0,0,0,57,85,94,96,103,119,124,129,143,151,159,164,182,
        184,195,200,220,237,249,255,262,268,274,276,283,293,303,316,367,
        390,395,417,422,430,432,440,447,456,475,478,487,490,506,562,572,
        574,582,591,627,634,640,651,665,667,676,684,697,705
    ]

class ProofParser ( Parser ):

    grammarFileName = "Proof.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'Reduction'", "'against'", "'Adversary'", 
                     "'compose'", "'proof'", "'assume'", "'theorem'", "'games'", 
                     "'let'", "'calls'", "'induction'", "'lemma'", "'by'", 
                     "'from'", "'{'", "'}'", "'['", "']'", "'('", "')'", 
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

    symbolicNames = [ "<INVALID>", "REDUCTION", "AGAINST", "ADVERSARY", 
                      "COMPOSE", "PROOF", "ASSUME", "THEOREM", "GAMES", 
                      "LET", "CALLS", "INDUCTION", "LEMMA", "BY", "FROM", 
                      "L_CURLY", "R_CURLY", "L_SQUARE", "R_SQUARE", "L_PAREN", 
                      "R_PAREN", "L_ANGLE", "R_ANGLE", "SEMI", "COLON", 
                      "COMMA", "PERIOD", "TIMES", "EQUALS", "PLUS", "SUBTRACT", 
                      "DIVIDE", "QUESTION", "EQUALSCOMPARE", "NOTEQUALS", 
                      "GEQ", "LEQ", "OR", "SAMPUNIQ", "SAMPLES", "AND", 
                      "BACKSLASH", "NOT", "CARET", "VBAR", "SET", "BOOL", 
                      "VOID", "INTTYPE", "MAP", "RETURN", "IMPORT", "BITSTRING", 
                      "MODINT", "ARRAY", "RANDOMFUNCTIONS", "PRIMITIVE", 
                      "SUBSETS", "IF", "FOR", "TO", "IN", "UNION", "GAME", 
                      "EXPORT", "AS", "PHASE", "ORACLES", "ELSE", "NONE", 
                      "THIS", "DETERMINISTIC", "INJECTIVE", "TRUE", "FALSE", 
                      "BINARYNUM", "ZEROS_CARET", "ONES_CARET", "INT", "ID", 
                      "WS", "LINE_COMMENT", "FILESTRING" ]

    RULE_program = 0
    RULE_proofHelpers = 1
    RULE_reduction = 2
    RULE_proof = 3
    RULE_lets = 4
    RULE_assumptions = 5
    RULE_lemmas = 6
    RULE_lemmaEntry = 7
    RULE_theorem = 8
    RULE_gameList = 9
    RULE_gameStep = 10
    RULE_induction = 11
    RULE_stepAssumption = 12
    RULE_gameField = 13
    RULE_concreteGame = 14
    RULE_gameAdversary = 15
    RULE_game = 16
    RULE_gameBody = 17
    RULE_gamePhase = 18
    RULE_field = 19
    RULE_initializedField = 20
    RULE_method = 21
    RULE_block = 22
    RULE_statement = 23
    RULE_lvalue = 24
    RULE_methodModifier = 25
    RULE_methodSignature = 26
    RULE_paramList = 27
    RULE_expression = 28
    RULE_argList = 29
    RULE_variable = 30
    RULE_parameterizedGame = 31
    RULE_type = 32
    RULE_integerExpression = 33
    RULE_integerAtom = 34
    RULE_bitstring = 35
    RULE_modint = 36
    RULE_set = 37
    RULE_bool = 38
    RULE_moduleImport = 39
    RULE_id = 40

    ruleNames =  [ "program", "proofHelpers", "reduction", "proof", "lets", 
                   "assumptions", "lemmas", "lemmaEntry", "theorem", "gameList", 
                   "gameStep", "induction", "stepAssumption", "gameField", 
                   "concreteGame", "gameAdversary", "game", "gameBody", 
                   "gamePhase", "field", "initializedField", "method", "block", 
                   "statement", "lvalue", "methodModifier", "methodSignature", 
                   "paramList", "expression", "argList", "variable", "parameterizedGame", 
                   "type", "integerExpression", "integerAtom", "bitstring", 
                   "modint", "set", "bool", "moduleImport", "id" ]

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
    LEMMA=12
    BY=13
    FROM=14
    L_CURLY=15
    R_CURLY=16
    L_SQUARE=17
    R_SQUARE=18
    L_PAREN=19
    R_PAREN=20
    L_ANGLE=21
    R_ANGLE=22
    SEMI=23
    COLON=24
    COMMA=25
    PERIOD=26
    TIMES=27
    EQUALS=28
    PLUS=29
    SUBTRACT=30
    DIVIDE=31
    QUESTION=32
    EQUALSCOMPARE=33
    NOTEQUALS=34
    GEQ=35
    LEQ=36
    OR=37
    SAMPUNIQ=38
    SAMPLES=39
    AND=40
    BACKSLASH=41
    NOT=42
    CARET=43
    VBAR=44
    SET=45
    BOOL=46
    VOID=47
    INTTYPE=48
    MAP=49
    RETURN=50
    IMPORT=51
    BITSTRING=52
    MODINT=53
    ARRAY=54
    RANDOMFUNCTIONS=55
    PRIMITIVE=56
    SUBSETS=57
    IF=58
    FOR=59
    TO=60
    IN=61
    UNION=62
    GAME=63
    EXPORT=64
    AS=65
    PHASE=66
    ORACLES=67
    ELSE=68
    NONE=69
    THIS=70
    DETERMINISTIC=71
    INJECTIVE=72
    TRUE=73
    FALSE=74
    BINARYNUM=75
    ZEROS_CARET=76
    ONES_CARET=77
    INT=78
    ID=79
    WS=80
    LINE_COMMENT=81
    FILESTRING=82

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

        def proofHelpers(self):
            return self.getTypedRuleContext(ProofParser.ProofHelpersContext,0)


        def proof(self):
            return self.getTypedRuleContext(ProofParser.ProofContext,0)


        def EOF(self):
            return self.getToken(ProofParser.EOF, 0)

        def moduleImport(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ModuleImportContext)
            else:
                return self.getTypedRuleContext(ProofParser.ModuleImportContext,i)


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
            self.state = 85
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==51:
                self.state = 82
                self.moduleImport()
                self.state = 87
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 88
            self.proofHelpers()
            self.state = 89
            self.proof()
            self.state = 90
            self.match(ProofParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ProofHelpersContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

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
            return ProofParser.RULE_proofHelpers

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitProofHelpers" ):
                return visitor.visitProofHelpers(self)
            else:
                return visitor.visitChildren(self)




    def proofHelpers(self):

        localctx = ProofParser.ProofHelpersContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_proofHelpers)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 96
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==1 or _la==63:
                self.state = 94
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [1]:
                    self.state = 92
                    self.reduction()
                    pass
                elif token in [63]:
                    self.state = 93
                    self.game()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 98
                self._errHandler.sync(self)
                _la = self._input.LA(1)

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

        def parameterizedGame(self):
            return self.getTypedRuleContext(ProofParser.ParameterizedGameContext,0)


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
        self.enterRule(localctx, 4, self.RULE_reduction)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 99
            self.match(ProofParser.REDUCTION)
            self.state = 100
            self.match(ProofParser.ID)
            self.state = 101
            self.match(ProofParser.L_PAREN)
            self.state = 103
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 17)) & ~0x3f) == 0 and ((1 << (_la - 17)) & 4620711333585747969) != 0):
                self.state = 102
                self.paramList()


            self.state = 105
            self.match(ProofParser.R_PAREN)
            self.state = 106
            self.match(ProofParser.COMPOSE)
            self.state = 107
            self.parameterizedGame()
            self.state = 108
            self.match(ProofParser.AGAINST)
            self.state = 109
            self.gameAdversary()
            self.state = 110
            self.match(ProofParser.L_CURLY)
            self.state = 111
            self.gameBody()
            self.state = 112
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


        def LEMMA(self):
            return self.getToken(ProofParser.LEMMA, 0)

        def lemmas(self):
            return self.getTypedRuleContext(ProofParser.LemmasContext,0)


        def getRuleIndex(self):
            return ProofParser.RULE_proof

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitProof" ):
                return visitor.visitProof(self)
            else:
                return visitor.visitChildren(self)




    def proof(self):

        localctx = ProofParser.ProofContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_proof)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 114
            self.match(ProofParser.PROOF)
            self.state = 115
            self.match(ProofParser.COLON)
            self.state = 119
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==9:
                self.state = 116
                self.match(ProofParser.LET)
                self.state = 117
                self.match(ProofParser.COLON)
                self.state = 118
                self.lets()


            self.state = 124
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==6:
                self.state = 121
                self.match(ProofParser.ASSUME)
                self.state = 122
                self.match(ProofParser.COLON)
                self.state = 123
                self.assumptions()


            self.state = 129
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 126
                self.match(ProofParser.LEMMA)
                self.state = 127
                self.match(ProofParser.COLON)
                self.state = 128
                self.lemmas()


            self.state = 131
            self.match(ProofParser.THEOREM)
            self.state = 132
            self.match(ProofParser.COLON)
            self.state = 133
            self.theorem()
            self.state = 134
            self.match(ProofParser.GAMES)
            self.state = 135
            self.match(ProofParser.COLON)
            self.state = 136
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
        self.enterRule(localctx, 8, self.RULE_lets)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 143
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while ((((_la - 17)) & ~0x3f) == 0 and ((1 << (_la - 17)) & 4620711333585747969) != 0):
                self.state = 138
                self.field()
                self.state = 139
                self.match(ProofParser.SEMI)
                self.state = 145
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

        def parameterizedGame(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ParameterizedGameContext)
            else:
                return self.getTypedRuleContext(ProofParser.ParameterizedGameContext,i)


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
        self.enterRule(localctx, 10, self.RULE_assumptions)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 151
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==79:
                self.state = 146
                self.parameterizedGame()
                self.state = 147
                self.match(ProofParser.SEMI)
                self.state = 153
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 159
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==10:
                self.state = 154
                self.match(ProofParser.CALLS)
                self.state = 155
                _la = self._input.LA(1)
                if not(_la==21 or _la==36):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 156
                self.expression(0)
                self.state = 157
                self.match(ProofParser.SEMI)


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LemmasContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def lemmaEntry(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.LemmaEntryContext)
            else:
                return self.getTypedRuleContext(ProofParser.LemmaEntryContext,i)


        def getRuleIndex(self):
            return ProofParser.RULE_lemmas

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLemmas" ):
                return visitor.visitLemmas(self)
            else:
                return visitor.visitChildren(self)




    def lemmas(self):

        localctx = ProofParser.LemmasContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_lemmas)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 164
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==79:
                self.state = 161
                self.lemmaEntry()
                self.state = 166
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LemmaEntryContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def parameterizedGame(self):
            return self.getTypedRuleContext(ProofParser.ParameterizedGameContext,0)


        def BY(self):
            return self.getToken(ProofParser.BY, 0)

        def FILESTRING(self):
            return self.getToken(ProofParser.FILESTRING, 0)

        def SEMI(self):
            return self.getToken(ProofParser.SEMI, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_lemmaEntry

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLemmaEntry" ):
                return visitor.visitLemmaEntry(self)
            else:
                return visitor.visitChildren(self)




    def lemmaEntry(self):

        localctx = ProofParser.LemmaEntryContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_lemmaEntry)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 167
            self.parameterizedGame()
            self.state = 168
            self.match(ProofParser.BY)
            self.state = 169
            self.match(ProofParser.FILESTRING)
            self.state = 170
            self.match(ProofParser.SEMI)
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

        def parameterizedGame(self):
            return self.getTypedRuleContext(ProofParser.ParameterizedGameContext,0)


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
        self.enterRule(localctx, 16, self.RULE_theorem)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 172
            self.parameterizedGame()
            self.state = 173
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


        def stepAssumption(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.StepAssumptionContext)
            else:
                return self.getTypedRuleContext(ProofParser.StepAssumptionContext,i)


        def getRuleIndex(self):
            return ProofParser.RULE_gameList

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGameList" ):
                return visitor.visitGameList(self)
            else:
                return visitor.visitChildren(self)




    def gameList(self):

        localctx = ProofParser.GameListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_gameList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 175
            self.gameStep()
            self.state = 176
            self.match(ProofParser.SEMI)
            self.state = 184
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==6 or _la==11 or _la==79:
                self.state = 182
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [79]:
                    self.state = 177
                    self.gameStep()
                    self.state = 178
                    self.match(ProofParser.SEMI)
                    pass
                elif token in [11]:
                    self.state = 180
                    self.induction()
                    pass
                elif token in [6]:
                    self.state = 181
                    self.stepAssumption()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 186
                self._errHandler.sync(self)
                _la = self._input.LA(1)

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


        def getRuleIndex(self):
            return ProofParser.RULE_gameStep

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)



    class RegularStepContext(GameStepContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.GameStepContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def AGAINST(self):
            return self.getToken(ProofParser.AGAINST, 0)
        def gameAdversary(self):
            return self.getTypedRuleContext(ProofParser.GameAdversaryContext,0)

        def concreteGame(self):
            return self.getTypedRuleContext(ProofParser.ConcreteGameContext,0)

        def parameterizedGame(self):
            return self.getTypedRuleContext(ProofParser.ParameterizedGameContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRegularStep" ):
                return visitor.visitRegularStep(self)
            else:
                return visitor.visitChildren(self)


    class ReductionStepContext(GameStepContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.GameStepContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def concreteGame(self):
            return self.getTypedRuleContext(ProofParser.ConcreteGameContext,0)

        def COMPOSE(self):
            return self.getToken(ProofParser.COMPOSE, 0)
        def parameterizedGame(self):
            return self.getTypedRuleContext(ProofParser.ParameterizedGameContext,0)

        def AGAINST(self):
            return self.getToken(ProofParser.AGAINST, 0)
        def gameAdversary(self):
            return self.getTypedRuleContext(ProofParser.GameAdversaryContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitReductionStep" ):
                return visitor.visitReductionStep(self)
            else:
                return visitor.visitChildren(self)



    def gameStep(self):

        localctx = ProofParser.GameStepContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_gameStep)
        try:
            self.state = 200
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                localctx = ProofParser.ReductionStepContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 187
                self.concreteGame()
                self.state = 188
                self.match(ProofParser.COMPOSE)
                self.state = 189
                self.parameterizedGame()
                self.state = 190
                self.match(ProofParser.AGAINST)
                self.state = 191
                self.gameAdversary()
                pass

            elif la_ == 2:
                localctx = ProofParser.RegularStepContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 195
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input,13,self._ctx)
                if la_ == 1:
                    self.state = 193
                    self.concreteGame()
                    pass

                elif la_ == 2:
                    self.state = 194
                    self.parameterizedGame()
                    pass


                self.state = 197
                self.match(ProofParser.AGAINST)
                self.state = 198
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

        def integerExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.IntegerExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.IntegerExpressionContext,i)


        def TO(self):
            return self.getToken(ProofParser.TO, 0)

        def R_PAREN(self):
            return self.getToken(ProofParser.R_PAREN, 0)

        def L_CURLY(self):
            return self.getToken(ProofParser.L_CURLY, 0)

        def gameList(self):
            return self.getTypedRuleContext(ProofParser.GameListContext,0)


        def R_CURLY(self):
            return self.getToken(ProofParser.R_CURLY, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_induction

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitInduction" ):
                return visitor.visitInduction(self)
            else:
                return visitor.visitChildren(self)




    def induction(self):

        localctx = ProofParser.InductionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_induction)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 202
            self.match(ProofParser.INDUCTION)
            self.state = 203
            self.match(ProofParser.L_PAREN)
            self.state = 204
            self.match(ProofParser.ID)
            self.state = 205
            self.match(ProofParser.FROM)
            self.state = 206
            self.integerExpression(0)
            self.state = 207
            self.match(ProofParser.TO)
            self.state = 208
            self.integerExpression(0)
            self.state = 209
            self.match(ProofParser.R_PAREN)
            self.state = 210
            self.match(ProofParser.L_CURLY)
            self.state = 211
            self.gameList()
            self.state = 212
            self.match(ProofParser.R_CURLY)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class StepAssumptionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ASSUME(self):
            return self.getToken(ProofParser.ASSUME, 0)

        def expression(self):
            return self.getTypedRuleContext(ProofParser.ExpressionContext,0)


        def SEMI(self):
            return self.getToken(ProofParser.SEMI, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_stepAssumption

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitStepAssumption" ):
                return visitor.visitStepAssumption(self)
            else:
                return visitor.visitChildren(self)




    def stepAssumption(self):

        localctx = ProofParser.StepAssumptionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_stepAssumption)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 214
            self.match(ProofParser.ASSUME)
            self.state = 215
            self.expression(0)
            self.state = 216
            self.match(ProofParser.SEMI)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class GameFieldContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def PERIOD(self):
            return self.getToken(ProofParser.PERIOD, 0)

        def ID(self):
            return self.getToken(ProofParser.ID, 0)

        def concreteGame(self):
            return self.getTypedRuleContext(ProofParser.ConcreteGameContext,0)


        def parameterizedGame(self):
            return self.getTypedRuleContext(ProofParser.ParameterizedGameContext,0)


        def getRuleIndex(self):
            return ProofParser.RULE_gameField

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGameField" ):
                return visitor.visitGameField(self)
            else:
                return visitor.visitChildren(self)




    def gameField(self):

        localctx = ProofParser.GameFieldContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_gameField)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 220
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,15,self._ctx)
            if la_ == 1:
                self.state = 218
                self.concreteGame()
                pass

            elif la_ == 2:
                self.state = 219
                self.parameterizedGame()
                pass


            self.state = 222
            self.match(ProofParser.PERIOD)
            self.state = 223
            self.match(ProofParser.ID)
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
            return self.getTypedRuleContext(ProofParser.ParameterizedGameContext,0)


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
        self.enterRule(localctx, 28, self.RULE_concreteGame)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 225
            self.parameterizedGame()
            self.state = 226
            self.match(ProofParser.PERIOD)
            self.state = 227
            self.match(ProofParser.ID)
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

        def parameterizedGame(self):
            return self.getTypedRuleContext(ProofParser.ParameterizedGameContext,0)


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
        self.enterRule(localctx, 30, self.RULE_gameAdversary)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 229
            self.parameterizedGame()
            self.state = 230
            self.match(ProofParser.PERIOD)
            self.state = 231
            self.match(ProofParser.ADVERSARY)
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
        self.enterRule(localctx, 32, self.RULE_game)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 233
            self.match(ProofParser.GAME)
            self.state = 234
            self.match(ProofParser.ID)
            self.state = 235
            self.match(ProofParser.L_PAREN)
            self.state = 237
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 17)) & ~0x3f) == 0 and ((1 << (_la - 17)) & 4620711333585747969) != 0):
                self.state = 236
                self.paramList()


            self.state = 239
            self.match(ProofParser.R_PAREN)
            self.state = 240
            self.match(ProofParser.L_CURLY)
            self.state = 241
            self.gameBody()
            self.state = 242
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
        self.enterRule(localctx, 34, self.RULE_gameBody)
        self._la = 0 # Token type
        try:
            self.state = 276
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,22,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 249
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,17,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 244
                        self.field()
                        self.state = 245
                        self.match(ProofParser.SEMI) 
                    self.state = 251
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,17,self._ctx)

                self.state = 253 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 252
                    self.method()
                    self.state = 255 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (((((_la - 17)) & ~0x3f) == 0 and ((1 << (_la - 17)) & 4674754529114193921) != 0)):
                        break

                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 262
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,19,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 257
                        self.field()
                        self.state = 258
                        self.match(ProofParser.SEMI) 
                    self.state = 264
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,19,self._ctx)

                self.state = 268
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while ((((_la - 17)) & ~0x3f) == 0 and ((1 << (_la - 17)) & 4674754529114193921) != 0):
                    self.state = 265
                    self.method()
                    self.state = 270
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 272 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 271
                    self.gamePhase()
                    self.state = 274 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==66):
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
        self.enterRule(localctx, 36, self.RULE_gamePhase)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 278
            self.match(ProofParser.PHASE)
            self.state = 279
            self.match(ProofParser.L_CURLY)
            self.state = 281 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 280
                self.method()
                self.state = 283 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (((((_la - 17)) & ~0x3f) == 0 and ((1 << (_la - 17)) & 4674754529114193921) != 0)):
                    break

            self.state = 285
            self.match(ProofParser.ORACLES)
            self.state = 286
            self.match(ProofParser.COLON)
            self.state = 287
            self.match(ProofParser.L_SQUARE)
            self.state = 288
            self.id_()
            self.state = 293
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==25:
                self.state = 289
                self.match(ProofParser.COMMA)
                self.state = 290
                self.id_()
                self.state = 295
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 296
            self.match(ProofParser.R_SQUARE)
            self.state = 297
            self.match(ProofParser.SEMI)
            self.state = 298
            self.match(ProofParser.R_CURLY)
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
        self.enterRule(localctx, 38, self.RULE_field)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 300
            self.variable()
            self.state = 303
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==28:
                self.state = 301
                self.match(ProofParser.EQUALS)
                self.state = 302
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
        self.enterRule(localctx, 40, self.RULE_initializedField)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 305
            self.variable()
            self.state = 306
            self.match(ProofParser.EQUALS)
            self.state = 307
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


        def block(self):
            return self.getTypedRuleContext(ProofParser.BlockContext,0)


        def getRuleIndex(self):
            return ProofParser.RULE_method

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMethod" ):
                return visitor.visitMethod(self)
            else:
                return visitor.visitChildren(self)




    def method(self):

        localctx = ProofParser.MethodContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_method)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 309
            self.methodSignature()
            self.state = 310
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
            return self.getToken(ProofParser.L_CURLY, 0)

        def R_CURLY(self):
            return self.getToken(ProofParser.R_CURLY, 0)

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
        self.enterRule(localctx, 44, self.RULE_block)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 312
            self.match(ProofParser.L_CURLY)
            self.state = 316
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 3240326738827968512) != 0) or ((((_la - 69)) & ~0x3f) == 0 and ((1 << (_la - 69)) & 2035) != 0):
                self.state = 313
                self.statement()
                self.state = 318
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 319
            self.match(ProofParser.R_CURLY)
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



    class UniqueSampleStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def type_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.TypeContext)
            else:
                return self.getTypedRuleContext(ProofParser.TypeContext,i)

        def lvalue(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.LvalueContext)
            else:
                return self.getTypedRuleContext(ProofParser.LvalueContext,i)

        def SAMPUNIQ(self):
            return self.getToken(ProofParser.SAMPUNIQ, 0)
        def L_SQUARE(self):
            return self.getToken(ProofParser.L_SQUARE, 0)
        def R_SQUARE(self):
            return self.getToken(ProofParser.R_SQUARE, 0)
        def SEMI(self):
            return self.getToken(ProofParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitUniqueSampleStatement" ):
                return visitor.visitUniqueSampleStatement(self)
            else:
                return visitor.visitChildren(self)


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
        def block(self):
            return self.getTypedRuleContext(ProofParser.BlockContext,0)


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
        def block(self):
            return self.getTypedRuleContext(ProofParser.BlockContext,0)


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
        def block(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.BlockContext)
            else:
                return self.getTypedRuleContext(ProofParser.BlockContext,i)

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


    class UniqueSampleNoTypeStatementContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def lvalue(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.LvalueContext)
            else:
                return self.getTypedRuleContext(ProofParser.LvalueContext,i)

        def SAMPUNIQ(self):
            return self.getToken(ProofParser.SAMPUNIQ, 0)
        def L_SQUARE(self):
            return self.getToken(ProofParser.L_SQUARE, 0)
        def R_SQUARE(self):
            return self.getToken(ProofParser.R_SQUARE, 0)
        def type_(self):
            return self.getTypedRuleContext(ProofParser.TypeContext,0)

        def SEMI(self):
            return self.getToken(ProofParser.SEMI, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitUniqueSampleNoTypeStatement" ):
                return visitor.visitUniqueSampleNoTypeStatement(self)
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
        self.enterRule(localctx, 46, self.RULE_statement)
        self._la = 0 # Token type
        try:
            self.state = 417
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,30,self._ctx)
            if la_ == 1:
                localctx = ProofParser.VarDeclStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 321
                self.type_(0)
                self.state = 322
                self.id_()
                self.state = 323
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 2:
                localctx = ProofParser.VarDeclWithValueStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 325
                self.type_(0)
                self.state = 326
                self.lvalue()
                self.state = 327
                self.match(ProofParser.EQUALS)
                self.state = 328
                self.expression(0)
                self.state = 329
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 3:
                localctx = ProofParser.VarDeclWithSampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 331
                self.type_(0)
                self.state = 332
                self.lvalue()
                self.state = 333
                self.match(ProofParser.SAMPLES)
                self.state = 334
                self.expression(0)
                self.state = 335
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 4:
                localctx = ProofParser.AssignmentStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 337
                self.lvalue()
                self.state = 338
                self.match(ProofParser.EQUALS)
                self.state = 339
                self.expression(0)
                self.state = 340
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 5:
                localctx = ProofParser.SampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 5)
                self.state = 342
                self.lvalue()
                self.state = 343
                self.match(ProofParser.SAMPLES)
                self.state = 344
                self.expression(0)
                self.state = 345
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 6:
                localctx = ProofParser.UniqueSampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 6)
                self.state = 347
                self.type_(0)
                self.state = 348
                self.lvalue()
                self.state = 349
                self.match(ProofParser.SAMPUNIQ)
                self.state = 350
                self.match(ProofParser.L_SQUARE)
                self.state = 351
                self.lvalue()
                self.state = 352
                self.match(ProofParser.R_SQUARE)
                self.state = 353
                self.type_(0)
                self.state = 354
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 7:
                localctx = ProofParser.UniqueSampleNoTypeStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 7)
                self.state = 356
                self.lvalue()
                self.state = 357
                self.match(ProofParser.SAMPUNIQ)
                self.state = 358
                self.match(ProofParser.L_SQUARE)
                self.state = 359
                self.lvalue()
                self.state = 360
                self.match(ProofParser.R_SQUARE)
                self.state = 361
                self.type_(0)
                self.state = 362
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 8:
                localctx = ProofParser.FunctionCallStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 8)
                self.state = 364
                self.expression(0)
                self.state = 365
                self.match(ProofParser.L_PAREN)
                self.state = 367
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 2374509710465990656) != 0) or ((((_la - 69)) & ~0x3f) == 0 and ((1 << (_la - 69)) & 2035) != 0):
                    self.state = 366
                    self.argList()


                self.state = 369
                self.match(ProofParser.R_PAREN)
                self.state = 370
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 9:
                localctx = ProofParser.ReturnStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 9)
                self.state = 372
                self.match(ProofParser.RETURN)
                self.state = 373
                self.expression(0)
                self.state = 374
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 10:
                localctx = ProofParser.IfStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 10)
                self.state = 376
                self.match(ProofParser.IF)
                self.state = 377
                self.match(ProofParser.L_PAREN)
                self.state = 378
                self.expression(0)
                self.state = 379
                self.match(ProofParser.R_PAREN)
                self.state = 380
                self.block()
                self.state = 390
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,28,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 381
                        self.match(ProofParser.ELSE)
                        self.state = 382
                        self.match(ProofParser.IF)
                        self.state = 383
                        self.match(ProofParser.L_PAREN)
                        self.state = 384
                        self.expression(0)
                        self.state = 385
                        self.match(ProofParser.R_PAREN)
                        self.state = 386
                        self.block() 
                    self.state = 392
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,28,self._ctx)

                self.state = 395
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==68:
                    self.state = 393
                    self.match(ProofParser.ELSE)
                    self.state = 394
                    self.block()


                pass

            elif la_ == 11:
                localctx = ProofParser.NumericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 11)
                self.state = 397
                self.match(ProofParser.FOR)
                self.state = 398
                self.match(ProofParser.L_PAREN)
                self.state = 399
                self.match(ProofParser.INTTYPE)
                self.state = 400
                self.id_()
                self.state = 401
                self.match(ProofParser.EQUALS)
                self.state = 402
                self.expression(0)
                self.state = 403
                self.match(ProofParser.TO)
                self.state = 404
                self.expression(0)
                self.state = 405
                self.match(ProofParser.R_PAREN)
                self.state = 406
                self.block()
                pass

            elif la_ == 12:
                localctx = ProofParser.GenericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 12)
                self.state = 408
                self.match(ProofParser.FOR)
                self.state = 409
                self.match(ProofParser.L_PAREN)
                self.state = 410
                self.type_(0)
                self.state = 411
                self.id_()
                self.state = 412
                self.match(ProofParser.IN)
                self.state = 413
                self.expression(0)
                self.state = 414
                self.match(ProofParser.R_PAREN)
                self.state = 415
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
                return self.getTypedRuleContexts(ProofParser.IdContext)
            else:
                return self.getTypedRuleContext(ProofParser.IdContext,i)


        def parameterizedGame(self):
            return self.getTypedRuleContext(ProofParser.ParameterizedGameContext,0)


        def THIS(self):
            return self.getToken(ProofParser.THIS, 0)

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

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)


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
        self.enterRule(localctx, 48, self.RULE_lvalue)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 422
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,31,self._ctx)
            if la_ == 1:
                self.state = 419
                self.id_()
                pass

            elif la_ == 2:
                self.state = 420
                self.parameterizedGame()
                pass

            elif la_ == 3:
                self.state = 421
                self.match(ProofParser.THIS)
                pass


            self.state = 432
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,33,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 430
                    self._errHandler.sync(self)
                    token = self._input.LA(1)
                    if token in [26]:
                        self.state = 424
                        self.match(ProofParser.PERIOD)
                        self.state = 425
                        self.id_()
                        pass
                    elif token in [17]:
                        self.state = 426
                        self.match(ProofParser.L_SQUARE)
                        self.state = 427
                        self.expression(0)
                        self.state = 428
                        self.match(ProofParser.R_SQUARE)
                        pass
                    else:
                        raise NoViableAltException(self)
             
                self.state = 434
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,33,self._ctx)

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
            return self.getToken(ProofParser.DETERMINISTIC, 0)

        def INJECTIVE(self):
            return self.getToken(ProofParser.INJECTIVE, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_methodModifier

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMethodModifier" ):
                return visitor.visitMethodModifier(self)
            else:
                return visitor.visitChildren(self)




    def methodModifier(self):

        localctx = ProofParser.MethodModifierContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_methodModifier)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 435
            _la = self._input.LA(1)
            if not(_la==71 or _la==72):
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
            return self.getTypedRuleContext(ProofParser.TypeContext,0)


        def id_(self):
            return self.getTypedRuleContext(ProofParser.IdContext,0)


        def L_PAREN(self):
            return self.getToken(ProofParser.L_PAREN, 0)

        def R_PAREN(self):
            return self.getToken(ProofParser.R_PAREN, 0)

        def methodModifier(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.MethodModifierContext)
            else:
                return self.getTypedRuleContext(ProofParser.MethodModifierContext,i)


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
        self.enterRule(localctx, 52, self.RULE_methodSignature)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 440
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==71 or _la==72:
                self.state = 437
                self.methodModifier()
                self.state = 442
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 443
            self.type_(0)
            self.state = 444
            self.id_()
            self.state = 445
            self.match(ProofParser.L_PAREN)
            self.state = 447
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 17)) & ~0x3f) == 0 and ((1 << (_la - 17)) & 4620711333585747969) != 0):
                self.state = 446
                self.paramList()


            self.state = 449
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
        self.enterRule(localctx, 54, self.RULE_paramList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 451
            self.variable()
            self.state = 456
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==25:
                self.state = 452
                self.match(ProofParser.COMMA)
                self.state = 453
                self.variable()
                self.state = 458
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


    class BoolExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def bool_(self):
            return self.getTypedRuleContext(ProofParser.BoolContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBoolExp" ):
                return visitor.visitBoolExp(self)
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


    class NoneExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def NONE(self):
            return self.getToken(ProofParser.NONE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNoneExp" ):
                return visitor.visitNoneExp(self)
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


    class OnesExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def ONES_CARET(self):
            return self.getToken(ProofParser.ONES_CARET, 0)
        def integerAtom(self):
            return self.getTypedRuleContext(ProofParser.IntegerAtomContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOnesExp" ):
                return visitor.visitOnesExp(self)
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


    class MinusExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def SUBTRACT(self):
            return self.getToken(ProofParser.SUBTRACT, 0)
        def expression(self):
            return self.getTypedRuleContext(ProofParser.ExpressionContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMinusExp" ):
                return visitor.visitMinusExp(self)
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


    class ZerosExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def ZEROS_CARET(self):
            return self.getToken(ProofParser.ZEROS_CARET, 0)
        def integerAtom(self):
            return self.getTypedRuleContext(ProofParser.IntegerAtomContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitZerosExp" ):
                return visitor.visitZerosExp(self)
            else:
                return visitor.visitChildren(self)


    class ExponentiationExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.ExpressionContext,i)

        def CARET(self):
            return self.getToken(ProofParser.CARET, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitExponentiationExp" ):
                return visitor.visitExponentiationExp(self)
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
        _startState = 56
        self.enterRecursionRule(localctx, 56, self.RULE_expression, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 506
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,41,self._ctx)
            if la_ == 1:
                localctx = ProofParser.NotExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 460
                self.match(ProofParser.NOT)
                self.state = 461
                self.expression(31)
                pass

            elif la_ == 2:
                localctx = ProofParser.SizeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 462
                self.match(ProofParser.VBAR)
                self.state = 463
                self.expression(0)
                self.state = 464
                self.match(ProofParser.VBAR)
                pass

            elif la_ == 3:
                localctx = ProofParser.MinusExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 466
                self.match(ProofParser.SUBTRACT)
                self.state = 467
                self.expression(26)
                pass

            elif la_ == 4:
                localctx = ProofParser.LvalueExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 468
                self.lvalue()
                pass

            elif la_ == 5:
                localctx = ProofParser.CreateTupleExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 469
                self.match(ProofParser.L_SQUARE)
                self.state = 478
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 2374509710465990656) != 0) or ((((_la - 69)) & ~0x3f) == 0 and ((1 << (_la - 69)) & 2035) != 0):
                    self.state = 470
                    self.expression(0)
                    self.state = 475
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==25:
                        self.state = 471
                        self.match(ProofParser.COMMA)
                        self.state = 472
                        self.expression(0)
                        self.state = 477
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 480
                self.match(ProofParser.R_SQUARE)
                pass

            elif la_ == 6:
                localctx = ProofParser.CreateSetExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 481
                self.match(ProofParser.L_CURLY)
                self.state = 490
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 2374509710465990656) != 0) or ((((_la - 69)) & ~0x3f) == 0 and ((1 << (_la - 69)) & 2035) != 0):
                    self.state = 482
                    self.expression(0)
                    self.state = 487
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==25:
                        self.state = 483
                        self.match(ProofParser.COMMA)
                        self.state = 484
                        self.expression(0)
                        self.state = 489
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 492
                self.match(ProofParser.R_CURLY)
                pass

            elif la_ == 7:
                localctx = ProofParser.TypeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 493
                self.type_(0)
                pass

            elif la_ == 8:
                localctx = ProofParser.ZerosExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 494
                self.match(ProofParser.ZEROS_CARET)
                self.state = 495
                self.integerAtom()
                pass

            elif la_ == 9:
                localctx = ProofParser.OnesExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 496
                self.match(ProofParser.ONES_CARET)
                self.state = 497
                self.integerAtom()
                pass

            elif la_ == 10:
                localctx = ProofParser.BinaryNumExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 498
                self.match(ProofParser.BINARYNUM)
                pass

            elif la_ == 11:
                localctx = ProofParser.IntExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 499
                self.match(ProofParser.INT)
                pass

            elif la_ == 12:
                localctx = ProofParser.BoolExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 500
                self.bool_()
                pass

            elif la_ == 13:
                localctx = ProofParser.NoneExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 501
                self.match(ProofParser.NONE)
                pass

            elif la_ == 14:
                localctx = ProofParser.ParenExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 502
                self.match(ProofParser.L_PAREN)
                self.state = 503
                self.expression(0)
                self.state = 504
                self.match(ProofParser.R_PAREN)
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 574
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,44,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 572
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,43,self._ctx)
                    if la_ == 1:
                        localctx = ProofParser.ExponentiationExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 508
                        if not self.precpred(self._ctx, 29):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 29)")
                        self.state = 509
                        self.match(ProofParser.CARET)
                        self.state = 510
                        self.expression(29)
                        pass

                    elif la_ == 2:
                        localctx = ProofParser.MultiplyExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 511
                        if not self.precpred(self._ctx, 28):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 28)")
                        self.state = 512
                        self.match(ProofParser.TIMES)
                        self.state = 513
                        self.expression(29)
                        pass

                    elif la_ == 3:
                        localctx = ProofParser.DivideExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 514
                        if not self.precpred(self._ctx, 27):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 27)")
                        self.state = 515
                        self.match(ProofParser.DIVIDE)
                        self.state = 516
                        self.expression(28)
                        pass

                    elif la_ == 4:
                        localctx = ProofParser.AddExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 517
                        if not self.precpred(self._ctx, 25):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 25)")
                        self.state = 518
                        self.match(ProofParser.PLUS)
                        self.state = 519
                        self.expression(26)
                        pass

                    elif la_ == 5:
                        localctx = ProofParser.SubtractExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 520
                        if not self.precpred(self._ctx, 24):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 24)")
                        self.state = 521
                        self.match(ProofParser.SUBTRACT)
                        self.state = 522
                        self.expression(25)
                        pass

                    elif la_ == 6:
                        localctx = ProofParser.EqualsExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 523
                        if not self.precpred(self._ctx, 23):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 23)")
                        self.state = 524
                        self.match(ProofParser.EQUALSCOMPARE)
                        self.state = 525
                        self.expression(24)
                        pass

                    elif la_ == 7:
                        localctx = ProofParser.NotEqualsExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 526
                        if not self.precpred(self._ctx, 22):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 22)")
                        self.state = 527
                        self.match(ProofParser.NOTEQUALS)
                        self.state = 528
                        self.expression(23)
                        pass

                    elif la_ == 8:
                        localctx = ProofParser.GtExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 529
                        if not self.precpred(self._ctx, 21):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 21)")
                        self.state = 530
                        self.match(ProofParser.R_ANGLE)
                        self.state = 531
                        self.expression(22)
                        pass

                    elif la_ == 9:
                        localctx = ProofParser.LtExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 532
                        if not self.precpred(self._ctx, 20):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 20)")
                        self.state = 533
                        self.match(ProofParser.L_ANGLE)
                        self.state = 534
                        self.expression(21)
                        pass

                    elif la_ == 10:
                        localctx = ProofParser.GeqExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 535
                        if not self.precpred(self._ctx, 19):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 19)")
                        self.state = 536
                        self.match(ProofParser.GEQ)
                        self.state = 537
                        self.expression(20)
                        pass

                    elif la_ == 11:
                        localctx = ProofParser.LeqExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 538
                        if not self.precpred(self._ctx, 18):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 18)")
                        self.state = 539
                        self.match(ProofParser.LEQ)
                        self.state = 540
                        self.expression(19)
                        pass

                    elif la_ == 12:
                        localctx = ProofParser.InExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 541
                        if not self.precpred(self._ctx, 17):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 17)")
                        self.state = 542
                        self.match(ProofParser.IN)
                        self.state = 543
                        self.expression(18)
                        pass

                    elif la_ == 13:
                        localctx = ProofParser.SubsetsExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 544
                        if not self.precpred(self._ctx, 16):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 16)")
                        self.state = 545
                        self.match(ProofParser.SUBSETS)
                        self.state = 546
                        self.expression(17)
                        pass

                    elif la_ == 14:
                        localctx = ProofParser.AndExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 547
                        if not self.precpred(self._ctx, 15):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 15)")
                        self.state = 548
                        self.match(ProofParser.AND)
                        self.state = 549
                        self.expression(16)
                        pass

                    elif la_ == 15:
                        localctx = ProofParser.OrExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 550
                        if not self.precpred(self._ctx, 14):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 14)")
                        self.state = 551
                        self.match(ProofParser.OR)
                        self.state = 552
                        self.expression(15)
                        pass

                    elif la_ == 16:
                        localctx = ProofParser.UnionExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 553
                        if not self.precpred(self._ctx, 13):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 13)")
                        self.state = 554
                        self.match(ProofParser.UNION)
                        self.state = 555
                        self.expression(14)
                        pass

                    elif la_ == 17:
                        localctx = ProofParser.SetMinusExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 556
                        if not self.precpred(self._ctx, 12):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 12)")
                        self.state = 557
                        self.match(ProofParser.BACKSLASH)
                        self.state = 558
                        self.expression(13)
                        pass

                    elif la_ == 18:
                        localctx = ProofParser.FnCallExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 559
                        if not self.precpred(self._ctx, 33):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 33)")
                        self.state = 560
                        self.match(ProofParser.L_PAREN)
                        self.state = 562
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)
                        if (((_la) & ~0x3f) == 0 and ((1 << _la) & 2374509710465990656) != 0) or ((((_la - 69)) & ~0x3f) == 0 and ((1 << (_la - 69)) & 2035) != 0):
                            self.state = 561
                            self.argList()


                        self.state = 564
                        self.match(ProofParser.R_PAREN)
                        pass

                    elif la_ == 19:
                        localctx = ProofParser.SliceExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 565
                        if not self.precpred(self._ctx, 32):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 32)")
                        self.state = 566
                        self.match(ProofParser.L_SQUARE)
                        self.state = 567
                        self.integerExpression(0)
                        self.state = 568
                        self.match(ProofParser.COLON)
                        self.state = 569
                        self.integerExpression(0)
                        self.state = 570
                        self.match(ProofParser.R_SQUARE)
                        pass

             
                self.state = 576
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,44,self._ctx)

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
        self.enterRule(localctx, 58, self.RULE_argList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 577
            self.expression(0)
            self.state = 582
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==25:
                self.state = 578
                self.match(ProofParser.COMMA)
                self.state = 579
                self.expression(0)
                self.state = 584
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
        self.enterRule(localctx, 60, self.RULE_variable)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 585
            self.type_(0)
            self.state = 586
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
            return self.getToken(ProofParser.ID, 0)

        def L_PAREN(self):
            return self.getToken(ProofParser.L_PAREN, 0)

        def R_PAREN(self):
            return self.getToken(ProofParser.R_PAREN, 0)

        def argList(self):
            return self.getTypedRuleContext(ProofParser.ArgListContext,0)


        def getRuleIndex(self):
            return ProofParser.RULE_parameterizedGame

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitParameterizedGame" ):
                return visitor.visitParameterizedGame(self)
            else:
                return visitor.visitChildren(self)




    def parameterizedGame(self):

        localctx = ProofParser.ParameterizedGameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 62, self.RULE_parameterizedGame)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 588
            self.match(ProofParser.ID)
            self.state = 589
            self.match(ProofParser.L_PAREN)
            self.state = 591
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 2374509710465990656) != 0) or ((((_la - 69)) & ~0x3f) == 0 and ((1 << (_la - 69)) & 2035) != 0):
                self.state = 590
                self.argList()


            self.state = 593
            self.match(ProofParser.R_PAREN)
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


    class LvalueTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def lvalue(self):
            return self.getTypedRuleContext(ProofParser.LvalueContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLvalueType" ):
                return visitor.visitLvalueType(self)
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


    class VoidTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def VOID(self):
            return self.getToken(ProofParser.VOID, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVoidType" ):
                return visitor.visitVoidType(self)
            else:
                return visitor.visitChildren(self)


    class RandomFunctionTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def RANDOMFUNCTIONS(self):
            return self.getToken(ProofParser.RANDOMFUNCTIONS, 0)
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
            if hasattr( visitor, "visitRandomFunctionType" ):
                return visitor.visitRandomFunctionType(self)
            else:
                return visitor.visitChildren(self)


    class ModIntTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def modint(self):
            return self.getTypedRuleContext(ProofParser.ModintContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitModIntType" ):
                return visitor.visitModIntType(self)
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

        def L_SQUARE(self):
            return self.getToken(ProofParser.L_SQUARE, 0)
        def type_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.TypeContext)
            else:
                return self.getTypedRuleContext(ProofParser.TypeContext,i)

        def R_SQUARE(self):
            return self.getToken(ProofParser.R_SQUARE, 0)
        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(ProofParser.COMMA)
            else:
                return self.getToken(ProofParser.COMMA, i)

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
        _startState = 64
        self.enterRecursionRule(localctx, 64, self.RULE_type, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 634
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [45]:
                localctx = ProofParser.SetTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 596
                self.set_()
                pass
            elif token in [46]:
                localctx = ProofParser.BoolTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 597
                self.match(ProofParser.BOOL)
                pass
            elif token in [47]:
                localctx = ProofParser.VoidTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 598
                self.match(ProofParser.VOID)
                pass
            elif token in [49]:
                localctx = ProofParser.MapTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 599
                self.match(ProofParser.MAP)
                self.state = 600
                self.match(ProofParser.L_ANGLE)
                self.state = 601
                self.type_(0)
                self.state = 602
                self.match(ProofParser.COMMA)
                self.state = 603
                self.type_(0)
                self.state = 604
                self.match(ProofParser.R_ANGLE)
                pass
            elif token in [54]:
                localctx = ProofParser.ArrayTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 606
                self.match(ProofParser.ARRAY)
                self.state = 607
                self.match(ProofParser.L_ANGLE)
                self.state = 608
                self.type_(0)
                self.state = 609
                self.match(ProofParser.COMMA)
                self.state = 610
                self.integerExpression(0)
                self.state = 611
                self.match(ProofParser.R_ANGLE)
                pass
            elif token in [55]:
                localctx = ProofParser.RandomFunctionTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 613
                self.match(ProofParser.RANDOMFUNCTIONS)
                self.state = 614
                self.match(ProofParser.L_ANGLE)
                self.state = 615
                self.type_(0)
                self.state = 616
                self.match(ProofParser.COMMA)
                self.state = 617
                self.type_(0)
                self.state = 618
                self.match(ProofParser.R_ANGLE)
                pass
            elif token in [48]:
                localctx = ProofParser.IntTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 620
                self.match(ProofParser.INTTYPE)
                pass
            elif token in [17]:
                localctx = ProofParser.ProductTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 621
                self.match(ProofParser.L_SQUARE)
                self.state = 622
                self.type_(0)
                self.state = 625 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 623
                    self.match(ProofParser.COMMA)
                    self.state = 624
                    self.type_(0)
                    self.state = 627 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==25):
                        break

                self.state = 629
                self.match(ProofParser.R_SQUARE)
                pass
            elif token in [52]:
                localctx = ProofParser.BitStringTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 631
                self.bitstring()
                pass
            elif token in [53]:
                localctx = ProofParser.ModIntTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 632
                self.modint()
                pass
            elif token in [61, 70, 79]:
                localctx = ProofParser.LvalueTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 633
                self.lvalue()
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 640
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,49,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = ProofParser.OptionalTypeContext(self, ProofParser.TypeContext(self, _parentctx, _parentState))
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_type)
                    self.state = 636
                    if not self.precpred(self._ctx, 12):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 12)")
                    self.state = 637
                    self.match(ProofParser.QUESTION) 
                self.state = 642
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,49,self._ctx)

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


        def INT(self):
            return self.getToken(ProofParser.INT, 0)

        def BINARYNUM(self):
            return self.getToken(ProofParser.BINARYNUM, 0)

        def L_PAREN(self):
            return self.getToken(ProofParser.L_PAREN, 0)

        def integerExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.IntegerExpressionContext)
            else:
                return self.getTypedRuleContext(ProofParser.IntegerExpressionContext,i)


        def R_PAREN(self):
            return self.getToken(ProofParser.R_PAREN, 0)

        def TIMES(self):
            return self.getToken(ProofParser.TIMES, 0)

        def DIVIDE(self):
            return self.getToken(ProofParser.DIVIDE, 0)

        def PLUS(self):
            return self.getToken(ProofParser.PLUS, 0)

        def SUBTRACT(self):
            return self.getToken(ProofParser.SUBTRACT, 0)

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
        _startState = 66
        self.enterRecursionRule(localctx, 66, self.RULE_integerExpression, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 651
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [61, 70, 79]:
                self.state = 644
                self.lvalue()
                pass
            elif token in [78]:
                self.state = 645
                self.match(ProofParser.INT)
                pass
            elif token in [75]:
                self.state = 646
                self.match(ProofParser.BINARYNUM)
                pass
            elif token in [19]:
                self.state = 647
                self.match(ProofParser.L_PAREN)
                self.state = 648
                self.integerExpression(0)
                self.state = 649
                self.match(ProofParser.R_PAREN)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 667
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,52,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 665
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,51,self._ctx)
                    if la_ == 1:
                        localctx = ProofParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 653
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 8)")
                        self.state = 654
                        self.match(ProofParser.TIMES)
                        self.state = 655
                        self.integerExpression(9)
                        pass

                    elif la_ == 2:
                        localctx = ProofParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 656
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 7)")
                        self.state = 657
                        self.match(ProofParser.DIVIDE)
                        self.state = 658
                        self.integerExpression(8)
                        pass

                    elif la_ == 3:
                        localctx = ProofParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 659
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 6)")
                        self.state = 660
                        self.match(ProofParser.PLUS)
                        self.state = 661
                        self.integerExpression(7)
                        pass

                    elif la_ == 4:
                        localctx = ProofParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 662
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 5)")
                        self.state = 663
                        self.match(ProofParser.SUBTRACT)
                        self.state = 664
                        self.integerExpression(6)
                        pass

             
                self.state = 669
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,52,self._ctx)

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
            return self.getTypedRuleContext(ProofParser.LvalueContext,0)


        def INT(self):
            return self.getToken(ProofParser.INT, 0)

        def L_PAREN(self):
            return self.getToken(ProofParser.L_PAREN, 0)

        def integerExpression(self):
            return self.getTypedRuleContext(ProofParser.IntegerExpressionContext,0)


        def R_PAREN(self):
            return self.getToken(ProofParser.R_PAREN, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_integerAtom

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIntegerAtom" ):
                return visitor.visitIntegerAtom(self)
            else:
                return visitor.visitChildren(self)




    def integerAtom(self):

        localctx = ProofParser.IntegerAtomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 68, self.RULE_integerAtom)
        try:
            self.state = 676
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [61, 70, 79]:
                self.enterOuterAlt(localctx, 1)
                self.state = 670
                self.lvalue()
                pass
            elif token in [78]:
                self.enterOuterAlt(localctx, 2)
                self.state = 671
                self.match(ProofParser.INT)
                pass
            elif token in [19]:
                self.enterOuterAlt(localctx, 3)
                self.state = 672
                self.match(ProofParser.L_PAREN)
                self.state = 673
                self.integerExpression(0)
                self.state = 674
                self.match(ProofParser.R_PAREN)
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
        self.enterRule(localctx, 70, self.RULE_bitstring)
        try:
            self.state = 684
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,54,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 678
                self.match(ProofParser.BITSTRING)
                self.state = 679
                self.match(ProofParser.L_ANGLE)
                self.state = 680
                self.integerExpression(0)
                self.state = 681
                self.match(ProofParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 683
                self.match(ProofParser.BITSTRING)
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
            return self.getToken(ProofParser.MODINT, 0)

        def L_ANGLE(self):
            return self.getToken(ProofParser.L_ANGLE, 0)

        def integerExpression(self):
            return self.getTypedRuleContext(ProofParser.IntegerExpressionContext,0)


        def R_ANGLE(self):
            return self.getToken(ProofParser.R_ANGLE, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_modint

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitModint" ):
                return visitor.visitModint(self)
            else:
                return visitor.visitChildren(self)




    def modint(self):

        localctx = ProofParser.ModintContext(self, self._ctx, self.state)
        self.enterRule(localctx, 72, self.RULE_modint)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 686
            self.match(ProofParser.MODINT)
            self.state = 687
            self.match(ProofParser.L_ANGLE)
            self.state = 688
            self.integerExpression(0)
            self.state = 689
            self.match(ProofParser.R_ANGLE)
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
        self.enterRule(localctx, 74, self.RULE_set)
        try:
            self.state = 697
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,55,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 691
                self.match(ProofParser.SET)
                self.state = 692
                self.match(ProofParser.L_ANGLE)
                self.state = 693
                self.type_(0)
                self.state = 694
                self.match(ProofParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 696
                self.match(ProofParser.SET)
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
            return self.getToken(ProofParser.TRUE, 0)

        def FALSE(self):
            return self.getToken(ProofParser.FALSE, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_bool

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBool" ):
                return visitor.visitBool(self)
            else:
                return visitor.visitChildren(self)




    def bool_(self):

        localctx = ProofParser.BoolContext(self, self._ctx, self.state)
        self.enterRule(localctx, 76, self.RULE_bool)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 699
            _la = self._input.LA(1)
            if not(_la==73 or _la==74):
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
        self.enterRule(localctx, 78, self.RULE_moduleImport)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 701
            self.match(ProofParser.IMPORT)
            self.state = 702
            self.match(ProofParser.FILESTRING)
            self.state = 705
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==65:
                self.state = 703
                self.match(ProofParser.AS)
                self.state = 704
                self.match(ProofParser.ID)


            self.state = 707
            self.match(ProofParser.SEMI)
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
        self.enterRule(localctx, 80, self.RULE_id)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 709
            _la = self._input.LA(1)
            if not(_la==61 or _la==79):
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
        self._predicates[28] = self.expression_sempred
        self._predicates[32] = self.type_sempred
        self._predicates[33] = self.integerExpression_sempred
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
         




