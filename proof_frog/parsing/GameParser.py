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
        4,1,70,558,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,1,0,5,0,58,8,0,10,0,12,0,61,9,0,1,0,1,0,1,0,1,0,1,0,1,
        1,1,1,1,1,1,1,1,1,1,2,1,2,1,2,1,2,3,2,77,8,2,1,2,1,2,1,2,1,2,1,2,
        1,3,1,3,1,3,5,3,87,8,3,10,3,12,3,90,9,3,1,3,4,3,93,8,3,11,3,12,3,
        94,1,3,1,3,1,3,5,3,100,8,3,10,3,12,3,103,9,3,1,3,5,3,106,8,3,10,
        3,12,3,109,9,3,1,3,4,3,112,8,3,11,3,12,3,113,3,3,116,8,3,1,4,1,4,
        1,4,4,4,121,8,4,11,4,12,4,122,1,4,1,4,1,4,1,4,1,4,1,4,5,4,131,8,
        4,10,4,12,4,134,9,4,1,4,1,4,1,4,1,4,1,5,1,5,1,5,3,5,143,8,5,1,6,
        1,6,1,6,1,6,1,7,1,7,1,7,1,8,1,8,5,8,154,8,8,10,8,12,8,157,9,8,1,
        8,1,8,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,
        9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,
        9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,3,
        9,207,8,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,
        9,1,9,1,9,1,9,1,9,1,9,5,9,228,8,9,10,9,12,9,231,9,9,1,9,1,9,3,9,
        235,8,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,
        1,9,1,9,1,9,1,9,1,9,1,9,3,9,257,8,9,1,10,1,10,1,10,3,10,262,8,10,
        1,10,1,10,1,10,1,10,1,10,1,10,5,10,270,8,10,10,10,12,10,273,9,10,
        1,11,1,11,1,12,5,12,278,8,12,10,12,12,12,281,9,12,1,12,1,12,1,12,
        1,12,3,12,287,8,12,1,12,1,12,1,13,1,13,1,13,5,13,294,8,13,10,13,
        12,13,297,9,13,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,5,14,313,8,14,10,14,12,14,316,9,14,3,14,318,
        8,14,1,14,1,14,1,14,1,14,1,14,5,14,325,8,14,10,14,12,14,328,9,14,
        3,14,330,8,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,3,14,346,8,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,3,14,402,8,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,1,14,5,14,412,8,14,10,14,12,14,415,
        9,14,1,15,1,15,1,15,5,15,420,8,15,10,15,12,15,423,9,15,1,16,1,16,
        1,16,1,17,1,17,1,17,3,17,431,8,17,1,17,1,17,1,18,1,18,1,18,1,18,
        1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,
        1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,
        4,18,465,8,18,11,18,12,18,466,1,18,1,18,1,18,1,18,1,18,1,18,1,18,
        3,18,476,8,18,1,18,1,18,5,18,480,8,18,10,18,12,18,483,9,18,1,19,
        1,19,1,19,1,19,1,19,1,19,1,19,1,19,3,19,493,8,19,1,19,1,19,1,19,
        1,19,1,19,1,19,1,19,1,19,1,19,1,19,1,19,1,19,5,19,507,8,19,10,19,
        12,19,510,9,19,1,20,1,20,1,20,1,20,1,20,1,20,3,20,518,8,20,1,21,
        1,21,1,21,1,21,1,21,1,21,3,21,526,8,21,1,22,1,22,1,22,1,22,1,22,
        1,23,1,23,1,23,1,23,1,23,1,24,1,24,1,24,1,24,1,24,1,24,3,24,544,
        8,24,1,25,1,25,1,26,1,26,1,26,1,26,3,26,552,8,26,1,26,1,26,1,27,
        1,27,1,27,0,3,28,36,38,28,0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,
        30,32,34,36,38,40,42,44,46,48,50,52,54,0,3,1,0,59,60,1,0,61,62,3,
        0,40,41,49,49,67,67,627,0,59,1,0,0,0,2,67,1,0,0,0,4,72,1,0,0,0,6,
        115,1,0,0,0,8,117,1,0,0,0,10,139,1,0,0,0,12,144,1,0,0,0,14,148,1,
        0,0,0,16,151,1,0,0,0,18,256,1,0,0,0,20,261,1,0,0,0,22,274,1,0,0,
        0,24,279,1,0,0,0,26,290,1,0,0,0,28,345,1,0,0,0,30,416,1,0,0,0,32,
        424,1,0,0,0,34,427,1,0,0,0,36,475,1,0,0,0,38,492,1,0,0,0,40,517,
        1,0,0,0,42,525,1,0,0,0,44,527,1,0,0,0,46,532,1,0,0,0,48,543,1,0,
        0,0,50,545,1,0,0,0,52,547,1,0,0,0,54,555,1,0,0,0,56,58,3,52,26,0,
        57,56,1,0,0,0,58,61,1,0,0,0,59,57,1,0,0,0,59,60,1,0,0,0,60,62,1,
        0,0,0,61,59,1,0,0,0,62,63,3,4,2,0,63,64,3,4,2,0,64,65,3,2,1,0,65,
        66,5,0,0,1,66,1,1,0,0,0,67,68,5,52,0,0,68,69,5,53,0,0,69,70,3,54,
        27,0,70,71,5,9,0,0,71,3,1,0,0,0,72,73,5,51,0,0,73,74,3,54,27,0,74,
        76,5,5,0,0,75,77,3,26,13,0,76,75,1,0,0,0,76,77,1,0,0,0,77,78,1,0,
        0,0,78,79,5,6,0,0,79,80,5,1,0,0,80,81,3,6,3,0,81,82,5,2,0,0,82,5,
        1,0,0,0,83,84,3,10,5,0,84,85,5,9,0,0,85,87,1,0,0,0,86,83,1,0,0,0,
        87,90,1,0,0,0,88,86,1,0,0,0,88,89,1,0,0,0,89,92,1,0,0,0,90,88,1,
        0,0,0,91,93,3,14,7,0,92,91,1,0,0,0,93,94,1,0,0,0,94,92,1,0,0,0,94,
        95,1,0,0,0,95,116,1,0,0,0,96,97,3,10,5,0,97,98,5,9,0,0,98,100,1,
        0,0,0,99,96,1,0,0,0,100,103,1,0,0,0,101,99,1,0,0,0,101,102,1,0,0,
        0,102,107,1,0,0,0,103,101,1,0,0,0,104,106,3,14,7,0,105,104,1,0,0,
        0,106,109,1,0,0,0,107,105,1,0,0,0,107,108,1,0,0,0,108,111,1,0,0,
        0,109,107,1,0,0,0,110,112,3,8,4,0,111,110,1,0,0,0,112,113,1,0,0,
        0,113,111,1,0,0,0,113,114,1,0,0,0,114,116,1,0,0,0,115,88,1,0,0,0,
        115,101,1,0,0,0,116,7,1,0,0,0,117,118,5,54,0,0,118,120,5,1,0,0,119,
        121,3,14,7,0,120,119,1,0,0,0,121,122,1,0,0,0,122,120,1,0,0,0,122,
        123,1,0,0,0,123,124,1,0,0,0,124,125,5,55,0,0,125,126,5,10,0,0,126,
        127,5,3,0,0,127,132,3,54,27,0,128,129,5,11,0,0,129,131,3,54,27,0,
        130,128,1,0,0,0,131,134,1,0,0,0,132,130,1,0,0,0,132,133,1,0,0,0,
        133,135,1,0,0,0,134,132,1,0,0,0,135,136,5,4,0,0,136,137,5,9,0,0,
        137,138,5,2,0,0,138,9,1,0,0,0,139,142,3,32,16,0,140,141,5,14,0,0,
        141,143,3,28,14,0,142,140,1,0,0,0,142,143,1,0,0,0,143,11,1,0,0,0,
        144,145,3,32,16,0,145,146,5,14,0,0,146,147,3,28,14,0,147,13,1,0,
        0,0,148,149,3,24,12,0,149,150,3,16,8,0,150,15,1,0,0,0,151,155,5,
        1,0,0,152,154,3,18,9,0,153,152,1,0,0,0,154,157,1,0,0,0,155,153,1,
        0,0,0,155,156,1,0,0,0,156,158,1,0,0,0,157,155,1,0,0,0,158,159,5,
        2,0,0,159,17,1,0,0,0,160,161,3,36,18,0,161,162,3,54,27,0,162,163,
        5,9,0,0,163,257,1,0,0,0,164,165,3,36,18,0,165,166,3,20,10,0,166,
        167,5,14,0,0,167,168,3,28,14,0,168,169,5,9,0,0,169,257,1,0,0,0,170,
        171,3,36,18,0,171,172,3,20,10,0,172,173,5,25,0,0,173,174,3,28,14,
        0,174,175,5,9,0,0,175,257,1,0,0,0,176,177,3,20,10,0,177,178,5,14,
        0,0,178,179,3,28,14,0,179,180,5,9,0,0,180,257,1,0,0,0,181,182,3,
        20,10,0,182,183,5,25,0,0,183,184,3,28,14,0,184,185,5,9,0,0,185,257,
        1,0,0,0,186,187,3,36,18,0,187,188,3,20,10,0,188,189,5,24,0,0,189,
        190,5,3,0,0,190,191,3,20,10,0,191,192,5,4,0,0,192,193,3,36,18,0,
        193,194,5,9,0,0,194,257,1,0,0,0,195,196,3,20,10,0,196,197,5,24,0,
        0,197,198,5,3,0,0,198,199,3,20,10,0,199,200,5,4,0,0,200,201,3,36,
        18,0,201,202,5,9,0,0,202,257,1,0,0,0,203,204,3,28,14,0,204,206,5,
        5,0,0,205,207,3,30,15,0,206,205,1,0,0,0,206,207,1,0,0,0,207,208,
        1,0,0,0,208,209,5,6,0,0,209,210,5,9,0,0,210,257,1,0,0,0,211,212,
        5,36,0,0,212,213,3,28,14,0,213,214,5,9,0,0,214,257,1,0,0,0,215,216,
        5,46,0,0,216,217,5,5,0,0,217,218,3,28,14,0,218,219,5,6,0,0,219,229,
        3,16,8,0,220,221,5,56,0,0,221,222,5,46,0,0,222,223,5,5,0,0,223,224,
        3,28,14,0,224,225,5,6,0,0,225,226,3,16,8,0,226,228,1,0,0,0,227,220,
        1,0,0,0,228,231,1,0,0,0,229,227,1,0,0,0,229,230,1,0,0,0,230,234,
        1,0,0,0,231,229,1,0,0,0,232,233,5,56,0,0,233,235,3,16,8,0,234,232,
        1,0,0,0,234,235,1,0,0,0,235,257,1,0,0,0,236,237,5,47,0,0,237,238,
        5,5,0,0,238,239,5,34,0,0,239,240,3,54,27,0,240,241,5,14,0,0,241,
        242,3,28,14,0,242,243,5,48,0,0,243,244,3,28,14,0,244,245,5,6,0,0,
        245,246,3,16,8,0,246,257,1,0,0,0,247,248,5,47,0,0,248,249,5,5,0,
        0,249,250,3,36,18,0,250,251,3,54,27,0,251,252,5,49,0,0,252,253,3,
        28,14,0,253,254,5,6,0,0,254,255,3,16,8,0,255,257,1,0,0,0,256,160,
        1,0,0,0,256,164,1,0,0,0,256,170,1,0,0,0,256,176,1,0,0,0,256,181,
        1,0,0,0,256,186,1,0,0,0,256,195,1,0,0,0,256,203,1,0,0,0,256,211,
        1,0,0,0,256,215,1,0,0,0,256,236,1,0,0,0,256,247,1,0,0,0,257,19,1,
        0,0,0,258,262,3,54,27,0,259,262,3,34,17,0,260,262,5,58,0,0,261,258,
        1,0,0,0,261,259,1,0,0,0,261,260,1,0,0,0,262,271,1,0,0,0,263,264,
        5,12,0,0,264,270,3,54,27,0,265,266,5,3,0,0,266,267,3,28,14,0,267,
        268,5,4,0,0,268,270,1,0,0,0,269,263,1,0,0,0,269,265,1,0,0,0,270,
        273,1,0,0,0,271,269,1,0,0,0,271,272,1,0,0,0,272,21,1,0,0,0,273,271,
        1,0,0,0,274,275,7,0,0,0,275,23,1,0,0,0,276,278,3,22,11,0,277,276,
        1,0,0,0,278,281,1,0,0,0,279,277,1,0,0,0,279,280,1,0,0,0,280,282,
        1,0,0,0,281,279,1,0,0,0,282,283,3,36,18,0,283,284,3,54,27,0,284,
        286,5,5,0,0,285,287,3,26,13,0,286,285,1,0,0,0,286,287,1,0,0,0,287,
        288,1,0,0,0,288,289,5,6,0,0,289,25,1,0,0,0,290,295,3,32,16,0,291,
        292,5,11,0,0,292,294,3,32,16,0,293,291,1,0,0,0,294,297,1,0,0,0,295,
        293,1,0,0,0,295,296,1,0,0,0,296,27,1,0,0,0,297,295,1,0,0,0,298,299,
        6,14,-1,0,299,300,5,28,0,0,300,346,3,28,14,31,301,302,5,30,0,0,302,
        303,3,28,14,0,303,304,5,30,0,0,304,346,1,0,0,0,305,306,5,16,0,0,
        306,346,3,28,14,26,307,346,3,20,10,0,308,317,5,3,0,0,309,314,3,28,
        14,0,310,311,5,11,0,0,311,313,3,28,14,0,312,310,1,0,0,0,313,316,
        1,0,0,0,314,312,1,0,0,0,314,315,1,0,0,0,315,318,1,0,0,0,316,314,
        1,0,0,0,317,309,1,0,0,0,317,318,1,0,0,0,318,319,1,0,0,0,319,346,
        5,4,0,0,320,329,5,1,0,0,321,326,3,28,14,0,322,323,5,11,0,0,323,325,
        3,28,14,0,324,322,1,0,0,0,325,328,1,0,0,0,326,324,1,0,0,0,326,327,
        1,0,0,0,327,330,1,0,0,0,328,326,1,0,0,0,329,321,1,0,0,0,329,330,
        1,0,0,0,330,331,1,0,0,0,331,346,5,2,0,0,332,346,3,36,18,0,333,334,
        5,64,0,0,334,346,3,40,20,0,335,336,5,65,0,0,336,346,3,40,20,0,337,
        346,5,63,0,0,338,346,5,66,0,0,339,346,3,50,25,0,340,346,5,57,0,0,
        341,342,5,5,0,0,342,343,3,28,14,0,343,344,5,6,0,0,344,346,1,0,0,
        0,345,298,1,0,0,0,345,301,1,0,0,0,345,305,1,0,0,0,345,307,1,0,0,
        0,345,308,1,0,0,0,345,320,1,0,0,0,345,332,1,0,0,0,345,333,1,0,0,
        0,345,335,1,0,0,0,345,337,1,0,0,0,345,338,1,0,0,0,345,339,1,0,0,
        0,345,340,1,0,0,0,345,341,1,0,0,0,346,413,1,0,0,0,347,348,10,29,
        0,0,348,349,5,29,0,0,349,412,3,28,14,29,350,351,10,28,0,0,351,352,
        5,13,0,0,352,412,3,28,14,29,353,354,10,27,0,0,354,355,5,17,0,0,355,
        412,3,28,14,28,356,357,10,25,0,0,357,358,5,15,0,0,358,412,3,28,14,
        26,359,360,10,24,0,0,360,361,5,16,0,0,361,412,3,28,14,25,362,363,
        10,23,0,0,363,364,5,19,0,0,364,412,3,28,14,24,365,366,10,22,0,0,
        366,367,5,20,0,0,367,412,3,28,14,23,368,369,10,21,0,0,369,370,5,
        8,0,0,370,412,3,28,14,22,371,372,10,20,0,0,372,373,5,7,0,0,373,412,
        3,28,14,21,374,375,10,19,0,0,375,376,5,21,0,0,376,412,3,28,14,20,
        377,378,10,18,0,0,378,379,5,22,0,0,379,412,3,28,14,19,380,381,10,
        17,0,0,381,382,5,49,0,0,382,412,3,28,14,18,383,384,10,16,0,0,384,
        385,5,45,0,0,385,412,3,28,14,17,386,387,10,15,0,0,387,388,5,26,0,
        0,388,412,3,28,14,16,389,390,10,14,0,0,390,391,5,23,0,0,391,412,
        3,28,14,15,392,393,10,13,0,0,393,394,5,50,0,0,394,412,3,28,14,14,
        395,396,10,12,0,0,396,397,5,27,0,0,397,412,3,28,14,13,398,399,10,
        33,0,0,399,401,5,5,0,0,400,402,3,30,15,0,401,400,1,0,0,0,401,402,
        1,0,0,0,402,403,1,0,0,0,403,412,5,6,0,0,404,405,10,32,0,0,405,406,
        5,3,0,0,406,407,3,38,19,0,407,408,5,10,0,0,408,409,3,38,19,0,409,
        410,5,4,0,0,410,412,1,0,0,0,411,347,1,0,0,0,411,350,1,0,0,0,411,
        353,1,0,0,0,411,356,1,0,0,0,411,359,1,0,0,0,411,362,1,0,0,0,411,
        365,1,0,0,0,411,368,1,0,0,0,411,371,1,0,0,0,411,374,1,0,0,0,411,
        377,1,0,0,0,411,380,1,0,0,0,411,383,1,0,0,0,411,386,1,0,0,0,411,
        389,1,0,0,0,411,392,1,0,0,0,411,395,1,0,0,0,411,398,1,0,0,0,411,
        404,1,0,0,0,412,415,1,0,0,0,413,411,1,0,0,0,413,414,1,0,0,0,414,
        29,1,0,0,0,415,413,1,0,0,0,416,421,3,28,14,0,417,418,5,11,0,0,418,
        420,3,28,14,0,419,417,1,0,0,0,420,423,1,0,0,0,421,419,1,0,0,0,421,
        422,1,0,0,0,422,31,1,0,0,0,423,421,1,0,0,0,424,425,3,36,18,0,425,
        426,3,54,27,0,426,33,1,0,0,0,427,428,3,54,27,0,428,430,5,5,0,0,429,
        431,3,30,15,0,430,429,1,0,0,0,430,431,1,0,0,0,431,432,1,0,0,0,432,
        433,5,6,0,0,433,35,1,0,0,0,434,435,6,18,-1,0,435,476,3,48,24,0,436,
        476,5,32,0,0,437,476,5,33,0,0,438,439,5,35,0,0,439,440,5,7,0,0,440,
        441,3,36,18,0,441,442,5,11,0,0,442,443,3,36,18,0,443,444,5,8,0,0,
        444,476,1,0,0,0,445,446,5,42,0,0,446,447,5,7,0,0,447,448,3,36,18,
        0,448,449,5,11,0,0,449,450,3,38,19,0,450,451,5,8,0,0,451,476,1,0,
        0,0,452,453,5,43,0,0,453,454,5,7,0,0,454,455,3,36,18,0,455,456,5,
        11,0,0,456,457,3,36,18,0,457,458,5,8,0,0,458,476,1,0,0,0,459,476,
        5,34,0,0,460,461,5,3,0,0,461,464,3,36,18,0,462,463,5,11,0,0,463,
        465,3,36,18,0,464,462,1,0,0,0,465,466,1,0,0,0,466,464,1,0,0,0,466,
        467,1,0,0,0,467,468,1,0,0,0,468,469,5,4,0,0,469,476,1,0,0,0,470,
        476,3,42,21,0,471,476,3,44,22,0,472,476,3,46,23,0,473,476,5,40,0,
        0,474,476,3,20,10,0,475,434,1,0,0,0,475,436,1,0,0,0,475,437,1,0,
        0,0,475,438,1,0,0,0,475,445,1,0,0,0,475,452,1,0,0,0,475,459,1,0,
        0,0,475,460,1,0,0,0,475,470,1,0,0,0,475,471,1,0,0,0,475,472,1,0,
        0,0,475,473,1,0,0,0,475,474,1,0,0,0,476,481,1,0,0,0,477,478,10,14,
        0,0,478,480,5,18,0,0,479,477,1,0,0,0,480,483,1,0,0,0,481,479,1,0,
        0,0,481,482,1,0,0,0,482,37,1,0,0,0,483,481,1,0,0,0,484,485,6,19,
        -1,0,485,493,3,20,10,0,486,493,5,66,0,0,487,493,5,63,0,0,488,489,
        5,5,0,0,489,490,3,38,19,0,490,491,5,6,0,0,491,493,1,0,0,0,492,484,
        1,0,0,0,492,486,1,0,0,0,492,487,1,0,0,0,492,488,1,0,0,0,493,508,
        1,0,0,0,494,495,10,8,0,0,495,496,5,13,0,0,496,507,3,38,19,9,497,
        498,10,7,0,0,498,499,5,17,0,0,499,507,3,38,19,8,500,501,10,6,0,0,
        501,502,5,15,0,0,502,507,3,38,19,7,503,504,10,5,0,0,504,505,5,16,
        0,0,505,507,3,38,19,6,506,494,1,0,0,0,506,497,1,0,0,0,506,500,1,
        0,0,0,506,503,1,0,0,0,507,510,1,0,0,0,508,506,1,0,0,0,508,509,1,
        0,0,0,509,39,1,0,0,0,510,508,1,0,0,0,511,518,3,20,10,0,512,518,5,
        66,0,0,513,514,5,5,0,0,514,515,3,38,19,0,515,516,5,6,0,0,516,518,
        1,0,0,0,517,511,1,0,0,0,517,512,1,0,0,0,517,513,1,0,0,0,518,41,1,
        0,0,0,519,520,5,38,0,0,520,521,5,7,0,0,521,522,3,38,19,0,522,523,
        5,8,0,0,523,526,1,0,0,0,524,526,5,38,0,0,525,519,1,0,0,0,525,524,
        1,0,0,0,526,43,1,0,0,0,527,528,5,39,0,0,528,529,5,7,0,0,529,530,
        3,38,19,0,530,531,5,8,0,0,531,45,1,0,0,0,532,533,5,41,0,0,533,534,
        5,7,0,0,534,535,3,20,10,0,535,536,5,8,0,0,536,47,1,0,0,0,537,538,
        5,31,0,0,538,539,5,7,0,0,539,540,3,36,18,0,540,541,5,8,0,0,541,544,
        1,0,0,0,542,544,5,31,0,0,543,537,1,0,0,0,543,542,1,0,0,0,544,49,
        1,0,0,0,545,546,7,1,0,0,546,51,1,0,0,0,547,548,5,37,0,0,548,551,
        5,70,0,0,549,550,5,53,0,0,550,552,5,67,0,0,551,549,1,0,0,0,551,552,
        1,0,0,0,552,553,1,0,0,0,553,554,5,9,0,0,554,53,1,0,0,0,555,556,7,
        2,0,0,556,55,1,0,0,0,42,59,76,88,94,101,107,113,115,122,132,142,
        155,206,229,234,256,261,269,271,279,286,295,314,317,326,329,345,
        401,411,413,421,430,466,475,481,492,506,508,517,525,543,551
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
                     "'in'", "'union'", "'Game'", "'export'", "'as'", "'Phase'", 
                     "'oracles'", "'else'", "'None'", "'this'", "'deterministic'", 
                     "'injective'", "'true'", "'false'", "<INVALID>", "'0^'", 
                     "'1^'" ]

    symbolicNames = [ "<INVALID>", "L_CURLY", "R_CURLY", "L_SQUARE", "R_SQUARE", 
                      "L_PAREN", "R_PAREN", "L_ANGLE", "R_ANGLE", "SEMI", 
                      "COLON", "COMMA", "PERIOD", "TIMES", "EQUALS", "PLUS", 
                      "SUBTRACT", "DIVIDE", "QUESTION", "EQUALSCOMPARE", 
                      "NOTEQUALS", "GEQ", "LEQ", "OR", "SAMPUNIQ", "SAMPLES", 
                      "AND", "BACKSLASH", "NOT", "CARET", "VBAR", "SET", 
                      "BOOL", "VOID", "INTTYPE", "MAP", "RETURN", "IMPORT", 
                      "BITSTRING", "MODINT", "GROUP", "GROUPELEM", "ARRAY", 
                      "FUNCTION", "PRIMITIVE", "SUBSETS", "IF", "FOR", "TO", 
                      "IN", "UNION", "GAME", "EXPORT", "AS", "PHASE", "ORACLES", 
                      "ELSE", "NONE", "THIS", "DETERMINISTIC", "INJECTIVE", 
                      "TRUE", "FALSE", "BINARYNUM", "ZEROS_CARET", "ONES_CARET", 
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
    RULE_groupelem = 23
    RULE_set = 24
    RULE_bool = 25
    RULE_moduleImport = 26
    RULE_id = 27

    ruleNames =  [ "program", "gameExport", "game", "gameBody", "gamePhase", 
                   "field", "initializedField", "method", "block", "statement", 
                   "lvalue", "methodModifier", "methodSignature", "paramList", 
                   "expression", "argList", "variable", "parameterizedGame", 
                   "type", "integerExpression", "integerAtom", "bitstring", 
                   "modint", "groupelem", "set", "bool", "moduleImport", 
                   "id" ]

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
    PHASE=54
    ORACLES=55
    ELSE=56
    NONE=57
    THIS=58
    DETERMINISTIC=59
    INJECTIVE=60
    TRUE=61
    FALSE=62
    BINARYNUM=63
    ZEROS_CARET=64
    ONES_CARET=65
    INT=66
    ID=67
    WS=68
    LINE_COMMENT=69
    FILESTRING=70

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
            self.state = 59
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==37:
                self.state = 56
                self.moduleImport()
                self.state = 61
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 62
            self.game()
            self.state = 63
            self.game()
            self.state = 64
            self.gameExport()
            self.state = 65
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
            self.state = 67
            self.match(GameParser.EXPORT)
            self.state = 68
            self.match(GameParser.AS)
            self.state = 69
            self.id_()
            self.state = 70
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
            self.state = 72
            self.match(GameParser.GAME)
            self.state = 73
            self.id_()
            self.state = 74
            self.match(GameParser.L_PAREN)
            self.state = 76
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 288810709985263624) != 0) or _la==67:
                self.state = 75
                self.paramList()


            self.state = 78
            self.match(GameParser.R_PAREN)
            self.state = 79
            self.match(GameParser.L_CURLY)
            self.state = 80
            self.gameBody()
            self.state = 81
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
            self.state = 115
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,7,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 88
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,2,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 83
                        self.field()
                        self.state = 84
                        self.match(GameParser.SEMI) 
                    self.state = 90
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,2,self._ctx)

                self.state = 92 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 91
                    self.method()
                    self.state = 94 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 2018192966895534088) != 0) or _la==67):
                        break

                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 101
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,4,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 96
                        self.field()
                        self.state = 97
                        self.match(GameParser.SEMI) 
                    self.state = 103
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,4,self._ctx)

                self.state = 107
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while (((_la) & ~0x3f) == 0 and ((1 << _la) & 2018192966895534088) != 0) or _la==67:
                    self.state = 104
                    self.method()
                    self.state = 109
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 111 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 110
                    self.gamePhase()
                    self.state = 113 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==54):
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
            self.state = 117
            self.match(GameParser.PHASE)
            self.state = 118
            self.match(GameParser.L_CURLY)
            self.state = 120 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 119
                self.method()
                self.state = 122 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 2018192966895534088) != 0) or _la==67):
                    break

            self.state = 124
            self.match(GameParser.ORACLES)
            self.state = 125
            self.match(GameParser.COLON)
            self.state = 126
            self.match(GameParser.L_SQUARE)
            self.state = 127
            self.id_()
            self.state = 132
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==11:
                self.state = 128
                self.match(GameParser.COMMA)
                self.state = 129
                self.id_()
                self.state = 134
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 135
            self.match(GameParser.R_SQUARE)
            self.state = 136
            self.match(GameParser.SEMI)
            self.state = 137
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
            self.state = 139
            self.variable()
            self.state = 142
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==14:
                self.state = 140
                self.match(GameParser.EQUALS)
                self.state = 141
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
            self.state = 144
            self.variable()
            self.state = 145
            self.match(GameParser.EQUALS)
            self.state = 146
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
            self.state = 148
            self.methodSignature()
            self.state = 149
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
            self.state = 151
            self.match(GameParser.L_CURLY)
            self.state = 155
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & -1872705934858321878) != 0) or ((((_la - 64)) & ~0x3f) == 0 and ((1 << (_la - 64)) & 15) != 0):
                self.state = 152
                self.statement()
                self.state = 157
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 158
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
            self.state = 256
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,15,self._ctx)
            if la_ == 1:
                localctx = GameParser.VarDeclStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 160
                self.type_(0)
                self.state = 161
                self.id_()
                self.state = 162
                self.match(GameParser.SEMI)
                pass

            elif la_ == 2:
                localctx = GameParser.VarDeclWithValueStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 164
                self.type_(0)
                self.state = 165
                self.lvalue()
                self.state = 166
                self.match(GameParser.EQUALS)
                self.state = 167
                self.expression(0)
                self.state = 168
                self.match(GameParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GameParser.VarDeclWithSampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 170
                self.type_(0)
                self.state = 171
                self.lvalue()
                self.state = 172
                self.match(GameParser.SAMPLES)
                self.state = 173
                self.expression(0)
                self.state = 174
                self.match(GameParser.SEMI)
                pass

            elif la_ == 4:
                localctx = GameParser.AssignmentStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 176
                self.lvalue()
                self.state = 177
                self.match(GameParser.EQUALS)
                self.state = 178
                self.expression(0)
                self.state = 179
                self.match(GameParser.SEMI)
                pass

            elif la_ == 5:
                localctx = GameParser.SampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 5)
                self.state = 181
                self.lvalue()
                self.state = 182
                self.match(GameParser.SAMPLES)
                self.state = 183
                self.expression(0)
                self.state = 184
                self.match(GameParser.SEMI)
                pass

            elif la_ == 6:
                localctx = GameParser.UniqueSampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 6)
                self.state = 186
                self.type_(0)
                self.state = 187
                self.lvalue()
                self.state = 188
                self.match(GameParser.SAMPUNIQ)
                self.state = 189
                self.match(GameParser.L_SQUARE)
                self.state = 190
                self.lvalue()
                self.state = 191
                self.match(GameParser.R_SQUARE)
                self.state = 192
                self.type_(0)
                self.state = 193
                self.match(GameParser.SEMI)
                pass

            elif la_ == 7:
                localctx = GameParser.UniqueSampleNoTypeStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 7)
                self.state = 195
                self.lvalue()
                self.state = 196
                self.match(GameParser.SAMPUNIQ)
                self.state = 197
                self.match(GameParser.L_SQUARE)
                self.state = 198
                self.lvalue()
                self.state = 199
                self.match(GameParser.R_SQUARE)
                self.state = 200
                self.type_(0)
                self.state = 201
                self.match(GameParser.SEMI)
                pass

            elif la_ == 8:
                localctx = GameParser.FunctionCallStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 8)
                self.state = 203
                self.expression(0)
                self.state = 204
                self.match(GameParser.L_PAREN)
                self.state = 206
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & -1872917109810331606) != 0) or ((((_la - 64)) & ~0x3f) == 0 and ((1 << (_la - 64)) & 15) != 0):
                    self.state = 205
                    self.argList()


                self.state = 208
                self.match(GameParser.R_PAREN)
                self.state = 209
                self.match(GameParser.SEMI)
                pass

            elif la_ == 9:
                localctx = GameParser.ReturnStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 9)
                self.state = 211
                self.match(GameParser.RETURN)
                self.state = 212
                self.expression(0)
                self.state = 213
                self.match(GameParser.SEMI)
                pass

            elif la_ == 10:
                localctx = GameParser.IfStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 10)
                self.state = 215
                self.match(GameParser.IF)
                self.state = 216
                self.match(GameParser.L_PAREN)
                self.state = 217
                self.expression(0)
                self.state = 218
                self.match(GameParser.R_PAREN)
                self.state = 219
                self.block()
                self.state = 229
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,13,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 220
                        self.match(GameParser.ELSE)
                        self.state = 221
                        self.match(GameParser.IF)
                        self.state = 222
                        self.match(GameParser.L_PAREN)
                        self.state = 223
                        self.expression(0)
                        self.state = 224
                        self.match(GameParser.R_PAREN)
                        self.state = 225
                        self.block() 
                    self.state = 231
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,13,self._ctx)

                self.state = 234
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==56:
                    self.state = 232
                    self.match(GameParser.ELSE)
                    self.state = 233
                    self.block()


                pass

            elif la_ == 11:
                localctx = GameParser.NumericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 11)
                self.state = 236
                self.match(GameParser.FOR)
                self.state = 237
                self.match(GameParser.L_PAREN)
                self.state = 238
                self.match(GameParser.INTTYPE)
                self.state = 239
                self.id_()
                self.state = 240
                self.match(GameParser.EQUALS)
                self.state = 241
                self.expression(0)
                self.state = 242
                self.match(GameParser.TO)
                self.state = 243
                self.expression(0)
                self.state = 244
                self.match(GameParser.R_PAREN)
                self.state = 245
                self.block()
                pass

            elif la_ == 12:
                localctx = GameParser.GenericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 12)
                self.state = 247
                self.match(GameParser.FOR)
                self.state = 248
                self.match(GameParser.L_PAREN)
                self.state = 249
                self.type_(0)
                self.state = 250
                self.id_()
                self.state = 251
                self.match(GameParser.IN)
                self.state = 252
                self.expression(0)
                self.state = 253
                self.match(GameParser.R_PAREN)
                self.state = 254
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
            self.state = 261
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,16,self._ctx)
            if la_ == 1:
                self.state = 258
                self.id_()
                pass

            elif la_ == 2:
                self.state = 259
                self.parameterizedGame()
                pass

            elif la_ == 3:
                self.state = 260
                self.match(GameParser.THIS)
                pass


            self.state = 271
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,18,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 269
                    self._errHandler.sync(self)
                    token = self._input.LA(1)
                    if token in [12]:
                        self.state = 263
                        self.match(GameParser.PERIOD)
                        self.state = 264
                        self.id_()
                        pass
                    elif token in [3]:
                        self.state = 265
                        self.match(GameParser.L_SQUARE)
                        self.state = 266
                        self.expression(0)
                        self.state = 267
                        self.match(GameParser.R_SQUARE)
                        pass
                    else:
                        raise NoViableAltException(self)
             
                self.state = 273
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
            self.state = 274
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
            self.state = 279
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59 or _la==60:
                self.state = 276
                self.methodModifier()
                self.state = 281
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 282
            self.type_(0)
            self.state = 283
            self.id_()
            self.state = 284
            self.match(GameParser.L_PAREN)
            self.state = 286
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 288810709985263624) != 0) or _la==67:
                self.state = 285
                self.paramList()


            self.state = 288
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
            self.state = 290
            self.variable()
            self.state = 295
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==11:
                self.state = 291
                self.match(GameParser.COMMA)
                self.state = 292
                self.variable()
                self.state = 297
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
            self.state = 345
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,26,self._ctx)
            if la_ == 1:
                localctx = GameParser.NotExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 299
                self.match(GameParser.NOT)
                self.state = 300
                self.expression(31)
                pass

            elif la_ == 2:
                localctx = GameParser.SizeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 301
                self.match(GameParser.VBAR)
                self.state = 302
                self.expression(0)
                self.state = 303
                self.match(GameParser.VBAR)
                pass

            elif la_ == 3:
                localctx = GameParser.MinusExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 305
                self.match(GameParser.SUBTRACT)
                self.state = 306
                self.expression(26)
                pass

            elif la_ == 4:
                localctx = GameParser.LvalueExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 307
                self.lvalue()
                pass

            elif la_ == 5:
                localctx = GameParser.CreateTupleExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 308
                self.match(GameParser.L_SQUARE)
                self.state = 317
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & -1872917109810331606) != 0) or ((((_la - 64)) & ~0x3f) == 0 and ((1 << (_la - 64)) & 15) != 0):
                    self.state = 309
                    self.expression(0)
                    self.state = 314
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==11:
                        self.state = 310
                        self.match(GameParser.COMMA)
                        self.state = 311
                        self.expression(0)
                        self.state = 316
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 319
                self.match(GameParser.R_SQUARE)
                pass

            elif la_ == 6:
                localctx = GameParser.CreateSetExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 320
                self.match(GameParser.L_CURLY)
                self.state = 329
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & -1872917109810331606) != 0) or ((((_la - 64)) & ~0x3f) == 0 and ((1 << (_la - 64)) & 15) != 0):
                    self.state = 321
                    self.expression(0)
                    self.state = 326
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==11:
                        self.state = 322
                        self.match(GameParser.COMMA)
                        self.state = 323
                        self.expression(0)
                        self.state = 328
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 331
                self.match(GameParser.R_CURLY)
                pass

            elif la_ == 7:
                localctx = GameParser.TypeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 332
                self.type_(0)
                pass

            elif la_ == 8:
                localctx = GameParser.ZerosExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 333
                self.match(GameParser.ZEROS_CARET)
                self.state = 334
                self.integerAtom()
                pass

            elif la_ == 9:
                localctx = GameParser.OnesExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 335
                self.match(GameParser.ONES_CARET)
                self.state = 336
                self.integerAtom()
                pass

            elif la_ == 10:
                localctx = GameParser.BinaryNumExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 337
                self.match(GameParser.BINARYNUM)
                pass

            elif la_ == 11:
                localctx = GameParser.IntExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 338
                self.match(GameParser.INT)
                pass

            elif la_ == 12:
                localctx = GameParser.BoolExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 339
                self.bool_()
                pass

            elif la_ == 13:
                localctx = GameParser.NoneExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 340
                self.match(GameParser.NONE)
                pass

            elif la_ == 14:
                localctx = GameParser.ParenExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 341
                self.match(GameParser.L_PAREN)
                self.state = 342
                self.expression(0)
                self.state = 343
                self.match(GameParser.R_PAREN)
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 413
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,29,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 411
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,28,self._ctx)
                    if la_ == 1:
                        localctx = GameParser.ExponentiationExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 347
                        if not self.precpred(self._ctx, 29):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 29)")
                        self.state = 348
                        self.match(GameParser.CARET)
                        self.state = 349
                        self.expression(29)
                        pass

                    elif la_ == 2:
                        localctx = GameParser.MultiplyExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 350
                        if not self.precpred(self._ctx, 28):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 28)")
                        self.state = 351
                        self.match(GameParser.TIMES)
                        self.state = 352
                        self.expression(29)
                        pass

                    elif la_ == 3:
                        localctx = GameParser.DivideExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 353
                        if not self.precpred(self._ctx, 27):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 27)")
                        self.state = 354
                        self.match(GameParser.DIVIDE)
                        self.state = 355
                        self.expression(28)
                        pass

                    elif la_ == 4:
                        localctx = GameParser.AddExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 356
                        if not self.precpred(self._ctx, 25):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 25)")
                        self.state = 357
                        self.match(GameParser.PLUS)
                        self.state = 358
                        self.expression(26)
                        pass

                    elif la_ == 5:
                        localctx = GameParser.SubtractExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 359
                        if not self.precpred(self._ctx, 24):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 24)")
                        self.state = 360
                        self.match(GameParser.SUBTRACT)
                        self.state = 361
                        self.expression(25)
                        pass

                    elif la_ == 6:
                        localctx = GameParser.EqualsExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 362
                        if not self.precpred(self._ctx, 23):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 23)")
                        self.state = 363
                        self.match(GameParser.EQUALSCOMPARE)
                        self.state = 364
                        self.expression(24)
                        pass

                    elif la_ == 7:
                        localctx = GameParser.NotEqualsExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 365
                        if not self.precpred(self._ctx, 22):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 22)")
                        self.state = 366
                        self.match(GameParser.NOTEQUALS)
                        self.state = 367
                        self.expression(23)
                        pass

                    elif la_ == 8:
                        localctx = GameParser.GtExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 368
                        if not self.precpred(self._ctx, 21):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 21)")
                        self.state = 369
                        self.match(GameParser.R_ANGLE)
                        self.state = 370
                        self.expression(22)
                        pass

                    elif la_ == 9:
                        localctx = GameParser.LtExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 371
                        if not self.precpred(self._ctx, 20):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 20)")
                        self.state = 372
                        self.match(GameParser.L_ANGLE)
                        self.state = 373
                        self.expression(21)
                        pass

                    elif la_ == 10:
                        localctx = GameParser.GeqExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 374
                        if not self.precpred(self._ctx, 19):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 19)")
                        self.state = 375
                        self.match(GameParser.GEQ)
                        self.state = 376
                        self.expression(20)
                        pass

                    elif la_ == 11:
                        localctx = GameParser.LeqExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 377
                        if not self.precpred(self._ctx, 18):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 18)")
                        self.state = 378
                        self.match(GameParser.LEQ)
                        self.state = 379
                        self.expression(19)
                        pass

                    elif la_ == 12:
                        localctx = GameParser.InExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 380
                        if not self.precpred(self._ctx, 17):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 17)")
                        self.state = 381
                        self.match(GameParser.IN)
                        self.state = 382
                        self.expression(18)
                        pass

                    elif la_ == 13:
                        localctx = GameParser.SubsetsExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 383
                        if not self.precpred(self._ctx, 16):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 16)")
                        self.state = 384
                        self.match(GameParser.SUBSETS)
                        self.state = 385
                        self.expression(17)
                        pass

                    elif la_ == 14:
                        localctx = GameParser.AndExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 386
                        if not self.precpred(self._ctx, 15):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 15)")
                        self.state = 387
                        self.match(GameParser.AND)
                        self.state = 388
                        self.expression(16)
                        pass

                    elif la_ == 15:
                        localctx = GameParser.OrExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 389
                        if not self.precpred(self._ctx, 14):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 14)")
                        self.state = 390
                        self.match(GameParser.OR)
                        self.state = 391
                        self.expression(15)
                        pass

                    elif la_ == 16:
                        localctx = GameParser.UnionExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 392
                        if not self.precpred(self._ctx, 13):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 13)")
                        self.state = 393
                        self.match(GameParser.UNION)
                        self.state = 394
                        self.expression(14)
                        pass

                    elif la_ == 17:
                        localctx = GameParser.SetMinusExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 395
                        if not self.precpred(self._ctx, 12):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 12)")
                        self.state = 396
                        self.match(GameParser.BACKSLASH)
                        self.state = 397
                        self.expression(13)
                        pass

                    elif la_ == 18:
                        localctx = GameParser.FnCallExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 398
                        if not self.precpred(self._ctx, 33):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 33)")
                        self.state = 399
                        self.match(GameParser.L_PAREN)
                        self.state = 401
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)
                        if (((_la) & ~0x3f) == 0 and ((1 << _la) & -1872917109810331606) != 0) or ((((_la - 64)) & ~0x3f) == 0 and ((1 << (_la - 64)) & 15) != 0):
                            self.state = 400
                            self.argList()


                        self.state = 403
                        self.match(GameParser.R_PAREN)
                        pass

                    elif la_ == 19:
                        localctx = GameParser.SliceExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 404
                        if not self.precpred(self._ctx, 32):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 32)")
                        self.state = 405
                        self.match(GameParser.L_SQUARE)
                        self.state = 406
                        self.integerExpression(0)
                        self.state = 407
                        self.match(GameParser.COLON)
                        self.state = 408
                        self.integerExpression(0)
                        self.state = 409
                        self.match(GameParser.R_SQUARE)
                        pass

             
                self.state = 415
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
            self.state = 416
            self.expression(0)
            self.state = 421
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==11:
                self.state = 417
                self.match(GameParser.COMMA)
                self.state = 418
                self.expression(0)
                self.state = 423
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
            self.state = 424
            self.type_(0)
            self.state = 425
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
        self.enterRule(localctx, 34, self.RULE_parameterizedGame)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 427
            self.id_()
            self.state = 428
            self.match(GameParser.L_PAREN)
            self.state = 430
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & -1872917109810331606) != 0) or ((((_la - 64)) & ~0x3f) == 0 and ((1 << (_la - 64)) & 15) != 0):
                self.state = 429
                self.argList()


            self.state = 432
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
        _startState = 36
        self.enterRecursionRule(localctx, 36, self.RULE_type, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 475
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,33,self._ctx)
            if la_ == 1:
                localctx = GameParser.SetTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 435
                self.set_()
                pass

            elif la_ == 2:
                localctx = GameParser.BoolTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 436
                self.match(GameParser.BOOL)
                pass

            elif la_ == 3:
                localctx = GameParser.VoidTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 437
                self.match(GameParser.VOID)
                pass

            elif la_ == 4:
                localctx = GameParser.MapTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 438
                self.match(GameParser.MAP)
                self.state = 439
                self.match(GameParser.L_ANGLE)
                self.state = 440
                self.type_(0)
                self.state = 441
                self.match(GameParser.COMMA)
                self.state = 442
                self.type_(0)
                self.state = 443
                self.match(GameParser.R_ANGLE)
                pass

            elif la_ == 5:
                localctx = GameParser.ArrayTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 445
                self.match(GameParser.ARRAY)
                self.state = 446
                self.match(GameParser.L_ANGLE)
                self.state = 447
                self.type_(0)
                self.state = 448
                self.match(GameParser.COMMA)
                self.state = 449
                self.integerExpression(0)
                self.state = 450
                self.match(GameParser.R_ANGLE)
                pass

            elif la_ == 6:
                localctx = GameParser.FunctionTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 452
                self.match(GameParser.FUNCTION)
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

            elif la_ == 7:
                localctx = GameParser.IntTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 459
                self.match(GameParser.INTTYPE)
                pass

            elif la_ == 8:
                localctx = GameParser.ProductTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 460
                self.match(GameParser.L_SQUARE)
                self.state = 461
                self.type_(0)
                self.state = 464 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 462
                    self.match(GameParser.COMMA)
                    self.state = 463
                    self.type_(0)
                    self.state = 466 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==11):
                        break

                self.state = 468
                self.match(GameParser.R_SQUARE)
                pass

            elif la_ == 9:
                localctx = GameParser.BitStringTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 470
                self.bitstring()
                pass

            elif la_ == 10:
                localctx = GameParser.ModIntTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 471
                self.modint()
                pass

            elif la_ == 11:
                localctx = GameParser.GroupElemTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 472
                self.groupelem()
                pass

            elif la_ == 12:
                localctx = GameParser.GroupTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 473
                self.match(GameParser.GROUP)
                pass

            elif la_ == 13:
                localctx = GameParser.LvalueTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 474
                self.lvalue()
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 481
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,34,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = GameParser.OptionalTypeContext(self, GameParser.TypeContext(self, _parentctx, _parentState))
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_type)
                    self.state = 477
                    if not self.precpred(self._ctx, 14):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 14)")
                    self.state = 478
                    self.match(GameParser.QUESTION) 
                self.state = 483
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
            self.state = 492
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [40, 41, 49, 58, 67]:
                self.state = 485
                self.lvalue()
                pass
            elif token in [66]:
                self.state = 486
                self.match(GameParser.INT)
                pass
            elif token in [63]:
                self.state = 487
                self.match(GameParser.BINARYNUM)
                pass
            elif token in [5]:
                self.state = 488
                self.match(GameParser.L_PAREN)
                self.state = 489
                self.integerExpression(0)
                self.state = 490
                self.match(GameParser.R_PAREN)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 508
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,37,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 506
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,36,self._ctx)
                    if la_ == 1:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 494
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 8)")
                        self.state = 495
                        self.match(GameParser.TIMES)
                        self.state = 496
                        self.integerExpression(9)
                        pass

                    elif la_ == 2:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 497
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 7)")
                        self.state = 498
                        self.match(GameParser.DIVIDE)
                        self.state = 499
                        self.integerExpression(8)
                        pass

                    elif la_ == 3:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 500
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 6)")
                        self.state = 501
                        self.match(GameParser.PLUS)
                        self.state = 502
                        self.integerExpression(7)
                        pass

                    elif la_ == 4:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 503
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 5)")
                        self.state = 504
                        self.match(GameParser.SUBTRACT)
                        self.state = 505
                        self.integerExpression(6)
                        pass

             
                self.state = 510
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
            self.state = 517
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [40, 41, 49, 58, 67]:
                self.enterOuterAlt(localctx, 1)
                self.state = 511
                self.lvalue()
                pass
            elif token in [66]:
                self.enterOuterAlt(localctx, 2)
                self.state = 512
                self.match(GameParser.INT)
                pass
            elif token in [5]:
                self.enterOuterAlt(localctx, 3)
                self.state = 513
                self.match(GameParser.L_PAREN)
                self.state = 514
                self.integerExpression(0)
                self.state = 515
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
            self.state = 525
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,39,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 519
                self.match(GameParser.BITSTRING)
                self.state = 520
                self.match(GameParser.L_ANGLE)
                self.state = 521
                self.integerExpression(0)
                self.state = 522
                self.match(GameParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 524
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
            self.state = 527
            self.match(GameParser.MODINT)
            self.state = 528
            self.match(GameParser.L_ANGLE)
            self.state = 529
            self.integerExpression(0)
            self.state = 530
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
        self.enterRule(localctx, 46, self.RULE_groupelem)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 532
            self.match(GameParser.GROUPELEM)
            self.state = 533
            self.match(GameParser.L_ANGLE)
            self.state = 534
            self.lvalue()
            self.state = 535
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
        self.enterRule(localctx, 48, self.RULE_set)
        try:
            self.state = 543
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,40,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 537
                self.match(GameParser.SET)
                self.state = 538
                self.match(GameParser.L_ANGLE)
                self.state = 539
                self.type_(0)
                self.state = 540
                self.match(GameParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 542
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
        self.enterRule(localctx, 50, self.RULE_bool)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 545
            _la = self._input.LA(1)
            if not(_la==61 or _la==62):
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
        self.enterRule(localctx, 52, self.RULE_moduleImport)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 547
            self.match(GameParser.IMPORT)
            self.state = 548
            self.match(GameParser.FILESTRING)
            self.state = 551
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==53:
                self.state = 549
                self.match(GameParser.AS)
                self.state = 550
                self.match(GameParser.ID)


            self.state = 553
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
        self.enterRule(localctx, 54, self.RULE_id)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 555
            _la = self._input.LA(1)
            if not(((((_la - 40)) & ~0x3f) == 0 and ((1 << (_la - 40)) & 134218243) != 0)):
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
         




