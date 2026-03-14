# Generated from proof_frog/antlr/Scheme.g4 by ANTLR 4.13.2
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
        4,1,66,539,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        1,0,5,0,56,8,0,10,0,12,0,59,9,0,1,0,1,0,1,0,1,1,1,1,1,1,1,1,3,1,
        68,8,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,1,2,1,2,1,2,5,2,81,8,2,10,
        2,12,2,84,9,2,1,2,1,2,1,2,1,2,4,2,90,8,2,11,2,12,2,91,1,3,1,3,1,
        3,1,3,3,3,98,8,3,1,3,1,3,1,3,1,3,1,3,1,4,1,4,1,4,5,4,108,8,4,10,
        4,12,4,111,9,4,1,4,4,4,114,8,4,11,4,12,4,115,1,4,1,4,1,4,5,4,121,
        8,4,10,4,12,4,124,9,4,1,4,5,4,127,8,4,10,4,12,4,130,9,4,1,4,4,4,
        133,8,4,11,4,12,4,134,3,4,137,8,4,1,5,1,5,1,5,4,5,142,8,5,11,5,12,
        5,143,1,5,1,5,1,5,1,5,1,5,1,5,5,5,152,8,5,10,5,12,5,155,9,5,1,5,
        1,5,1,5,1,5,1,6,1,6,1,6,3,6,164,8,6,1,7,1,7,1,7,1,7,1,8,1,8,1,8,
        1,9,1,9,5,9,175,8,9,10,9,12,9,178,9,9,1,9,1,9,1,10,1,10,1,10,1,10,
        1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,
        1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,3,10,
        211,8,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,
        1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,5,10,232,8,10,10,10,12,10,
        235,9,10,1,10,1,10,3,10,239,8,10,1,10,1,10,1,10,1,10,1,10,1,10,1,
        10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,10,1,
        10,3,10,261,8,10,1,11,1,11,3,11,265,8,11,1,11,1,11,1,11,1,11,1,11,
        1,11,5,11,273,8,11,10,11,12,11,276,9,11,1,12,1,12,1,12,1,12,3,12,
        282,8,12,1,12,1,12,1,13,1,13,1,13,5,13,289,8,13,10,13,12,13,292,
        9,13,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,5,14,308,8,14,10,14,12,14,311,9,14,3,14,313,8,14,1,14,
        1,14,1,14,1,14,1,14,5,14,320,8,14,10,14,12,14,323,9,14,3,14,325,
        8,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,3,14,341,8,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,3,14,397,8,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,5,14,407,8,14,10,14,12,14,410,9,14,1,15,
        1,15,1,15,5,15,415,8,15,10,15,12,15,418,9,15,1,16,1,16,1,16,1,17,
        1,17,1,17,3,17,426,8,17,1,17,1,17,1,18,1,18,1,18,1,18,1,18,1,18,
        1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,
        1,18,1,18,1,18,1,18,4,18,453,8,18,11,18,12,18,454,1,18,1,18,1,18,
        1,18,1,18,3,18,462,8,18,1,18,1,18,5,18,466,8,18,10,18,12,18,469,
        9,18,1,19,1,19,1,19,1,19,1,19,1,19,1,19,1,19,3,19,479,8,19,1,19,
        1,19,1,19,1,19,1,19,1,19,1,19,1,19,1,19,1,19,1,19,1,19,5,19,493,
        8,19,10,19,12,19,496,9,19,1,20,1,20,1,20,1,20,1,20,1,20,3,20,504,
        8,20,1,21,1,21,1,21,1,21,1,21,1,21,3,21,512,8,21,1,22,1,22,1,22,
        1,22,1,22,1,23,1,23,1,23,1,23,1,23,1,23,3,23,525,8,23,1,24,1,24,
        1,25,1,25,1,25,1,25,3,25,533,8,25,1,25,1,25,1,26,1,26,1,26,0,3,28,
        36,38,27,0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,
        40,42,44,46,48,50,52,0,2,1,0,57,58,2,0,48,48,63,63,606,0,57,1,0,
        0,0,2,63,1,0,0,0,4,82,1,0,0,0,6,93,1,0,0,0,8,136,1,0,0,0,10,138,
        1,0,0,0,12,160,1,0,0,0,14,165,1,0,0,0,16,169,1,0,0,0,18,172,1,0,
        0,0,20,260,1,0,0,0,22,264,1,0,0,0,24,277,1,0,0,0,26,285,1,0,0,0,
        28,340,1,0,0,0,30,411,1,0,0,0,32,419,1,0,0,0,34,422,1,0,0,0,36,461,
        1,0,0,0,38,478,1,0,0,0,40,503,1,0,0,0,42,511,1,0,0,0,44,513,1,0,
        0,0,46,524,1,0,0,0,48,526,1,0,0,0,50,528,1,0,0,0,52,536,1,0,0,0,
        54,56,3,50,25,0,55,54,1,0,0,0,56,59,1,0,0,0,57,55,1,0,0,0,57,58,
        1,0,0,0,58,60,1,0,0,0,59,57,1,0,0,0,60,61,3,2,1,0,61,62,5,0,0,1,
        62,1,1,0,0,0,63,64,5,2,0,0,64,65,5,63,0,0,65,67,5,8,0,0,66,68,3,
        26,13,0,67,66,1,0,0,0,67,68,1,0,0,0,68,69,1,0,0,0,69,70,5,9,0,0,
        70,71,5,3,0,0,71,72,5,63,0,0,72,73,5,4,0,0,73,74,3,4,2,0,74,75,5,
        5,0,0,75,3,1,0,0,0,76,77,5,1,0,0,77,78,3,28,14,0,78,79,5,12,0,0,
        79,81,1,0,0,0,80,76,1,0,0,0,81,84,1,0,0,0,82,80,1,0,0,0,82,83,1,
        0,0,0,83,89,1,0,0,0,84,82,1,0,0,0,85,86,3,12,6,0,86,87,5,12,0,0,
        87,90,1,0,0,0,88,90,3,16,8,0,89,85,1,0,0,0,89,88,1,0,0,0,90,91,1,
        0,0,0,91,89,1,0,0,0,91,92,1,0,0,0,92,5,1,0,0,0,93,94,5,50,0,0,94,
        95,5,63,0,0,95,97,5,8,0,0,96,98,3,26,13,0,97,96,1,0,0,0,97,98,1,
        0,0,0,98,99,1,0,0,0,99,100,5,9,0,0,100,101,5,4,0,0,101,102,3,8,4,
        0,102,103,5,5,0,0,103,7,1,0,0,0,104,105,3,12,6,0,105,106,5,12,0,
        0,106,108,1,0,0,0,107,104,1,0,0,0,108,111,1,0,0,0,109,107,1,0,0,
        0,109,110,1,0,0,0,110,113,1,0,0,0,111,109,1,0,0,0,112,114,3,16,8,
        0,113,112,1,0,0,0,114,115,1,0,0,0,115,113,1,0,0,0,115,116,1,0,0,
        0,116,137,1,0,0,0,117,118,3,12,6,0,118,119,5,12,0,0,119,121,1,0,
        0,0,120,117,1,0,0,0,121,124,1,0,0,0,122,120,1,0,0,0,122,123,1,0,
        0,0,123,128,1,0,0,0,124,122,1,0,0,0,125,127,3,16,8,0,126,125,1,0,
        0,0,127,130,1,0,0,0,128,126,1,0,0,0,128,129,1,0,0,0,129,132,1,0,
        0,0,130,128,1,0,0,0,131,133,3,10,5,0,132,131,1,0,0,0,133,134,1,0,
        0,0,134,132,1,0,0,0,134,135,1,0,0,0,135,137,1,0,0,0,136,109,1,0,
        0,0,136,122,1,0,0,0,137,9,1,0,0,0,138,139,5,53,0,0,139,141,5,4,0,
        0,140,142,3,16,8,0,141,140,1,0,0,0,142,143,1,0,0,0,143,141,1,0,0,
        0,143,144,1,0,0,0,144,145,1,0,0,0,145,146,5,54,0,0,146,147,5,13,
        0,0,147,148,5,6,0,0,148,153,3,52,26,0,149,150,5,14,0,0,150,152,3,
        52,26,0,151,149,1,0,0,0,152,155,1,0,0,0,153,151,1,0,0,0,153,154,
        1,0,0,0,154,156,1,0,0,0,155,153,1,0,0,0,156,157,5,7,0,0,157,158,
        5,12,0,0,158,159,5,5,0,0,159,11,1,0,0,0,160,163,3,32,16,0,161,162,
        5,17,0,0,162,164,3,28,14,0,163,161,1,0,0,0,163,164,1,0,0,0,164,13,
        1,0,0,0,165,166,3,32,16,0,166,167,5,17,0,0,167,168,3,28,14,0,168,
        15,1,0,0,0,169,170,3,24,12,0,170,171,3,18,9,0,171,17,1,0,0,0,172,
        176,5,4,0,0,173,175,3,20,10,0,174,173,1,0,0,0,175,178,1,0,0,0,176,
        174,1,0,0,0,176,177,1,0,0,0,177,179,1,0,0,0,178,176,1,0,0,0,179,
        180,5,5,0,0,180,19,1,0,0,0,181,182,3,36,18,0,182,183,3,52,26,0,183,
        184,5,12,0,0,184,261,1,0,0,0,185,186,3,36,18,0,186,187,3,22,11,0,
        187,188,5,17,0,0,188,189,3,28,14,0,189,190,5,12,0,0,190,261,1,0,
        0,0,191,192,3,36,18,0,192,193,3,22,11,0,193,194,5,27,0,0,194,195,
        3,28,14,0,195,196,5,12,0,0,196,261,1,0,0,0,197,198,3,22,11,0,198,
        199,5,17,0,0,199,200,3,28,14,0,200,201,5,12,0,0,201,261,1,0,0,0,
        202,203,3,22,11,0,203,204,5,27,0,0,204,205,3,28,14,0,205,206,5,12,
        0,0,206,261,1,0,0,0,207,208,3,28,14,0,208,210,5,8,0,0,209,211,3,
        30,15,0,210,209,1,0,0,0,210,211,1,0,0,0,211,212,1,0,0,0,212,213,
        5,9,0,0,213,214,5,12,0,0,214,261,1,0,0,0,215,216,5,38,0,0,216,217,
        3,28,14,0,217,218,5,12,0,0,218,261,1,0,0,0,219,220,5,45,0,0,220,
        221,5,8,0,0,221,222,3,28,14,0,222,223,5,9,0,0,223,233,3,18,9,0,224,
        225,5,55,0,0,225,226,5,45,0,0,226,227,5,8,0,0,227,228,3,28,14,0,
        228,229,5,9,0,0,229,230,3,18,9,0,230,232,1,0,0,0,231,224,1,0,0,0,
        232,235,1,0,0,0,233,231,1,0,0,0,233,234,1,0,0,0,234,238,1,0,0,0,
        235,233,1,0,0,0,236,237,5,55,0,0,237,239,3,18,9,0,238,236,1,0,0,
        0,238,239,1,0,0,0,239,261,1,0,0,0,240,241,5,46,0,0,241,242,5,8,0,
        0,242,243,5,36,0,0,243,244,3,52,26,0,244,245,5,17,0,0,245,246,3,
        28,14,0,246,247,5,47,0,0,247,248,3,28,14,0,248,249,5,9,0,0,249,250,
        3,18,9,0,250,261,1,0,0,0,251,252,5,46,0,0,252,253,5,8,0,0,253,254,
        3,36,18,0,254,255,3,52,26,0,255,256,5,48,0,0,256,257,3,28,14,0,257,
        258,5,9,0,0,258,259,3,18,9,0,259,261,1,0,0,0,260,181,1,0,0,0,260,
        185,1,0,0,0,260,191,1,0,0,0,260,197,1,0,0,0,260,202,1,0,0,0,260,
        207,1,0,0,0,260,215,1,0,0,0,260,219,1,0,0,0,260,240,1,0,0,0,260,
        251,1,0,0,0,261,21,1,0,0,0,262,265,3,52,26,0,263,265,3,34,17,0,264,
        262,1,0,0,0,264,263,1,0,0,0,265,274,1,0,0,0,266,267,5,15,0,0,267,
        273,3,52,26,0,268,269,5,6,0,0,269,270,3,28,14,0,270,271,5,7,0,0,
        271,273,1,0,0,0,272,266,1,0,0,0,272,268,1,0,0,0,273,276,1,0,0,0,
        274,272,1,0,0,0,274,275,1,0,0,0,275,23,1,0,0,0,276,274,1,0,0,0,277,
        278,3,36,18,0,278,279,3,52,26,0,279,281,5,8,0,0,280,282,3,26,13,
        0,281,280,1,0,0,0,281,282,1,0,0,0,282,283,1,0,0,0,283,284,5,9,0,
        0,284,25,1,0,0,0,285,290,3,32,16,0,286,287,5,14,0,0,287,289,3,32,
        16,0,288,286,1,0,0,0,289,292,1,0,0,0,290,288,1,0,0,0,290,291,1,0,
        0,0,291,27,1,0,0,0,292,290,1,0,0,0,293,294,6,14,-1,0,294,295,5,30,
        0,0,295,341,3,28,14,31,296,297,5,32,0,0,297,298,3,28,14,0,298,299,
        5,32,0,0,299,341,1,0,0,0,300,301,5,19,0,0,301,341,3,28,14,26,302,
        341,3,22,11,0,303,312,5,6,0,0,304,309,3,28,14,0,305,306,5,14,0,0,
        306,308,3,28,14,0,307,305,1,0,0,0,308,311,1,0,0,0,309,307,1,0,0,
        0,309,310,1,0,0,0,310,313,1,0,0,0,311,309,1,0,0,0,312,304,1,0,0,
        0,312,313,1,0,0,0,313,314,1,0,0,0,314,341,5,7,0,0,315,324,5,4,0,
        0,316,321,3,28,14,0,317,318,5,14,0,0,318,320,3,28,14,0,319,317,1,
        0,0,0,320,323,1,0,0,0,321,319,1,0,0,0,321,322,1,0,0,0,322,325,1,
        0,0,0,323,321,1,0,0,0,324,316,1,0,0,0,324,325,1,0,0,0,325,326,1,
        0,0,0,326,341,5,5,0,0,327,341,3,36,18,0,328,329,5,60,0,0,329,341,
        3,40,20,0,330,331,5,61,0,0,331,341,3,40,20,0,332,341,5,59,0,0,333,
        341,5,62,0,0,334,341,3,48,24,0,335,341,5,56,0,0,336,337,5,8,0,0,
        337,338,3,28,14,0,338,339,5,9,0,0,339,341,1,0,0,0,340,293,1,0,0,
        0,340,296,1,0,0,0,340,300,1,0,0,0,340,302,1,0,0,0,340,303,1,0,0,
        0,340,315,1,0,0,0,340,327,1,0,0,0,340,328,1,0,0,0,340,330,1,0,0,
        0,340,332,1,0,0,0,340,333,1,0,0,0,340,334,1,0,0,0,340,335,1,0,0,
        0,340,336,1,0,0,0,341,408,1,0,0,0,342,343,10,29,0,0,343,344,5,31,
        0,0,344,407,3,28,14,29,345,346,10,28,0,0,346,347,5,16,0,0,347,407,
        3,28,14,29,348,349,10,27,0,0,349,350,5,20,0,0,350,407,3,28,14,28,
        351,352,10,25,0,0,352,353,5,18,0,0,353,407,3,28,14,26,354,355,10,
        24,0,0,355,356,5,19,0,0,356,407,3,28,14,25,357,358,10,23,0,0,358,
        359,5,22,0,0,359,407,3,28,14,24,360,361,10,22,0,0,361,362,5,23,0,
        0,362,407,3,28,14,23,363,364,10,21,0,0,364,365,5,11,0,0,365,407,
        3,28,14,22,366,367,10,20,0,0,367,368,5,10,0,0,368,407,3,28,14,21,
        369,370,10,19,0,0,370,371,5,24,0,0,371,407,3,28,14,20,372,373,10,
        18,0,0,373,374,5,25,0,0,374,407,3,28,14,19,375,376,10,17,0,0,376,
        377,5,48,0,0,377,407,3,28,14,18,378,379,10,16,0,0,379,380,5,44,0,
        0,380,407,3,28,14,17,381,382,10,15,0,0,382,383,5,28,0,0,383,407,
        3,28,14,16,384,385,10,14,0,0,385,386,5,26,0,0,386,407,3,28,14,15,
        387,388,10,13,0,0,388,389,5,49,0,0,389,407,3,28,14,14,390,391,10,
        12,0,0,391,392,5,29,0,0,392,407,3,28,14,13,393,394,10,33,0,0,394,
        396,5,8,0,0,395,397,3,30,15,0,396,395,1,0,0,0,396,397,1,0,0,0,397,
        398,1,0,0,0,398,407,5,9,0,0,399,400,10,32,0,0,400,401,5,6,0,0,401,
        402,3,38,19,0,402,403,5,13,0,0,403,404,3,38,19,0,404,405,5,7,0,0,
        405,407,1,0,0,0,406,342,1,0,0,0,406,345,1,0,0,0,406,348,1,0,0,0,
        406,351,1,0,0,0,406,354,1,0,0,0,406,357,1,0,0,0,406,360,1,0,0,0,
        406,363,1,0,0,0,406,366,1,0,0,0,406,369,1,0,0,0,406,372,1,0,0,0,
        406,375,1,0,0,0,406,378,1,0,0,0,406,381,1,0,0,0,406,384,1,0,0,0,
        406,387,1,0,0,0,406,390,1,0,0,0,406,393,1,0,0,0,406,399,1,0,0,0,
        407,410,1,0,0,0,408,406,1,0,0,0,408,409,1,0,0,0,409,29,1,0,0,0,410,
        408,1,0,0,0,411,416,3,28,14,0,412,413,5,14,0,0,413,415,3,28,14,0,
        414,412,1,0,0,0,415,418,1,0,0,0,416,414,1,0,0,0,416,417,1,0,0,0,
        417,31,1,0,0,0,418,416,1,0,0,0,419,420,3,36,18,0,420,421,3,52,26,
        0,421,33,1,0,0,0,422,423,5,63,0,0,423,425,5,8,0,0,424,426,3,30,15,
        0,425,424,1,0,0,0,425,426,1,0,0,0,426,427,1,0,0,0,427,428,5,9,0,
        0,428,35,1,0,0,0,429,430,6,18,-1,0,430,462,3,46,23,0,431,462,5,34,
        0,0,432,462,5,35,0,0,433,434,5,37,0,0,434,435,5,10,0,0,435,436,3,
        36,18,0,436,437,5,14,0,0,437,438,3,36,18,0,438,439,5,11,0,0,439,
        462,1,0,0,0,440,441,5,42,0,0,441,442,5,10,0,0,442,443,3,36,18,0,
        443,444,5,14,0,0,444,445,3,38,19,0,445,446,5,11,0,0,446,462,1,0,
        0,0,447,462,5,36,0,0,448,449,5,6,0,0,449,452,3,36,18,0,450,451,5,
        14,0,0,451,453,3,36,18,0,452,450,1,0,0,0,453,454,1,0,0,0,454,452,
        1,0,0,0,454,455,1,0,0,0,455,456,1,0,0,0,456,457,5,7,0,0,457,462,
        1,0,0,0,458,462,3,42,21,0,459,462,3,44,22,0,460,462,3,22,11,0,461,
        429,1,0,0,0,461,431,1,0,0,0,461,432,1,0,0,0,461,433,1,0,0,0,461,
        440,1,0,0,0,461,447,1,0,0,0,461,448,1,0,0,0,461,458,1,0,0,0,461,
        459,1,0,0,0,461,460,1,0,0,0,462,467,1,0,0,0,463,464,10,11,0,0,464,
        466,5,21,0,0,465,463,1,0,0,0,466,469,1,0,0,0,467,465,1,0,0,0,467,
        468,1,0,0,0,468,37,1,0,0,0,469,467,1,0,0,0,470,471,6,19,-1,0,471,
        479,3,22,11,0,472,479,5,62,0,0,473,479,5,59,0,0,474,475,5,8,0,0,
        475,476,3,38,19,0,476,477,5,9,0,0,477,479,1,0,0,0,478,470,1,0,0,
        0,478,472,1,0,0,0,478,473,1,0,0,0,478,474,1,0,0,0,479,494,1,0,0,
        0,480,481,10,8,0,0,481,482,5,16,0,0,482,493,3,38,19,9,483,484,10,
        7,0,0,484,485,5,20,0,0,485,493,3,38,19,8,486,487,10,6,0,0,487,488,
        5,18,0,0,488,493,3,38,19,7,489,490,10,5,0,0,490,491,5,19,0,0,491,
        493,3,38,19,6,492,480,1,0,0,0,492,483,1,0,0,0,492,486,1,0,0,0,492,
        489,1,0,0,0,493,496,1,0,0,0,494,492,1,0,0,0,494,495,1,0,0,0,495,
        39,1,0,0,0,496,494,1,0,0,0,497,504,3,22,11,0,498,504,5,62,0,0,499,
        500,5,8,0,0,500,501,3,38,19,0,501,502,5,9,0,0,502,504,1,0,0,0,503,
        497,1,0,0,0,503,498,1,0,0,0,503,499,1,0,0,0,504,41,1,0,0,0,505,506,
        5,40,0,0,506,507,5,10,0,0,507,508,3,38,19,0,508,509,5,11,0,0,509,
        512,1,0,0,0,510,512,5,40,0,0,511,505,1,0,0,0,511,510,1,0,0,0,512,
        43,1,0,0,0,513,514,5,41,0,0,514,515,5,10,0,0,515,516,3,38,19,0,516,
        517,5,11,0,0,517,45,1,0,0,0,518,519,5,33,0,0,519,520,5,10,0,0,520,
        521,3,36,18,0,521,522,5,11,0,0,522,525,1,0,0,0,523,525,5,33,0,0,
        524,518,1,0,0,0,524,523,1,0,0,0,525,47,1,0,0,0,526,527,7,0,0,0,527,
        49,1,0,0,0,528,529,5,39,0,0,529,532,5,66,0,0,530,531,5,52,0,0,531,
        533,5,63,0,0,532,530,1,0,0,0,532,533,1,0,0,0,533,534,1,0,0,0,534,
        535,5,12,0,0,535,51,1,0,0,0,536,537,7,1,0,0,537,53,1,0,0,0,45,57,
        67,82,89,91,97,109,115,122,128,134,136,143,153,163,176,210,233,238,
        260,264,272,274,281,290,309,312,321,324,340,396,406,408,416,425,
        454,461,467,478,492,494,503,511,524,532
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
                     "'<-'", "'&&'", "'\\'", "'!'", "'^'", "'|'", "'Set'", 
                     "'Bool'", "'Void'", "'Int'", "'Map'", "'return'", "'import'", 
                     "'BitString'", "'ModInt'", "'Array'", "'Primitive'", 
                     "'subsets'", "'if'", "'for'", "'to'", "'in'", "'union'", 
                     "'Game'", "'export'", "'as'", "'Phase'", "'oracles'", 
                     "'else'", "'None'", "'true'", "'false'", "<INVALID>", 
                     "'0^'", "'1^'" ]

    symbolicNames = [ "<INVALID>", "REQUIRES", "SCHEME", "EXTENDS", "L_CURLY", 
                      "R_CURLY", "L_SQUARE", "R_SQUARE", "L_PAREN", "R_PAREN", 
                      "L_ANGLE", "R_ANGLE", "SEMI", "COLON", "COMMA", "PERIOD", 
                      "TIMES", "EQUALS", "PLUS", "SUBTRACT", "DIVIDE", "QUESTION", 
                      "EQUALSCOMPARE", "NOTEQUALS", "GEQ", "LEQ", "OR", 
                      "SAMPLES", "AND", "BACKSLASH", "NOT", "CARET", "VBAR", 
                      "SET", "BOOL", "VOID", "INTTYPE", "MAP", "RETURN", 
                      "IMPORT", "BITSTRING", "MODINT", "ARRAY", "PRIMITIVE", 
                      "SUBSETS", "IF", "FOR", "TO", "IN", "UNION", "GAME", 
                      "EXPORT", "AS", "PHASE", "ORACLES", "ELSE", "NONE", 
                      "TRUE", "FALSE", "BINARYNUM", "ZEROS_CARET", "ONES_CARET", 
                      "INT", "ID", "WS", "LINE_COMMENT", "FILESTRING" ]

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

    ruleNames =  [ "program", "scheme", "schemeBody", "game", "gameBody", 
                   "gamePhase", "field", "initializedField", "method", "block", 
                   "statement", "lvalue", "methodSignature", "paramList", 
                   "expression", "argList", "variable", "parameterizedGame", 
                   "type", "integerExpression", "integerAtom", "bitstring", 
                   "modint", "set", "bool", "moduleImport", "id" ]

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
    CARET=31
    VBAR=32
    SET=33
    BOOL=34
    VOID=35
    INTTYPE=36
    MAP=37
    RETURN=38
    IMPORT=39
    BITSTRING=40
    MODINT=41
    ARRAY=42
    PRIMITIVE=43
    SUBSETS=44
    IF=45
    FOR=46
    TO=47
    IN=48
    UNION=49
    GAME=50
    EXPORT=51
    AS=52
    PHASE=53
    ORACLES=54
    ELSE=55
    NONE=56
    TRUE=57
    FALSE=58
    BINARYNUM=59
    ZEROS_CARET=60
    ONES_CARET=61
    INT=62
    ID=63
    WS=64
    LINE_COMMENT=65
    FILESTRING=66

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
            self.state = 57
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==39:
                self.state = 54
                self.moduleImport()
                self.state = 59
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 60
            self.scheme()
            self.state = 61
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
            self.state = 63
            self.match(SchemeParser.SCHEME)
            self.state = 64
            self.match(SchemeParser.ID)
            self.state = 65
            self.match(SchemeParser.L_PAREN)
            self.state = 67
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & -9223082599008698304) != 0):
                self.state = 66
                self.paramList()


            self.state = 69
            self.match(SchemeParser.R_PAREN)
            self.state = 70
            self.match(SchemeParser.EXTENDS)
            self.state = 71
            self.match(SchemeParser.ID)
            self.state = 72
            self.match(SchemeParser.L_CURLY)
            self.state = 73
            self.schemeBody()
            self.state = 74
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
            self.state = 82
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==1:
                self.state = 76
                self.match(SchemeParser.REQUIRES)
                self.state = 77
                self.expression(0)
                self.state = 78
                self.match(SchemeParser.SEMI)
                self.state = 84
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 89 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 89
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input,3,self._ctx)
                if la_ == 1:
                    self.state = 85
                    self.field()
                    self.state = 86
                    self.match(SchemeParser.SEMI)
                    pass

                elif la_ == 2:
                    self.state = 88
                    self.method()
                    pass


                self.state = 91 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & -9223082599008698304) != 0)):
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
            self.state = 93
            self.match(SchemeParser.GAME)
            self.state = 94
            self.match(SchemeParser.ID)
            self.state = 95
            self.match(SchemeParser.L_PAREN)
            self.state = 97
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & -9223082599008698304) != 0):
                self.state = 96
                self.paramList()


            self.state = 99
            self.match(SchemeParser.R_PAREN)
            self.state = 100
            self.match(SchemeParser.L_CURLY)
            self.state = 101
            self.gameBody()
            self.state = 102
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
            self.state = 136
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,11,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 109
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,6,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 104
                        self.field()
                        self.state = 105
                        self.match(SchemeParser.SEMI) 
                    self.state = 111
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,6,self._ctx)

                self.state = 113 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 112
                    self.method()
                    self.state = 115 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & -9223082599008698304) != 0)):
                        break

                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 122
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,8,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 117
                        self.field()
                        self.state = 118
                        self.match(SchemeParser.SEMI) 
                    self.state = 124
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,8,self._ctx)

                self.state = 128
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while (((_la) & ~0x3f) == 0 and ((1 << _la) & -9223082599008698304) != 0):
                    self.state = 125
                    self.method()
                    self.state = 130
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 132 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 131
                    self.gamePhase()
                    self.state = 134 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==53):
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
            self.state = 138
            self.match(SchemeParser.PHASE)
            self.state = 139
            self.match(SchemeParser.L_CURLY)
            self.state = 141 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 140
                self.method()
                self.state = 143 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & -9223082599008698304) != 0)):
                    break

            self.state = 145
            self.match(SchemeParser.ORACLES)
            self.state = 146
            self.match(SchemeParser.COLON)
            self.state = 147
            self.match(SchemeParser.L_SQUARE)
            self.state = 148
            self.id_()
            self.state = 153
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==14:
                self.state = 149
                self.match(SchemeParser.COMMA)
                self.state = 150
                self.id_()
                self.state = 155
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 156
            self.match(SchemeParser.R_SQUARE)
            self.state = 157
            self.match(SchemeParser.SEMI)
            self.state = 158
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
            self.state = 160
            self.variable()
            self.state = 163
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==17:
                self.state = 161
                self.match(SchemeParser.EQUALS)
                self.state = 162
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
            self.state = 165
            self.variable()
            self.state = 166
            self.match(SchemeParser.EQUALS)
            self.state = 167
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
            self.state = 169
            self.methodSignature()
            self.state = 170
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
            self.state = 172
            self.match(SchemeParser.L_CURLY)
            self.state = 176
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & -71662322828443312) != 0):
                self.state = 173
                self.statement()
                self.state = 178
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 179
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
            self.state = 260
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,19,self._ctx)
            if la_ == 1:
                localctx = SchemeParser.VarDeclStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 181
                self.type_(0)
                self.state = 182
                self.id_()
                self.state = 183
                self.match(SchemeParser.SEMI)
                pass

            elif la_ == 2:
                localctx = SchemeParser.VarDeclWithValueStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 185
                self.type_(0)
                self.state = 186
                self.lvalue()
                self.state = 187
                self.match(SchemeParser.EQUALS)
                self.state = 188
                self.expression(0)
                self.state = 189
                self.match(SchemeParser.SEMI)
                pass

            elif la_ == 3:
                localctx = SchemeParser.VarDeclWithSampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 191
                self.type_(0)
                self.state = 192
                self.lvalue()
                self.state = 193
                self.match(SchemeParser.SAMPLES)
                self.state = 194
                self.expression(0)
                self.state = 195
                self.match(SchemeParser.SEMI)
                pass

            elif la_ == 4:
                localctx = SchemeParser.AssignmentStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 197
                self.lvalue()
                self.state = 198
                self.match(SchemeParser.EQUALS)
                self.state = 199
                self.expression(0)
                self.state = 200
                self.match(SchemeParser.SEMI)
                pass

            elif la_ == 5:
                localctx = SchemeParser.SampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 5)
                self.state = 202
                self.lvalue()
                self.state = 203
                self.match(SchemeParser.SAMPLES)
                self.state = 204
                self.expression(0)
                self.state = 205
                self.match(SchemeParser.SEMI)
                pass

            elif la_ == 6:
                localctx = SchemeParser.FunctionCallStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 6)
                self.state = 207
                self.expression(0)
                self.state = 208
                self.match(SchemeParser.L_PAREN)
                self.state = 210
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & -71768150822616752) != 0):
                    self.state = 209
                    self.argList()


                self.state = 212
                self.match(SchemeParser.R_PAREN)
                self.state = 213
                self.match(SchemeParser.SEMI)
                pass

            elif la_ == 7:
                localctx = SchemeParser.ReturnStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 7)
                self.state = 215
                self.match(SchemeParser.RETURN)
                self.state = 216
                self.expression(0)
                self.state = 217
                self.match(SchemeParser.SEMI)
                pass

            elif la_ == 8:
                localctx = SchemeParser.IfStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 8)
                self.state = 219
                self.match(SchemeParser.IF)
                self.state = 220
                self.match(SchemeParser.L_PAREN)
                self.state = 221
                self.expression(0)
                self.state = 222
                self.match(SchemeParser.R_PAREN)
                self.state = 223
                self.block()
                self.state = 233
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,17,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 224
                        self.match(SchemeParser.ELSE)
                        self.state = 225
                        self.match(SchemeParser.IF)
                        self.state = 226
                        self.match(SchemeParser.L_PAREN)
                        self.state = 227
                        self.expression(0)
                        self.state = 228
                        self.match(SchemeParser.R_PAREN)
                        self.state = 229
                        self.block() 
                    self.state = 235
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,17,self._ctx)

                self.state = 238
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==55:
                    self.state = 236
                    self.match(SchemeParser.ELSE)
                    self.state = 237
                    self.block()


                pass

            elif la_ == 9:
                localctx = SchemeParser.NumericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 9)
                self.state = 240
                self.match(SchemeParser.FOR)
                self.state = 241
                self.match(SchemeParser.L_PAREN)
                self.state = 242
                self.match(SchemeParser.INTTYPE)
                self.state = 243
                self.id_()
                self.state = 244
                self.match(SchemeParser.EQUALS)
                self.state = 245
                self.expression(0)
                self.state = 246
                self.match(SchemeParser.TO)
                self.state = 247
                self.expression(0)
                self.state = 248
                self.match(SchemeParser.R_PAREN)
                self.state = 249
                self.block()
                pass

            elif la_ == 10:
                localctx = SchemeParser.GenericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 10)
                self.state = 251
                self.match(SchemeParser.FOR)
                self.state = 252
                self.match(SchemeParser.L_PAREN)
                self.state = 253
                self.type_(0)
                self.state = 254
                self.id_()
                self.state = 255
                self.match(SchemeParser.IN)
                self.state = 256
                self.expression(0)
                self.state = 257
                self.match(SchemeParser.R_PAREN)
                self.state = 258
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

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)


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
            self.state = 264
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,20,self._ctx)
            if la_ == 1:
                self.state = 262
                self.id_()
                pass

            elif la_ == 2:
                self.state = 263
                self.parameterizedGame()
                pass


            self.state = 274
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,22,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 272
                    self._errHandler.sync(self)
                    token = self._input.LA(1)
                    if token in [15]:
                        self.state = 266
                        self.match(SchemeParser.PERIOD)
                        self.state = 267
                        self.id_()
                        pass
                    elif token in [6]:
                        self.state = 268
                        self.match(SchemeParser.L_SQUARE)
                        self.state = 269
                        self.expression(0)
                        self.state = 270
                        self.match(SchemeParser.R_SQUARE)
                        pass
                    else:
                        raise NoViableAltException(self)
             
                self.state = 276
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
            self.state = 277
            self.type_(0)
            self.state = 278
            self.id_()
            self.state = 279
            self.match(SchemeParser.L_PAREN)
            self.state = 281
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & -9223082599008698304) != 0):
                self.state = 280
                self.paramList()


            self.state = 283
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
            self.state = 285
            self.variable()
            self.state = 290
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==14:
                self.state = 286
                self.match(SchemeParser.COMMA)
                self.state = 287
                self.variable()
                self.state = 292
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


    class OnesExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def ONES_CARET(self):
            return self.getToken(SchemeParser.ONES_CARET, 0)
        def integerAtom(self):
            return self.getTypedRuleContext(SchemeParser.IntegerAtomContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOnesExp" ):
                return visitor.visitOnesExp(self)
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


    class MinusExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def SUBTRACT(self):
            return self.getToken(SchemeParser.SUBTRACT, 0)
        def expression(self):
            return self.getTypedRuleContext(SchemeParser.ExpressionContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMinusExp" ):
                return visitor.visitMinusExp(self)
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


    class ZerosExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def ZEROS_CARET(self):
            return self.getToken(SchemeParser.ZEROS_CARET, 0)
        def integerAtom(self):
            return self.getTypedRuleContext(SchemeParser.IntegerAtomContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitZerosExp" ):
                return visitor.visitZerosExp(self)
            else:
                return visitor.visitChildren(self)


    class ExponentiationExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.ExpressionContext,i)

        def CARET(self):
            return self.getToken(SchemeParser.CARET, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitExponentiationExp" ):
                return visitor.visitExponentiationExp(self)
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
            self.state = 340
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,29,self._ctx)
            if la_ == 1:
                localctx = SchemeParser.NotExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 294
                self.match(SchemeParser.NOT)
                self.state = 295
                self.expression(31)
                pass

            elif la_ == 2:
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

            elif la_ == 3:
                localctx = SchemeParser.MinusExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 300
                self.match(SchemeParser.SUBTRACT)
                self.state = 301
                self.expression(26)
                pass

            elif la_ == 4:
                localctx = SchemeParser.LvalueExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 302
                self.lvalue()
                pass

            elif la_ == 5:
                localctx = SchemeParser.CreateTupleExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 303
                self.match(SchemeParser.L_SQUARE)
                self.state = 312
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & -71768150822616752) != 0):
                    self.state = 304
                    self.expression(0)
                    self.state = 309
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==14:
                        self.state = 305
                        self.match(SchemeParser.COMMA)
                        self.state = 306
                        self.expression(0)
                        self.state = 311
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 314
                self.match(SchemeParser.R_SQUARE)
                pass

            elif la_ == 6:
                localctx = SchemeParser.CreateSetExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 315
                self.match(SchemeParser.L_CURLY)
                self.state = 324
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & -71768150822616752) != 0):
                    self.state = 316
                    self.expression(0)
                    self.state = 321
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==14:
                        self.state = 317
                        self.match(SchemeParser.COMMA)
                        self.state = 318
                        self.expression(0)
                        self.state = 323
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 326
                self.match(SchemeParser.R_CURLY)
                pass

            elif la_ == 7:
                localctx = SchemeParser.TypeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 327
                self.type_(0)
                pass

            elif la_ == 8:
                localctx = SchemeParser.ZerosExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 328
                self.match(SchemeParser.ZEROS_CARET)
                self.state = 329
                self.integerAtom()
                pass

            elif la_ == 9:
                localctx = SchemeParser.OnesExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 330
                self.match(SchemeParser.ONES_CARET)
                self.state = 331
                self.integerAtom()
                pass

            elif la_ == 10:
                localctx = SchemeParser.BinaryNumExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 332
                self.match(SchemeParser.BINARYNUM)
                pass

            elif la_ == 11:
                localctx = SchemeParser.IntExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 333
                self.match(SchemeParser.INT)
                pass

            elif la_ == 12:
                localctx = SchemeParser.BoolExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 334
                self.bool_()
                pass

            elif la_ == 13:
                localctx = SchemeParser.NoneExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 335
                self.match(SchemeParser.NONE)
                pass

            elif la_ == 14:
                localctx = SchemeParser.ParenExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 336
                self.match(SchemeParser.L_PAREN)
                self.state = 337
                self.expression(0)
                self.state = 338
                self.match(SchemeParser.R_PAREN)
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 408
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,32,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 406
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,31,self._ctx)
                    if la_ == 1:
                        localctx = SchemeParser.ExponentiationExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 342
                        if not self.precpred(self._ctx, 29):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 29)")
                        self.state = 343
                        self.match(SchemeParser.CARET)
                        self.state = 344
                        self.expression(29)
                        pass

                    elif la_ == 2:
                        localctx = SchemeParser.MultiplyExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 345
                        if not self.precpred(self._ctx, 28):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 28)")
                        self.state = 346
                        self.match(SchemeParser.TIMES)
                        self.state = 347
                        self.expression(29)
                        pass

                    elif la_ == 3:
                        localctx = SchemeParser.DivideExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 348
                        if not self.precpred(self._ctx, 27):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 27)")
                        self.state = 349
                        self.match(SchemeParser.DIVIDE)
                        self.state = 350
                        self.expression(28)
                        pass

                    elif la_ == 4:
                        localctx = SchemeParser.AddExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 351
                        if not self.precpred(self._ctx, 25):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 25)")
                        self.state = 352
                        self.match(SchemeParser.PLUS)
                        self.state = 353
                        self.expression(26)
                        pass

                    elif la_ == 5:
                        localctx = SchemeParser.SubtractExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 354
                        if not self.precpred(self._ctx, 24):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 24)")
                        self.state = 355
                        self.match(SchemeParser.SUBTRACT)
                        self.state = 356
                        self.expression(25)
                        pass

                    elif la_ == 6:
                        localctx = SchemeParser.EqualsExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 357
                        if not self.precpred(self._ctx, 23):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 23)")
                        self.state = 358
                        self.match(SchemeParser.EQUALSCOMPARE)
                        self.state = 359
                        self.expression(24)
                        pass

                    elif la_ == 7:
                        localctx = SchemeParser.NotEqualsExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 360
                        if not self.precpred(self._ctx, 22):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 22)")
                        self.state = 361
                        self.match(SchemeParser.NOTEQUALS)
                        self.state = 362
                        self.expression(23)
                        pass

                    elif la_ == 8:
                        localctx = SchemeParser.GtExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 363
                        if not self.precpred(self._ctx, 21):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 21)")
                        self.state = 364
                        self.match(SchemeParser.R_ANGLE)
                        self.state = 365
                        self.expression(22)
                        pass

                    elif la_ == 9:
                        localctx = SchemeParser.LtExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 366
                        if not self.precpred(self._ctx, 20):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 20)")
                        self.state = 367
                        self.match(SchemeParser.L_ANGLE)
                        self.state = 368
                        self.expression(21)
                        pass

                    elif la_ == 10:
                        localctx = SchemeParser.GeqExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 369
                        if not self.precpred(self._ctx, 19):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 19)")
                        self.state = 370
                        self.match(SchemeParser.GEQ)
                        self.state = 371
                        self.expression(20)
                        pass

                    elif la_ == 11:
                        localctx = SchemeParser.LeqExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 372
                        if not self.precpred(self._ctx, 18):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 18)")
                        self.state = 373
                        self.match(SchemeParser.LEQ)
                        self.state = 374
                        self.expression(19)
                        pass

                    elif la_ == 12:
                        localctx = SchemeParser.InExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 375
                        if not self.precpred(self._ctx, 17):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 17)")
                        self.state = 376
                        self.match(SchemeParser.IN)
                        self.state = 377
                        self.expression(18)
                        pass

                    elif la_ == 13:
                        localctx = SchemeParser.SubsetsExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 378
                        if not self.precpred(self._ctx, 16):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 16)")
                        self.state = 379
                        self.match(SchemeParser.SUBSETS)
                        self.state = 380
                        self.expression(17)
                        pass

                    elif la_ == 14:
                        localctx = SchemeParser.AndExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 381
                        if not self.precpred(self._ctx, 15):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 15)")
                        self.state = 382
                        self.match(SchemeParser.AND)
                        self.state = 383
                        self.expression(16)
                        pass

                    elif la_ == 15:
                        localctx = SchemeParser.OrExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 384
                        if not self.precpred(self._ctx, 14):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 14)")
                        self.state = 385
                        self.match(SchemeParser.OR)
                        self.state = 386
                        self.expression(15)
                        pass

                    elif la_ == 16:
                        localctx = SchemeParser.UnionExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 387
                        if not self.precpred(self._ctx, 13):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 13)")
                        self.state = 388
                        self.match(SchemeParser.UNION)
                        self.state = 389
                        self.expression(14)
                        pass

                    elif la_ == 17:
                        localctx = SchemeParser.SetMinusExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 390
                        if not self.precpred(self._ctx, 12):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 12)")
                        self.state = 391
                        self.match(SchemeParser.BACKSLASH)
                        self.state = 392
                        self.expression(13)
                        pass

                    elif la_ == 18:
                        localctx = SchemeParser.FnCallExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 393
                        if not self.precpred(self._ctx, 33):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 33)")
                        self.state = 394
                        self.match(SchemeParser.L_PAREN)
                        self.state = 396
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)
                        if (((_la) & ~0x3f) == 0 and ((1 << _la) & -71768150822616752) != 0):
                            self.state = 395
                            self.argList()


                        self.state = 398
                        self.match(SchemeParser.R_PAREN)
                        pass

                    elif la_ == 19:
                        localctx = SchemeParser.SliceExpContext(self, SchemeParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 399
                        if not self.precpred(self._ctx, 32):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 32)")
                        self.state = 400
                        self.match(SchemeParser.L_SQUARE)
                        self.state = 401
                        self.integerExpression(0)
                        self.state = 402
                        self.match(SchemeParser.COLON)
                        self.state = 403
                        self.integerExpression(0)
                        self.state = 404
                        self.match(SchemeParser.R_SQUARE)
                        pass

             
                self.state = 410
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,32,self._ctx)

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
        self.enterRule(localctx, 30, self.RULE_argList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 411
            self.expression(0)
            self.state = 416
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==14:
                self.state = 412
                self.match(SchemeParser.COMMA)
                self.state = 413
                self.expression(0)
                self.state = 418
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
        self.enterRule(localctx, 32, self.RULE_variable)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 419
            self.type_(0)
            self.state = 420
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
        self.enterRule(localctx, 34, self.RULE_parameterizedGame)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 422
            self.match(SchemeParser.ID)
            self.state = 423
            self.match(SchemeParser.L_PAREN)
            self.state = 425
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & -71768150822616752) != 0):
                self.state = 424
                self.argList()


            self.state = 427
            self.match(SchemeParser.R_PAREN)
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


    class VoidTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def VOID(self):
            return self.getToken(SchemeParser.VOID, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVoidType" ):
                return visitor.visitVoidType(self)
            else:
                return visitor.visitChildren(self)


    class ModIntTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SchemeParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def modint(self):
            return self.getTypedRuleContext(SchemeParser.ModintContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitModIntType" ):
                return visitor.visitModIntType(self)
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

        def L_SQUARE(self):
            return self.getToken(SchemeParser.L_SQUARE, 0)
        def type_(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.TypeContext)
            else:
                return self.getTypedRuleContext(SchemeParser.TypeContext,i)

        def R_SQUARE(self):
            return self.getToken(SchemeParser.R_SQUARE, 0)
        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(SchemeParser.COMMA)
            else:
                return self.getToken(SchemeParser.COMMA, i)

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
        _startState = 36
        self.enterRecursionRule(localctx, 36, self.RULE_type, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 461
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [33]:
                localctx = SchemeParser.SetTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 430
                self.set_()
                pass
            elif token in [34]:
                localctx = SchemeParser.BoolTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 431
                self.match(SchemeParser.BOOL)
                pass
            elif token in [35]:
                localctx = SchemeParser.VoidTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 432
                self.match(SchemeParser.VOID)
                pass
            elif token in [37]:
                localctx = SchemeParser.MapTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 433
                self.match(SchemeParser.MAP)
                self.state = 434
                self.match(SchemeParser.L_ANGLE)
                self.state = 435
                self.type_(0)
                self.state = 436
                self.match(SchemeParser.COMMA)
                self.state = 437
                self.type_(0)
                self.state = 438
                self.match(SchemeParser.R_ANGLE)
                pass
            elif token in [42]:
                localctx = SchemeParser.ArrayTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 440
                self.match(SchemeParser.ARRAY)
                self.state = 441
                self.match(SchemeParser.L_ANGLE)
                self.state = 442
                self.type_(0)
                self.state = 443
                self.match(SchemeParser.COMMA)
                self.state = 444
                self.integerExpression(0)
                self.state = 445
                self.match(SchemeParser.R_ANGLE)
                pass
            elif token in [36]:
                localctx = SchemeParser.IntTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 447
                self.match(SchemeParser.INTTYPE)
                pass
            elif token in [6]:
                localctx = SchemeParser.ProductTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 448
                self.match(SchemeParser.L_SQUARE)
                self.state = 449
                self.type_(0)
                self.state = 452 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 450
                    self.match(SchemeParser.COMMA)
                    self.state = 451
                    self.type_(0)
                    self.state = 454 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==14):
                        break

                self.state = 456
                self.match(SchemeParser.R_SQUARE)
                pass
            elif token in [40]:
                localctx = SchemeParser.BitStringTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 458
                self.bitstring()
                pass
            elif token in [41]:
                localctx = SchemeParser.ModIntTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 459
                self.modint()
                pass
            elif token in [48, 63]:
                localctx = SchemeParser.LvalueTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 460
                self.lvalue()
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 467
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,37,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = SchemeParser.OptionalTypeContext(self, SchemeParser.TypeContext(self, _parentctx, _parentState))
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_type)
                    self.state = 463
                    if not self.precpred(self._ctx, 11):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 11)")
                    self.state = 464
                    self.match(SchemeParser.QUESTION) 
                self.state = 469
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,37,self._ctx)

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

        def L_PAREN(self):
            return self.getToken(SchemeParser.L_PAREN, 0)

        def integerExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SchemeParser.IntegerExpressionContext)
            else:
                return self.getTypedRuleContext(SchemeParser.IntegerExpressionContext,i)


        def R_PAREN(self):
            return self.getToken(SchemeParser.R_PAREN, 0)

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
        _startState = 38
        self.enterRecursionRule(localctx, 38, self.RULE_integerExpression, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 478
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [48, 63]:
                self.state = 471
                self.lvalue()
                pass
            elif token in [62]:
                self.state = 472
                self.match(SchemeParser.INT)
                pass
            elif token in [59]:
                self.state = 473
                self.match(SchemeParser.BINARYNUM)
                pass
            elif token in [8]:
                self.state = 474
                self.match(SchemeParser.L_PAREN)
                self.state = 475
                self.integerExpression(0)
                self.state = 476
                self.match(SchemeParser.R_PAREN)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 494
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,40,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 492
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,39,self._ctx)
                    if la_ == 1:
                        localctx = SchemeParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 480
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 8)")
                        self.state = 481
                        self.match(SchemeParser.TIMES)
                        self.state = 482
                        self.integerExpression(9)
                        pass

                    elif la_ == 2:
                        localctx = SchemeParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 483
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 7)")
                        self.state = 484
                        self.match(SchemeParser.DIVIDE)
                        self.state = 485
                        self.integerExpression(8)
                        pass

                    elif la_ == 3:
                        localctx = SchemeParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 486
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 6)")
                        self.state = 487
                        self.match(SchemeParser.PLUS)
                        self.state = 488
                        self.integerExpression(7)
                        pass

                    elif la_ == 4:
                        localctx = SchemeParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 489
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 5)")
                        self.state = 490
                        self.match(SchemeParser.SUBTRACT)
                        self.state = 491
                        self.integerExpression(6)
                        pass

             
                self.state = 496
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,40,self._ctx)

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
            return self.getTypedRuleContext(SchemeParser.LvalueContext,0)


        def INT(self):
            return self.getToken(SchemeParser.INT, 0)

        def L_PAREN(self):
            return self.getToken(SchemeParser.L_PAREN, 0)

        def integerExpression(self):
            return self.getTypedRuleContext(SchemeParser.IntegerExpressionContext,0)


        def R_PAREN(self):
            return self.getToken(SchemeParser.R_PAREN, 0)

        def getRuleIndex(self):
            return SchemeParser.RULE_integerAtom

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIntegerAtom" ):
                return visitor.visitIntegerAtom(self)
            else:
                return visitor.visitChildren(self)




    def integerAtom(self):

        localctx = SchemeParser.IntegerAtomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_integerAtom)
        try:
            self.state = 503
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [48, 63]:
                self.enterOuterAlt(localctx, 1)
                self.state = 497
                self.lvalue()
                pass
            elif token in [62]:
                self.enterOuterAlt(localctx, 2)
                self.state = 498
                self.match(SchemeParser.INT)
                pass
            elif token in [8]:
                self.enterOuterAlt(localctx, 3)
                self.state = 499
                self.match(SchemeParser.L_PAREN)
                self.state = 500
                self.integerExpression(0)
                self.state = 501
                self.match(SchemeParser.R_PAREN)
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
            self.state = 511
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,42,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 505
                self.match(SchemeParser.BITSTRING)
                self.state = 506
                self.match(SchemeParser.L_ANGLE)
                self.state = 507
                self.integerExpression(0)
                self.state = 508
                self.match(SchemeParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 510
                self.match(SchemeParser.BITSTRING)
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
            return self.getToken(SchemeParser.MODINT, 0)

        def L_ANGLE(self):
            return self.getToken(SchemeParser.L_ANGLE, 0)

        def integerExpression(self):
            return self.getTypedRuleContext(SchemeParser.IntegerExpressionContext,0)


        def R_ANGLE(self):
            return self.getToken(SchemeParser.R_ANGLE, 0)

        def getRuleIndex(self):
            return SchemeParser.RULE_modint

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitModint" ):
                return visitor.visitModint(self)
            else:
                return visitor.visitChildren(self)




    def modint(self):

        localctx = SchemeParser.ModintContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_modint)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 513
            self.match(SchemeParser.MODINT)
            self.state = 514
            self.match(SchemeParser.L_ANGLE)
            self.state = 515
            self.integerExpression(0)
            self.state = 516
            self.match(SchemeParser.R_ANGLE)
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
        self.enterRule(localctx, 46, self.RULE_set)
        try:
            self.state = 524
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,43,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 518
                self.match(SchemeParser.SET)
                self.state = 519
                self.match(SchemeParser.L_ANGLE)
                self.state = 520
                self.type_(0)
                self.state = 521
                self.match(SchemeParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 523
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
        self.enterRule(localctx, 48, self.RULE_bool)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 526
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
        self.enterRule(localctx, 50, self.RULE_moduleImport)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 528
            self.match(SchemeParser.IMPORT)
            self.state = 529
            self.match(SchemeParser.FILESTRING)
            self.state = 532
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==52:
                self.state = 530
                self.match(SchemeParser.AS)
                self.state = 531
                self.match(SchemeParser.ID)


            self.state = 534
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
        self.enterRule(localctx, 52, self.RULE_id)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 536
            _la = self._input.LA(1)
            if not(_la==48 or _la==63):
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
                return self.precpred(self._ctx, 11)
         

    def integerExpression_sempred(self, localctx:IntegerExpressionContext, predIndex:int):
            if predIndex == 20:
                return self.precpred(self._ctx, 8)
         

            if predIndex == 21:
                return self.precpred(self._ctx, 7)
         

            if predIndex == 22:
                return self.precpred(self._ctx, 6)
         

            if predIndex == 23:
                return self.precpred(self._ctx, 5)
         




