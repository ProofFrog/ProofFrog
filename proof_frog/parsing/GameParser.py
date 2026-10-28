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
        4,1,70,570,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,1,0,5,0,58,8,0,10,0,12,0,61,9,0,1,0,1,0,1,0,3,0,66,8,0,
        1,0,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,2,1,2,1,2,1,2,1,2,1,3,1,3,1,3,
        1,3,3,3,85,8,3,1,3,1,3,1,3,1,3,1,3,1,4,1,4,1,4,5,4,95,8,4,10,4,12,
        4,98,9,4,1,4,4,4,101,8,4,11,4,12,4,102,1,5,1,5,1,5,3,5,108,8,5,1,
        6,1,6,1,6,1,6,1,7,1,7,1,7,1,8,1,8,5,8,119,8,8,10,8,12,8,122,9,8,
        1,8,1,8,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,
        1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,4,9,
        155,8,9,11,9,12,9,156,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,4,
        9,169,8,9,11,9,12,9,170,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,
        1,9,1,9,4,9,185,8,9,11,9,12,9,186,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,
        9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,
        9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,
        9,1,9,1,9,3,9,231,8,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,
        9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,5,9,252,8,9,10,9,12,9,255,9,9,
        1,9,1,9,3,9,259,8,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,
        1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,3,9,281,8,9,1,10,1,10,1,10,3,
        10,286,8,10,1,10,1,10,1,10,1,10,1,10,1,10,5,10,294,8,10,10,10,12,
        10,297,9,10,1,11,1,11,1,12,5,12,302,8,12,10,12,12,12,305,9,12,1,
        12,1,12,1,12,1,12,3,12,311,8,12,1,12,1,12,1,13,1,13,1,13,5,13,318,
        8,13,10,13,12,13,321,9,13,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,
        1,14,1,14,1,14,1,14,1,14,1,14,5,14,337,8,14,10,14,12,14,340,9,14,
        3,14,342,8,14,1,14,1,14,1,14,1,14,1,14,5,14,349,8,14,10,14,12,14,
        352,9,14,3,14,354,8,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,
        14,1,14,1,14,1,14,1,14,1,14,3,14,370,8,14,1,14,1,14,1,14,1,14,1,
        14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,
        14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,
        14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,14,1,
        14,1,14,1,14,1,14,1,14,3,14,420,8,14,1,14,1,14,1,14,1,14,1,14,1,
        14,1,14,1,14,5,14,430,8,14,10,14,12,14,433,9,14,1,15,1,15,1,15,5,
        15,438,8,15,10,15,12,15,441,9,15,1,16,1,16,1,16,1,17,1,17,1,17,3,
        17,449,8,17,1,17,1,17,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,
        18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,
        18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,1,18,4,18,483,8,18,11,18,12,
        18,484,1,18,1,18,1,18,1,18,1,18,1,18,1,18,3,18,494,8,18,1,18,1,18,
        5,18,498,8,18,10,18,12,18,501,9,18,1,19,1,19,1,19,1,19,1,19,1,19,
        1,19,1,19,3,19,511,8,19,1,19,1,19,1,19,1,19,1,19,1,19,5,19,519,8,
        19,10,19,12,19,522,9,19,1,20,1,20,1,20,1,20,1,20,1,20,3,20,530,8,
        20,1,21,1,21,1,21,1,21,1,21,1,21,3,21,538,8,21,1,22,1,22,1,22,1,
        22,1,22,1,23,1,23,1,23,1,23,1,23,1,24,1,24,1,24,1,24,1,24,1,24,3,
        24,556,8,24,1,25,1,25,1,26,1,26,1,26,1,26,3,26,564,8,26,1,26,1,26,
        1,27,1,27,1,27,0,3,28,36,38,28,0,2,4,6,8,10,12,14,16,18,20,22,24,
        26,28,30,32,34,36,38,40,42,44,46,48,50,52,54,0,6,2,0,8,8,23,23,1,
        0,58,59,2,0,14,14,18,18,1,0,16,17,1,0,60,61,3,0,41,42,50,50,66,66,
        638,0,59,1,0,0,0,2,70,1,0,0,0,4,75,1,0,0,0,6,80,1,0,0,0,8,96,1,0,
        0,0,10,104,1,0,0,0,12,109,1,0,0,0,14,113,1,0,0,0,16,116,1,0,0,0,
        18,280,1,0,0,0,20,285,1,0,0,0,22,298,1,0,0,0,24,303,1,0,0,0,26,314,
        1,0,0,0,28,369,1,0,0,0,30,434,1,0,0,0,32,442,1,0,0,0,34,445,1,0,
        0,0,36,493,1,0,0,0,38,510,1,0,0,0,40,529,1,0,0,0,42,537,1,0,0,0,
        44,539,1,0,0,0,46,544,1,0,0,0,48,555,1,0,0,0,50,557,1,0,0,0,52,559,
        1,0,0,0,54,567,1,0,0,0,56,58,3,52,26,0,57,56,1,0,0,0,58,61,1,0,0,
        0,59,57,1,0,0,0,59,60,1,0,0,0,60,62,1,0,0,0,61,59,1,0,0,0,62,63,
        3,6,3,0,63,65,3,6,3,0,64,66,3,2,1,0,65,64,1,0,0,0,65,66,1,0,0,0,
        66,67,1,0,0,0,67,68,3,4,2,0,68,69,5,0,0,1,69,1,1,0,0,0,70,71,5,1,
        0,0,71,72,7,0,0,0,72,73,3,28,14,0,73,74,5,10,0,0,74,3,1,0,0,0,75,
        76,5,53,0,0,76,77,5,54,0,0,77,78,3,54,27,0,78,79,5,10,0,0,79,5,1,
        0,0,0,80,81,5,52,0,0,81,82,3,54,27,0,82,84,5,6,0,0,83,85,3,26,13,
        0,84,83,1,0,0,0,84,85,1,0,0,0,85,86,1,0,0,0,86,87,5,7,0,0,87,88,
        5,2,0,0,88,89,3,8,4,0,89,90,5,3,0,0,90,7,1,0,0,0,91,92,3,10,5,0,
        92,93,5,10,0,0,93,95,1,0,0,0,94,91,1,0,0,0,95,98,1,0,0,0,96,94,1,
        0,0,0,96,97,1,0,0,0,97,100,1,0,0,0,98,96,1,0,0,0,99,101,3,14,7,0,
        100,99,1,0,0,0,101,102,1,0,0,0,102,100,1,0,0,0,102,103,1,0,0,0,103,
        9,1,0,0,0,104,107,3,32,16,0,105,106,5,15,0,0,106,108,3,28,14,0,107,
        105,1,0,0,0,107,108,1,0,0,0,108,11,1,0,0,0,109,110,3,32,16,0,110,
        111,5,15,0,0,111,112,3,28,14,0,112,13,1,0,0,0,113,114,3,24,12,0,
        114,115,3,16,8,0,115,15,1,0,0,0,116,120,5,2,0,0,117,119,3,18,9,0,
        118,117,1,0,0,0,119,122,1,0,0,0,120,118,1,0,0,0,120,121,1,0,0,0,
        121,123,1,0,0,0,122,120,1,0,0,0,123,124,5,3,0,0,124,17,1,0,0,0,125,
        126,3,36,18,0,126,127,3,54,27,0,127,128,5,10,0,0,128,281,1,0,0,0,
        129,130,3,36,18,0,130,131,3,20,10,0,131,132,5,15,0,0,132,133,3,28,
        14,0,133,134,5,10,0,0,134,281,1,0,0,0,135,136,3,36,18,0,136,137,
        3,20,10,0,137,138,5,26,0,0,138,139,3,28,14,0,139,140,5,28,0,0,140,
        141,3,28,14,0,141,142,5,10,0,0,142,281,1,0,0,0,143,144,3,36,18,0,
        144,145,3,20,10,0,145,146,5,26,0,0,146,147,3,28,14,0,147,148,5,10,
        0,0,148,281,1,0,0,0,149,150,3,36,18,0,150,151,5,4,0,0,151,154,3,
        54,27,0,152,153,5,12,0,0,153,155,3,54,27,0,154,152,1,0,0,0,155,156,
        1,0,0,0,156,154,1,0,0,0,156,157,1,0,0,0,157,158,1,0,0,0,158,159,
        5,5,0,0,159,160,5,15,0,0,160,161,3,28,14,0,161,162,5,10,0,0,162,
        281,1,0,0,0,163,164,3,36,18,0,164,165,5,4,0,0,165,168,3,54,27,0,
        166,167,5,12,0,0,167,169,3,54,27,0,168,166,1,0,0,0,169,170,1,0,0,
        0,170,168,1,0,0,0,170,171,1,0,0,0,171,172,1,0,0,0,172,173,5,5,0,
        0,173,174,5,26,0,0,174,175,3,28,14,0,175,176,5,28,0,0,176,177,3,
        28,14,0,177,178,5,10,0,0,178,281,1,0,0,0,179,180,3,36,18,0,180,181,
        5,4,0,0,181,184,3,54,27,0,182,183,5,12,0,0,183,185,3,54,27,0,184,
        182,1,0,0,0,185,186,1,0,0,0,186,184,1,0,0,0,186,187,1,0,0,0,187,
        188,1,0,0,0,188,189,5,5,0,0,189,190,5,26,0,0,190,191,3,28,14,0,191,
        192,5,10,0,0,192,281,1,0,0,0,193,194,3,20,10,0,194,195,5,15,0,0,
        195,196,3,28,14,0,196,197,5,10,0,0,197,281,1,0,0,0,198,199,3,20,
        10,0,199,200,5,26,0,0,200,201,3,28,14,0,201,202,5,28,0,0,202,203,
        3,28,14,0,203,204,5,10,0,0,204,281,1,0,0,0,205,206,3,20,10,0,206,
        207,5,26,0,0,207,208,3,28,14,0,208,209,5,10,0,0,209,281,1,0,0,0,
        210,211,3,36,18,0,211,212,3,20,10,0,212,213,5,25,0,0,213,214,5,4,
        0,0,214,215,3,28,14,0,215,216,5,5,0,0,216,217,3,36,18,0,217,218,
        5,10,0,0,218,281,1,0,0,0,219,220,3,20,10,0,220,221,5,25,0,0,221,
        222,5,4,0,0,222,223,3,28,14,0,223,224,5,5,0,0,224,225,3,36,18,0,
        225,226,5,10,0,0,226,281,1,0,0,0,227,228,3,28,14,0,228,230,5,6,0,
        0,229,231,3,30,15,0,230,229,1,0,0,0,230,231,1,0,0,0,231,232,1,0,
        0,0,232,233,5,7,0,0,233,234,5,10,0,0,234,281,1,0,0,0,235,236,5,37,
        0,0,236,237,3,28,14,0,237,238,5,10,0,0,238,281,1,0,0,0,239,240,5,
        47,0,0,240,241,5,6,0,0,241,242,3,28,14,0,242,243,5,7,0,0,243,253,
        3,16,8,0,244,245,5,55,0,0,245,246,5,47,0,0,246,247,5,6,0,0,247,248,
        3,28,14,0,248,249,5,7,0,0,249,250,3,16,8,0,250,252,1,0,0,0,251,244,
        1,0,0,0,252,255,1,0,0,0,253,251,1,0,0,0,253,254,1,0,0,0,254,258,
        1,0,0,0,255,253,1,0,0,0,256,257,5,55,0,0,257,259,3,16,8,0,258,256,
        1,0,0,0,258,259,1,0,0,0,259,281,1,0,0,0,260,261,5,48,0,0,261,262,
        5,6,0,0,262,263,5,35,0,0,263,264,3,54,27,0,264,265,5,15,0,0,265,
        266,3,28,14,0,266,267,5,49,0,0,267,268,3,28,14,0,268,269,5,7,0,0,
        269,270,3,16,8,0,270,281,1,0,0,0,271,272,5,48,0,0,272,273,5,6,0,
        0,273,274,3,36,18,0,274,275,3,54,27,0,275,276,5,50,0,0,276,277,3,
        28,14,0,277,278,5,7,0,0,278,279,3,16,8,0,279,281,1,0,0,0,280,125,
        1,0,0,0,280,129,1,0,0,0,280,135,1,0,0,0,280,143,1,0,0,0,280,149,
        1,0,0,0,280,163,1,0,0,0,280,179,1,0,0,0,280,193,1,0,0,0,280,198,
        1,0,0,0,280,205,1,0,0,0,280,210,1,0,0,0,280,219,1,0,0,0,280,227,
        1,0,0,0,280,235,1,0,0,0,280,239,1,0,0,0,280,260,1,0,0,0,280,271,
        1,0,0,0,281,19,1,0,0,0,282,286,3,54,27,0,283,286,3,34,17,0,284,286,
        5,57,0,0,285,282,1,0,0,0,285,283,1,0,0,0,285,284,1,0,0,0,286,295,
        1,0,0,0,287,288,5,13,0,0,288,294,3,54,27,0,289,290,5,4,0,0,290,291,
        3,28,14,0,291,292,5,5,0,0,292,294,1,0,0,0,293,287,1,0,0,0,293,289,
        1,0,0,0,294,297,1,0,0,0,295,293,1,0,0,0,295,296,1,0,0,0,296,21,1,
        0,0,0,297,295,1,0,0,0,298,299,7,1,0,0,299,23,1,0,0,0,300,302,3,22,
        11,0,301,300,1,0,0,0,302,305,1,0,0,0,303,301,1,0,0,0,303,304,1,0,
        0,0,304,306,1,0,0,0,305,303,1,0,0,0,306,307,3,36,18,0,307,308,3,
        54,27,0,308,310,5,6,0,0,309,311,3,26,13,0,310,309,1,0,0,0,310,311,
        1,0,0,0,311,312,1,0,0,0,312,313,5,7,0,0,313,25,1,0,0,0,314,319,3,
        32,16,0,315,316,5,12,0,0,316,318,3,32,16,0,317,315,1,0,0,0,318,321,
        1,0,0,0,319,317,1,0,0,0,319,320,1,0,0,0,320,27,1,0,0,0,321,319,1,
        0,0,0,322,323,6,14,-1,0,323,324,5,29,0,0,324,370,3,28,14,29,325,
        326,5,31,0,0,326,327,3,28,14,0,327,328,5,31,0,0,328,370,1,0,0,0,
        329,330,5,17,0,0,330,370,3,28,14,25,331,370,3,20,10,0,332,341,5,
        4,0,0,333,338,3,28,14,0,334,335,5,12,0,0,335,337,3,28,14,0,336,334,
        1,0,0,0,337,340,1,0,0,0,338,336,1,0,0,0,338,339,1,0,0,0,339,342,
        1,0,0,0,340,338,1,0,0,0,341,333,1,0,0,0,341,342,1,0,0,0,342,343,
        1,0,0,0,343,370,5,5,0,0,344,353,5,2,0,0,345,350,3,28,14,0,346,347,
        5,12,0,0,347,349,3,28,14,0,348,346,1,0,0,0,349,352,1,0,0,0,350,348,
        1,0,0,0,350,351,1,0,0,0,351,354,1,0,0,0,352,350,1,0,0,0,353,345,
        1,0,0,0,353,354,1,0,0,0,354,355,1,0,0,0,355,370,5,3,0,0,356,370,
        3,36,18,0,357,358,5,63,0,0,358,370,3,40,20,0,359,360,5,64,0,0,360,
        370,3,40,20,0,361,370,5,62,0,0,362,370,5,65,0,0,363,370,3,50,25,
        0,364,370,5,56,0,0,365,366,5,6,0,0,366,367,3,28,14,0,367,368,5,7,
        0,0,368,370,1,0,0,0,369,322,1,0,0,0,369,325,1,0,0,0,369,329,1,0,
        0,0,369,331,1,0,0,0,369,332,1,0,0,0,369,344,1,0,0,0,369,356,1,0,
        0,0,369,357,1,0,0,0,369,359,1,0,0,0,369,361,1,0,0,0,369,362,1,0,
        0,0,369,363,1,0,0,0,369,364,1,0,0,0,369,365,1,0,0,0,370,431,1,0,
        0,0,371,372,10,27,0,0,372,373,5,30,0,0,373,430,3,28,14,27,374,375,
        10,26,0,0,375,376,7,2,0,0,376,430,3,28,14,27,377,378,10,24,0,0,378,
        379,7,3,0,0,379,430,3,28,14,25,380,381,10,23,0,0,381,382,5,20,0,
        0,382,430,3,28,14,24,383,384,10,22,0,0,384,385,5,21,0,0,385,430,
        3,28,14,23,386,387,10,21,0,0,387,388,5,9,0,0,388,430,3,28,14,22,
        389,390,10,20,0,0,390,391,5,8,0,0,391,430,3,28,14,21,392,393,10,
        19,0,0,393,394,5,22,0,0,394,430,3,28,14,20,395,396,10,18,0,0,396,
        397,5,23,0,0,397,430,3,28,14,19,398,399,10,17,0,0,399,400,5,50,0,
        0,400,430,3,28,14,18,401,402,10,16,0,0,402,403,5,46,0,0,403,430,
        3,28,14,17,404,405,10,15,0,0,405,406,5,27,0,0,406,430,3,28,14,16,
        407,408,10,14,0,0,408,409,5,24,0,0,409,430,3,28,14,15,410,411,10,
        13,0,0,411,412,5,51,0,0,412,430,3,28,14,14,413,414,10,12,0,0,414,
        415,5,28,0,0,415,430,3,28,14,13,416,417,10,31,0,0,417,419,5,6,0,
        0,418,420,3,30,15,0,419,418,1,0,0,0,419,420,1,0,0,0,420,421,1,0,
        0,0,421,430,5,7,0,0,422,423,10,30,0,0,423,424,5,4,0,0,424,425,3,
        38,19,0,425,426,5,11,0,0,426,427,3,38,19,0,427,428,5,5,0,0,428,430,
        1,0,0,0,429,371,1,0,0,0,429,374,1,0,0,0,429,377,1,0,0,0,429,380,
        1,0,0,0,429,383,1,0,0,0,429,386,1,0,0,0,429,389,1,0,0,0,429,392,
        1,0,0,0,429,395,1,0,0,0,429,398,1,0,0,0,429,401,1,0,0,0,429,404,
        1,0,0,0,429,407,1,0,0,0,429,410,1,0,0,0,429,413,1,0,0,0,429,416,
        1,0,0,0,429,422,1,0,0,0,430,433,1,0,0,0,431,429,1,0,0,0,431,432,
        1,0,0,0,432,29,1,0,0,0,433,431,1,0,0,0,434,439,3,28,14,0,435,436,
        5,12,0,0,436,438,3,28,14,0,437,435,1,0,0,0,438,441,1,0,0,0,439,437,
        1,0,0,0,439,440,1,0,0,0,440,31,1,0,0,0,441,439,1,0,0,0,442,443,3,
        36,18,0,443,444,3,54,27,0,444,33,1,0,0,0,445,446,3,54,27,0,446,448,
        5,6,0,0,447,449,3,30,15,0,448,447,1,0,0,0,448,449,1,0,0,0,449,450,
        1,0,0,0,450,451,5,7,0,0,451,35,1,0,0,0,452,453,6,18,-1,0,453,494,
        3,48,24,0,454,494,5,33,0,0,455,494,5,34,0,0,456,457,5,36,0,0,457,
        458,5,8,0,0,458,459,3,36,18,0,459,460,5,12,0,0,460,461,3,36,18,0,
        461,462,5,9,0,0,462,494,1,0,0,0,463,464,5,43,0,0,464,465,5,8,0,0,
        465,466,3,36,18,0,466,467,5,12,0,0,467,468,3,38,19,0,468,469,5,9,
        0,0,469,494,1,0,0,0,470,471,5,44,0,0,471,472,5,8,0,0,472,473,3,36,
        18,0,473,474,5,12,0,0,474,475,3,36,18,0,475,476,5,9,0,0,476,494,
        1,0,0,0,477,494,5,35,0,0,478,479,5,4,0,0,479,482,3,36,18,0,480,481,
        5,12,0,0,481,483,3,36,18,0,482,480,1,0,0,0,483,484,1,0,0,0,484,482,
        1,0,0,0,484,485,1,0,0,0,485,486,1,0,0,0,486,487,5,5,0,0,487,494,
        1,0,0,0,488,494,3,42,21,0,489,494,3,44,22,0,490,494,3,46,23,0,491,
        494,5,41,0,0,492,494,3,20,10,0,493,452,1,0,0,0,493,454,1,0,0,0,493,
        455,1,0,0,0,493,456,1,0,0,0,493,463,1,0,0,0,493,470,1,0,0,0,493,
        477,1,0,0,0,493,478,1,0,0,0,493,488,1,0,0,0,493,489,1,0,0,0,493,
        490,1,0,0,0,493,491,1,0,0,0,493,492,1,0,0,0,494,499,1,0,0,0,495,
        496,10,14,0,0,496,498,5,19,0,0,497,495,1,0,0,0,498,501,1,0,0,0,499,
        497,1,0,0,0,499,500,1,0,0,0,500,37,1,0,0,0,501,499,1,0,0,0,502,503,
        6,19,-1,0,503,511,3,20,10,0,504,511,5,65,0,0,505,511,5,62,0,0,506,
        507,5,6,0,0,507,508,3,38,19,0,508,509,5,7,0,0,509,511,1,0,0,0,510,
        502,1,0,0,0,510,504,1,0,0,0,510,505,1,0,0,0,510,506,1,0,0,0,511,
        520,1,0,0,0,512,513,10,6,0,0,513,514,7,2,0,0,514,519,3,38,19,7,515,
        516,10,5,0,0,516,517,7,3,0,0,517,519,3,38,19,6,518,512,1,0,0,0,518,
        515,1,0,0,0,519,522,1,0,0,0,520,518,1,0,0,0,520,521,1,0,0,0,521,
        39,1,0,0,0,522,520,1,0,0,0,523,530,3,20,10,0,524,530,5,65,0,0,525,
        526,5,6,0,0,526,527,3,38,19,0,527,528,5,7,0,0,528,530,1,0,0,0,529,
        523,1,0,0,0,529,524,1,0,0,0,529,525,1,0,0,0,530,41,1,0,0,0,531,532,
        5,39,0,0,532,533,5,8,0,0,533,534,3,38,19,0,534,535,5,9,0,0,535,538,
        1,0,0,0,536,538,5,39,0,0,537,531,1,0,0,0,537,536,1,0,0,0,538,43,
        1,0,0,0,539,540,5,40,0,0,540,541,5,8,0,0,541,542,3,38,19,0,542,543,
        5,9,0,0,543,45,1,0,0,0,544,545,5,42,0,0,545,546,5,8,0,0,546,547,
        3,20,10,0,547,548,5,9,0,0,548,47,1,0,0,0,549,550,5,32,0,0,550,551,
        5,8,0,0,551,552,3,36,18,0,552,553,5,9,0,0,553,556,1,0,0,0,554,556,
        5,32,0,0,555,549,1,0,0,0,555,554,1,0,0,0,556,49,1,0,0,0,557,558,
        7,4,0,0,558,51,1,0,0,0,559,560,5,38,0,0,560,563,5,70,0,0,561,562,
        5,54,0,0,562,564,5,66,0,0,563,561,1,0,0,0,563,564,1,0,0,0,564,565,
        1,0,0,0,565,566,5,10,0,0,566,53,1,0,0,0,567,568,7,5,0,0,568,55,1,
        0,0,0,40,59,65,84,96,102,107,120,156,170,186,230,253,258,280,285,
        293,295,303,310,319,338,341,350,353,369,419,429,431,439,448,484,
        493,499,510,518,520,529,537,555,563
    ]

class GameParser ( Parser ):

    grammarFileName = "Game.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'advantage'", "'{'", "'}'", "'['", "']'", 
                     "'('", "')'", "'<'", "'>'", "';'", "':'", "','", "'.'", 
                     "'*'", "'='", "'+'", "'-'", "'/'", "'?'", "'=='", "'!='", 
                     "'>='", "'<='", "'||'", "'<-uniq'", "'<-'", "'&&'", 
                     "'\\'", "'!'", "'^'", "'|'", "'Set'", "'Bool'", "'Void'", 
                     "'Int'", "'Map'", "'return'", "'import'", "'BitString'", 
                     "'ModInt'", "'Group'", "'GroupElem'", "'Array'", "'Function'", 
                     "'Primitive'", "'subsets'", "'if'", "'for'", "'to'", 
                     "'in'", "'union'", "'Game'", "'export'", "'as'", "'else'", 
                     "'None'", "'this'", "'deterministic'", "'injective'", 
                     "'true'", "'false'", "<INVALID>", "'0^'", "'1^'" ]

    symbolicNames = [ "<INVALID>", "ADVANTAGE", "L_CURLY", "R_CURLY", "L_SQUARE", 
                      "R_SQUARE", "L_PAREN", "R_PAREN", "L_ANGLE", "R_ANGLE", 
                      "SEMI", "COLON", "COMMA", "PERIOD", "TIMES", "EQUALS", 
                      "PLUS", "SUBTRACT", "DIVIDE", "QUESTION", "EQUALSCOMPARE", 
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
    RULE_advantageClause = 1
    RULE_gameExport = 2
    RULE_game = 3
    RULE_gameBody = 4
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

    ruleNames =  [ "program", "advantageClause", "gameExport", "game", "gameBody", 
                   "field", "initializedField", "method", "block", "statement", 
                   "lvalue", "methodModifier", "methodSignature", "paramList", 
                   "expression", "argList", "variable", "parameterizedGame", 
                   "type", "integerExpression", "integerAtom", "bitstring", 
                   "modint", "groupelem", "set", "bool", "moduleImport", 
                   "id" ]

    EOF = Token.EOF
    ADVANTAGE=1
    L_CURLY=2
    R_CURLY=3
    L_SQUARE=4
    R_SQUARE=5
    L_PAREN=6
    R_PAREN=7
    L_ANGLE=8
    R_ANGLE=9
    SEMI=10
    COLON=11
    COMMA=12
    PERIOD=13
    TIMES=14
    EQUALS=15
    PLUS=16
    SUBTRACT=17
    DIVIDE=18
    QUESTION=19
    EQUALSCOMPARE=20
    NOTEQUALS=21
    GEQ=22
    LEQ=23
    OR=24
    SAMPUNIQ=25
    SAMPLES=26
    AND=27
    BACKSLASH=28
    NOT=29
    CARET=30
    VBAR=31
    SET=32
    BOOL=33
    VOID=34
    INTTYPE=35
    MAP=36
    RETURN=37
    IMPORT=38
    BITSTRING=39
    MODINT=40
    GROUP=41
    GROUPELEM=42
    ARRAY=43
    FUNCTION=44
    PRIMITIVE=45
    SUBSETS=46
    IF=47
    FOR=48
    TO=49
    IN=50
    UNION=51
    GAME=52
    EXPORT=53
    AS=54
    ELSE=55
    NONE=56
    THIS=57
    DETERMINISTIC=58
    INJECTIVE=59
    TRUE=60
    FALSE=61
    BINARYNUM=62
    ZEROS_CARET=63
    ONES_CARET=64
    INT=65
    ID=66
    WS=67
    LINE_COMMENT=68
    BLOCK_COMMENT=69
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


        def advantageClause(self):
            return self.getTypedRuleContext(GameParser.AdvantageClauseContext,0)


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
            while _la==38:
                self.state = 56
                self.moduleImport()
                self.state = 61
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 62
            self.game()
            self.state = 63
            self.game()
            self.state = 65
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==1:
                self.state = 64
                self.advantageClause()


            self.state = 67
            self.gameExport()
            self.state = 68
            self.match(GameParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AdvantageClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ADVANTAGE(self):
            return self.getToken(GameParser.ADVANTAGE, 0)

        def expression(self):
            return self.getTypedRuleContext(GameParser.ExpressionContext,0)


        def SEMI(self):
            return self.getToken(GameParser.SEMI, 0)

        def LEQ(self):
            return self.getToken(GameParser.LEQ, 0)

        def L_ANGLE(self):
            return self.getToken(GameParser.L_ANGLE, 0)

        def getRuleIndex(self):
            return GameParser.RULE_advantageClause

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAdvantageClause" ):
                return visitor.visitAdvantageClause(self)
            else:
                return visitor.visitChildren(self)




    def advantageClause(self):

        localctx = GameParser.AdvantageClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_advantageClause)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 70
            self.match(GameParser.ADVANTAGE)
            self.state = 71
            _la = self._input.LA(1)
            if not(_la==8 or _la==23):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 72
            self.expression(0)
            self.state = 73
            self.match(GameParser.SEMI)
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
        self.enterRule(localctx, 4, self.RULE_gameExport)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 75
            self.match(GameParser.EXPORT)
            self.state = 76
            self.match(GameParser.AS)
            self.state = 77
            self.id_()
            self.state = 78
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
        self.enterRule(localctx, 6, self.RULE_game)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 80
            self.match(GameParser.GAME)
            self.state = 81
            self.id_()
            self.state = 82
            self.match(GameParser.L_PAREN)
            self.state = 84
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 4)) & ~0x3f) == 0 and ((1 << (_la - 4)) & 4620765759411322881) != 0):
                self.state = 83
                self.paramList()


            self.state = 86
            self.match(GameParser.R_PAREN)
            self.state = 87
            self.match(GameParser.L_CURLY)
            self.state = 88
            self.gameBody()
            self.state = 89
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
        self.enterRule(localctx, 8, self.RULE_gameBody)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 96
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,3,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 91
                    self.field()
                    self.state = 92
                    self.match(GameParser.SEMI) 
                self.state = 98
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,3,self._ctx)

            self.state = 100 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 99
                self.method()
                self.state = 102 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (((((_la - 4)) & ~0x3f) == 0 and ((1 << (_la - 4)) & 4674808954939768833) != 0)):
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
        self.enterRule(localctx, 10, self.RULE_field)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 104
            self.variable()
            self.state = 107
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==15:
                self.state = 105
                self.match(GameParser.EQUALS)
                self.state = 106
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
            self.state = 109
            self.variable()
            self.state = 110
            self.match(GameParser.EQUALS)
            self.state = 111
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
            self.state = 113
            self.methodSignature()
            self.state = 114
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
            self.state = 116
            self.match(GameParser.L_CURLY)
            self.state = 120
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & -935165702237454252) != 0) or ((((_la - 64)) & ~0x3f) == 0 and ((1 << (_la - 64)) & 7) != 0):
                self.state = 117
                self.statement()
                self.state = 122
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 123
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
        self.enterRule(localctx, 18, self.RULE_statement)
        self._la = 0 # Token type
        try:
            self.state = 280
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,13,self._ctx)
            if la_ == 1:
                localctx = GameParser.VarDeclStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 125
                self.type_(0)
                self.state = 126
                self.id_()
                self.state = 127
                self.match(GameParser.SEMI)
                pass

            elif la_ == 2:
                localctx = GameParser.VarDeclWithValueStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 129
                self.type_(0)
                self.state = 130
                self.lvalue()
                self.state = 131
                self.match(GameParser.EQUALS)
                self.state = 132
                self.expression(0)
                self.state = 133
                self.match(GameParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GameParser.VarDeclWithSampleMinusStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 135
                self.type_(0)
                self.state = 136
                self.lvalue()
                self.state = 137
                self.match(GameParser.SAMPLES)
                self.state = 138
                self.expression(0)
                self.state = 139
                self.match(GameParser.BACKSLASH)
                self.state = 140
                self.expression(0)
                self.state = 141
                self.match(GameParser.SEMI)
                pass

            elif la_ == 4:
                localctx = GameParser.VarDeclWithSampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 143
                self.type_(0)
                self.state = 144
                self.lvalue()
                self.state = 145
                self.match(GameParser.SAMPLES)
                self.state = 146
                self.expression(0)
                self.state = 147
                self.match(GameParser.SEMI)
                pass

            elif la_ == 5:
                localctx = GameParser.DestructuringAssignStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 5)
                self.state = 149
                self.type_(0)
                self.state = 150
                self.match(GameParser.L_SQUARE)
                self.state = 151
                self.id_()
                self.state = 154 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 152
                    self.match(GameParser.COMMA)
                    self.state = 153
                    self.id_()
                    self.state = 156 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==12):
                        break

                self.state = 158
                self.match(GameParser.R_SQUARE)
                self.state = 159
                self.match(GameParser.EQUALS)
                self.state = 160
                self.expression(0)
                self.state = 161
                self.match(GameParser.SEMI)
                pass

            elif la_ == 6:
                localctx = GameParser.DestructuringSampleMinusStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 6)
                self.state = 163
                self.type_(0)
                self.state = 164
                self.match(GameParser.L_SQUARE)
                self.state = 165
                self.id_()
                self.state = 168 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 166
                    self.match(GameParser.COMMA)
                    self.state = 167
                    self.id_()
                    self.state = 170 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==12):
                        break

                self.state = 172
                self.match(GameParser.R_SQUARE)
                self.state = 173
                self.match(GameParser.SAMPLES)
                self.state = 174
                self.expression(0)
                self.state = 175
                self.match(GameParser.BACKSLASH)
                self.state = 176
                self.expression(0)
                self.state = 177
                self.match(GameParser.SEMI)
                pass

            elif la_ == 7:
                localctx = GameParser.DestructuringSampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 7)
                self.state = 179
                self.type_(0)
                self.state = 180
                self.match(GameParser.L_SQUARE)
                self.state = 181
                self.id_()
                self.state = 184 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 182
                    self.match(GameParser.COMMA)
                    self.state = 183
                    self.id_()
                    self.state = 186 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==12):
                        break

                self.state = 188
                self.match(GameParser.R_SQUARE)
                self.state = 189
                self.match(GameParser.SAMPLES)
                self.state = 190
                self.expression(0)
                self.state = 191
                self.match(GameParser.SEMI)
                pass

            elif la_ == 8:
                localctx = GameParser.AssignmentStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 8)
                self.state = 193
                self.lvalue()
                self.state = 194
                self.match(GameParser.EQUALS)
                self.state = 195
                self.expression(0)
                self.state = 196
                self.match(GameParser.SEMI)
                pass

            elif la_ == 9:
                localctx = GameParser.SampleMinusStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 9)
                self.state = 198
                self.lvalue()
                self.state = 199
                self.match(GameParser.SAMPLES)
                self.state = 200
                self.expression(0)
                self.state = 201
                self.match(GameParser.BACKSLASH)
                self.state = 202
                self.expression(0)
                self.state = 203
                self.match(GameParser.SEMI)
                pass

            elif la_ == 10:
                localctx = GameParser.SampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 10)
                self.state = 205
                self.lvalue()
                self.state = 206
                self.match(GameParser.SAMPLES)
                self.state = 207
                self.expression(0)
                self.state = 208
                self.match(GameParser.SEMI)
                pass

            elif la_ == 11:
                localctx = GameParser.UniqueSampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 11)
                self.state = 210
                self.type_(0)
                self.state = 211
                self.lvalue()
                self.state = 212
                self.match(GameParser.SAMPUNIQ)
                self.state = 213
                self.match(GameParser.L_SQUARE)
                self.state = 214
                self.expression(0)
                self.state = 215
                self.match(GameParser.R_SQUARE)
                self.state = 216
                self.type_(0)
                self.state = 217
                self.match(GameParser.SEMI)
                pass

            elif la_ == 12:
                localctx = GameParser.UniqueSampleNoTypeStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 12)
                self.state = 219
                self.lvalue()
                self.state = 220
                self.match(GameParser.SAMPUNIQ)
                self.state = 221
                self.match(GameParser.L_SQUARE)
                self.state = 222
                self.expression(0)
                self.state = 223
                self.match(GameParser.R_SQUARE)
                self.state = 224
                self.type_(0)
                self.state = 225
                self.match(GameParser.SEMI)
                pass

            elif la_ == 13:
                localctx = GameParser.FunctionCallStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 13)
                self.state = 227
                self.expression(0)
                self.state = 228
                self.match(GameParser.L_PAREN)
                self.state = 230
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & -935588052141473708) != 0) or ((((_la - 64)) & ~0x3f) == 0 and ((1 << (_la - 64)) & 7) != 0):
                    self.state = 229
                    self.argList()


                self.state = 232
                self.match(GameParser.R_PAREN)
                self.state = 233
                self.match(GameParser.SEMI)
                pass

            elif la_ == 14:
                localctx = GameParser.ReturnStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 14)
                self.state = 235
                self.match(GameParser.RETURN)
                self.state = 236
                self.expression(0)
                self.state = 237
                self.match(GameParser.SEMI)
                pass

            elif la_ == 15:
                localctx = GameParser.IfStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 15)
                self.state = 239
                self.match(GameParser.IF)
                self.state = 240
                self.match(GameParser.L_PAREN)
                self.state = 241
                self.expression(0)
                self.state = 242
                self.match(GameParser.R_PAREN)
                self.state = 243
                self.block()
                self.state = 253
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,11,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 244
                        self.match(GameParser.ELSE)
                        self.state = 245
                        self.match(GameParser.IF)
                        self.state = 246
                        self.match(GameParser.L_PAREN)
                        self.state = 247
                        self.expression(0)
                        self.state = 248
                        self.match(GameParser.R_PAREN)
                        self.state = 249
                        self.block() 
                    self.state = 255
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,11,self._ctx)

                self.state = 258
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==55:
                    self.state = 256
                    self.match(GameParser.ELSE)
                    self.state = 257
                    self.block()


                pass

            elif la_ == 16:
                localctx = GameParser.NumericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 16)
                self.state = 260
                self.match(GameParser.FOR)
                self.state = 261
                self.match(GameParser.L_PAREN)
                self.state = 262
                self.match(GameParser.INTTYPE)
                self.state = 263
                self.id_()
                self.state = 264
                self.match(GameParser.EQUALS)
                self.state = 265
                self.expression(0)
                self.state = 266
                self.match(GameParser.TO)
                self.state = 267
                self.expression(0)
                self.state = 268
                self.match(GameParser.R_PAREN)
                self.state = 269
                self.block()
                pass

            elif la_ == 17:
                localctx = GameParser.GenericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 17)
                self.state = 271
                self.match(GameParser.FOR)
                self.state = 272
                self.match(GameParser.L_PAREN)
                self.state = 273
                self.type_(0)
                self.state = 274
                self.id_()
                self.state = 275
                self.match(GameParser.IN)
                self.state = 276
                self.expression(0)
                self.state = 277
                self.match(GameParser.R_PAREN)
                self.state = 278
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
            self.state = 285
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                self.state = 282
                self.id_()
                pass

            elif la_ == 2:
                self.state = 283
                self.parameterizedGame()
                pass

            elif la_ == 3:
                self.state = 284
                self.match(GameParser.THIS)
                pass


            self.state = 295
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,16,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 293
                    self._errHandler.sync(self)
                    token = self._input.LA(1)
                    if token in [13]:
                        self.state = 287
                        self.match(GameParser.PERIOD)
                        self.state = 288
                        self.id_()
                        pass
                    elif token in [4]:
                        self.state = 289
                        self.match(GameParser.L_SQUARE)
                        self.state = 290
                        self.expression(0)
                        self.state = 291
                        self.match(GameParser.R_SQUARE)
                        pass
                    else:
                        raise NoViableAltException(self)
             
                self.state = 297
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,16,self._ctx)

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
            self.state = 298
            _la = self._input.LA(1)
            if not(_la==58 or _la==59):
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
            self.state = 303
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==58 or _la==59:
                self.state = 300
                self.methodModifier()
                self.state = 305
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 306
            self.type_(0)
            self.state = 307
            self.id_()
            self.state = 308
            self.match(GameParser.L_PAREN)
            self.state = 310
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if ((((_la - 4)) & ~0x3f) == 0 and ((1 << (_la - 4)) & 4620765759411322881) != 0):
                self.state = 309
                self.paramList()


            self.state = 312
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
            self.state = 314
            self.variable()
            self.state = 319
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==12:
                self.state = 315
                self.match(GameParser.COMMA)
                self.state = 316
                self.variable()
                self.state = 321
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


    class AddSubtractExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.op = None # Token
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def PLUS(self):
            return self.getToken(GameParser.PLUS, 0)
        def SUBTRACT(self):
            return self.getToken(GameParser.SUBTRACT, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAddSubtractExp" ):
                return visitor.visitAddSubtractExp(self)
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


    class MultiplyDivideExpContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a GameParser.ExpressionContext
            super().__init__(parser)
            self.op = None # Token
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(GameParser.ExpressionContext)
            else:
                return self.getTypedRuleContext(GameParser.ExpressionContext,i)

        def TIMES(self):
            return self.getToken(GameParser.TIMES, 0)
        def DIVIDE(self):
            return self.getToken(GameParser.DIVIDE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMultiplyDivideExp" ):
                return visitor.visitMultiplyDivideExp(self)
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
            self.state = 369
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,24,self._ctx)
            if la_ == 1:
                localctx = GameParser.NotExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 323
                self.match(GameParser.NOT)
                self.state = 324
                self.expression(29)
                pass

            elif la_ == 2:
                localctx = GameParser.SizeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 325
                self.match(GameParser.VBAR)
                self.state = 326
                self.expression(0)
                self.state = 327
                self.match(GameParser.VBAR)
                pass

            elif la_ == 3:
                localctx = GameParser.MinusExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 329
                self.match(GameParser.SUBTRACT)
                self.state = 330
                self.expression(25)
                pass

            elif la_ == 4:
                localctx = GameParser.LvalueExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 331
                self.lvalue()
                pass

            elif la_ == 5:
                localctx = GameParser.CreateTupleExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 332
                self.match(GameParser.L_SQUARE)
                self.state = 341
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & -935588052141473708) != 0) or ((((_la - 64)) & ~0x3f) == 0 and ((1 << (_la - 64)) & 7) != 0):
                    self.state = 333
                    self.expression(0)
                    self.state = 338
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==12:
                        self.state = 334
                        self.match(GameParser.COMMA)
                        self.state = 335
                        self.expression(0)
                        self.state = 340
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 343
                self.match(GameParser.R_SQUARE)
                pass

            elif la_ == 6:
                localctx = GameParser.CreateSetExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 344
                self.match(GameParser.L_CURLY)
                self.state = 353
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & -935588052141473708) != 0) or ((((_la - 64)) & ~0x3f) == 0 and ((1 << (_la - 64)) & 7) != 0):
                    self.state = 345
                    self.expression(0)
                    self.state = 350
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==12:
                        self.state = 346
                        self.match(GameParser.COMMA)
                        self.state = 347
                        self.expression(0)
                        self.state = 352
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 355
                self.match(GameParser.R_CURLY)
                pass

            elif la_ == 7:
                localctx = GameParser.TypeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 356
                self.type_(0)
                pass

            elif la_ == 8:
                localctx = GameParser.ZerosExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 357
                self.match(GameParser.ZEROS_CARET)
                self.state = 358
                self.integerAtom()
                pass

            elif la_ == 9:
                localctx = GameParser.OnesExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 359
                self.match(GameParser.ONES_CARET)
                self.state = 360
                self.integerAtom()
                pass

            elif la_ == 10:
                localctx = GameParser.BinaryNumExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 361
                self.match(GameParser.BINARYNUM)
                pass

            elif la_ == 11:
                localctx = GameParser.IntExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 362
                self.match(GameParser.INT)
                pass

            elif la_ == 12:
                localctx = GameParser.BoolExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 363
                self.bool_()
                pass

            elif la_ == 13:
                localctx = GameParser.NoneExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 364
                self.match(GameParser.NONE)
                pass

            elif la_ == 14:
                localctx = GameParser.ParenExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 365
                self.match(GameParser.L_PAREN)
                self.state = 366
                self.expression(0)
                self.state = 367
                self.match(GameParser.R_PAREN)
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 431
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,27,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 429
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,26,self._ctx)
                    if la_ == 1:
                        localctx = GameParser.ExponentiationExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 371
                        if not self.precpred(self._ctx, 27):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 27)")
                        self.state = 372
                        self.match(GameParser.CARET)
                        self.state = 373
                        self.expression(27)
                        pass

                    elif la_ == 2:
                        localctx = GameParser.MultiplyDivideExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 374
                        if not self.precpred(self._ctx, 26):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 26)")
                        self.state = 375
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not(_la==14 or _la==18):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 376
                        self.expression(27)
                        pass

                    elif la_ == 3:
                        localctx = GameParser.AddSubtractExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 377
                        if not self.precpred(self._ctx, 24):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 24)")
                        self.state = 378
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not(_la==16 or _la==17):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 379
                        self.expression(25)
                        pass

                    elif la_ == 4:
                        localctx = GameParser.EqualsExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 380
                        if not self.precpred(self._ctx, 23):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 23)")
                        self.state = 381
                        self.match(GameParser.EQUALSCOMPARE)
                        self.state = 382
                        self.expression(24)
                        pass

                    elif la_ == 5:
                        localctx = GameParser.NotEqualsExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 383
                        if not self.precpred(self._ctx, 22):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 22)")
                        self.state = 384
                        self.match(GameParser.NOTEQUALS)
                        self.state = 385
                        self.expression(23)
                        pass

                    elif la_ == 6:
                        localctx = GameParser.GtExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 386
                        if not self.precpred(self._ctx, 21):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 21)")
                        self.state = 387
                        self.match(GameParser.R_ANGLE)
                        self.state = 388
                        self.expression(22)
                        pass

                    elif la_ == 7:
                        localctx = GameParser.LtExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 389
                        if not self.precpred(self._ctx, 20):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 20)")
                        self.state = 390
                        self.match(GameParser.L_ANGLE)
                        self.state = 391
                        self.expression(21)
                        pass

                    elif la_ == 8:
                        localctx = GameParser.GeqExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 392
                        if not self.precpred(self._ctx, 19):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 19)")
                        self.state = 393
                        self.match(GameParser.GEQ)
                        self.state = 394
                        self.expression(20)
                        pass

                    elif la_ == 9:
                        localctx = GameParser.LeqExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 395
                        if not self.precpred(self._ctx, 18):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 18)")
                        self.state = 396
                        self.match(GameParser.LEQ)
                        self.state = 397
                        self.expression(19)
                        pass

                    elif la_ == 10:
                        localctx = GameParser.InExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 398
                        if not self.precpred(self._ctx, 17):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 17)")
                        self.state = 399
                        self.match(GameParser.IN)
                        self.state = 400
                        self.expression(18)
                        pass

                    elif la_ == 11:
                        localctx = GameParser.SubsetsExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 401
                        if not self.precpred(self._ctx, 16):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 16)")
                        self.state = 402
                        self.match(GameParser.SUBSETS)
                        self.state = 403
                        self.expression(17)
                        pass

                    elif la_ == 12:
                        localctx = GameParser.AndExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 404
                        if not self.precpred(self._ctx, 15):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 15)")
                        self.state = 405
                        self.match(GameParser.AND)
                        self.state = 406
                        self.expression(16)
                        pass

                    elif la_ == 13:
                        localctx = GameParser.OrExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 407
                        if not self.precpred(self._ctx, 14):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 14)")
                        self.state = 408
                        self.match(GameParser.OR)
                        self.state = 409
                        self.expression(15)
                        pass

                    elif la_ == 14:
                        localctx = GameParser.UnionExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 410
                        if not self.precpred(self._ctx, 13):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 13)")
                        self.state = 411
                        self.match(GameParser.UNION)
                        self.state = 412
                        self.expression(14)
                        pass

                    elif la_ == 15:
                        localctx = GameParser.SetMinusExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 413
                        if not self.precpred(self._ctx, 12):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 12)")
                        self.state = 414
                        self.match(GameParser.BACKSLASH)
                        self.state = 415
                        self.expression(13)
                        pass

                    elif la_ == 16:
                        localctx = GameParser.FnCallExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 416
                        if not self.precpred(self._ctx, 31):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 31)")
                        self.state = 417
                        self.match(GameParser.L_PAREN)
                        self.state = 419
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)
                        if (((_la) & ~0x3f) == 0 and ((1 << _la) & -935588052141473708) != 0) or ((((_la - 64)) & ~0x3f) == 0 and ((1 << (_la - 64)) & 7) != 0):
                            self.state = 418
                            self.argList()


                        self.state = 421
                        self.match(GameParser.R_PAREN)
                        pass

                    elif la_ == 17:
                        localctx = GameParser.SliceExpContext(self, GameParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 422
                        if not self.precpred(self._ctx, 30):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 30)")
                        self.state = 423
                        self.match(GameParser.L_SQUARE)
                        self.state = 424
                        self.integerExpression(0)
                        self.state = 425
                        self.match(GameParser.COLON)
                        self.state = 426
                        self.integerExpression(0)
                        self.state = 427
                        self.match(GameParser.R_SQUARE)
                        pass

             
                self.state = 433
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
        self.enterRule(localctx, 30, self.RULE_argList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 434
            self.expression(0)
            self.state = 439
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==12:
                self.state = 435
                self.match(GameParser.COMMA)
                self.state = 436
                self.expression(0)
                self.state = 441
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
            self.state = 442
            self.type_(0)
            self.state = 443
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
            self.state = 445
            self.id_()
            self.state = 446
            self.match(GameParser.L_PAREN)
            self.state = 448
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & -935588052141473708) != 0) or ((((_la - 64)) & ~0x3f) == 0 and ((1 << (_la - 64)) & 7) != 0):
                self.state = 447
                self.argList()


            self.state = 450
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
            self.state = 493
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,31,self._ctx)
            if la_ == 1:
                localctx = GameParser.SetTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 453
                self.set_()
                pass

            elif la_ == 2:
                localctx = GameParser.BoolTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 454
                self.match(GameParser.BOOL)
                pass

            elif la_ == 3:
                localctx = GameParser.VoidTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 455
                self.match(GameParser.VOID)
                pass

            elif la_ == 4:
                localctx = GameParser.MapTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 456
                self.match(GameParser.MAP)
                self.state = 457
                self.match(GameParser.L_ANGLE)
                self.state = 458
                self.type_(0)
                self.state = 459
                self.match(GameParser.COMMA)
                self.state = 460
                self.type_(0)
                self.state = 461
                self.match(GameParser.R_ANGLE)
                pass

            elif la_ == 5:
                localctx = GameParser.ArrayTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 463
                self.match(GameParser.ARRAY)
                self.state = 464
                self.match(GameParser.L_ANGLE)
                self.state = 465
                self.type_(0)
                self.state = 466
                self.match(GameParser.COMMA)
                self.state = 467
                self.integerExpression(0)
                self.state = 468
                self.match(GameParser.R_ANGLE)
                pass

            elif la_ == 6:
                localctx = GameParser.FunctionTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 470
                self.match(GameParser.FUNCTION)
                self.state = 471
                self.match(GameParser.L_ANGLE)
                self.state = 472
                self.type_(0)
                self.state = 473
                self.match(GameParser.COMMA)
                self.state = 474
                self.type_(0)
                self.state = 475
                self.match(GameParser.R_ANGLE)
                pass

            elif la_ == 7:
                localctx = GameParser.IntTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 477
                self.match(GameParser.INTTYPE)
                pass

            elif la_ == 8:
                localctx = GameParser.ProductTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 478
                self.match(GameParser.L_SQUARE)
                self.state = 479
                self.type_(0)
                self.state = 482 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 480
                    self.match(GameParser.COMMA)
                    self.state = 481
                    self.type_(0)
                    self.state = 484 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==12):
                        break

                self.state = 486
                self.match(GameParser.R_SQUARE)
                pass

            elif la_ == 9:
                localctx = GameParser.BitStringTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 488
                self.bitstring()
                pass

            elif la_ == 10:
                localctx = GameParser.ModIntTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 489
                self.modint()
                pass

            elif la_ == 11:
                localctx = GameParser.GroupElemTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 490
                self.groupelem()
                pass

            elif la_ == 12:
                localctx = GameParser.GroupTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 491
                self.match(GameParser.GROUP)
                pass

            elif la_ == 13:
                localctx = GameParser.LvalueTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 492
                self.lvalue()
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 499
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,32,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = GameParser.OptionalTypeContext(self, GameParser.TypeContext(self, _parentctx, _parentState))
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_type)
                    self.state = 495
                    if not self.precpred(self._ctx, 14):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 14)")
                    self.state = 496
                    self.match(GameParser.QUESTION) 
                self.state = 501
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,32,self._ctx)

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
            self.op = None # Token

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
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 510
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [41, 42, 50, 57, 66]:
                self.state = 503
                self.lvalue()
                pass
            elif token in [65]:
                self.state = 504
                self.match(GameParser.INT)
                pass
            elif token in [62]:
                self.state = 505
                self.match(GameParser.BINARYNUM)
                pass
            elif token in [6]:
                self.state = 506
                self.match(GameParser.L_PAREN)
                self.state = 507
                self.integerExpression(0)
                self.state = 508
                self.match(GameParser.R_PAREN)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 520
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,35,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 518
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,34,self._ctx)
                    if la_ == 1:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 512
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 6)")
                        self.state = 513
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not(_la==14 or _la==18):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 514
                        self.integerExpression(7)
                        pass

                    elif la_ == 2:
                        localctx = GameParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 515
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 5)")
                        self.state = 516
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not(_la==16 or _la==17):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 517
                        self.integerExpression(6)
                        pass

             
                self.state = 522
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,35,self._ctx)

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
            self.state = 529
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [41, 42, 50, 57, 66]:
                self.enterOuterAlt(localctx, 1)
                self.state = 523
                self.lvalue()
                pass
            elif token in [65]:
                self.enterOuterAlt(localctx, 2)
                self.state = 524
                self.match(GameParser.INT)
                pass
            elif token in [6]:
                self.enterOuterAlt(localctx, 3)
                self.state = 525
                self.match(GameParser.L_PAREN)
                self.state = 526
                self.integerExpression(0)
                self.state = 527
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
            self.state = 537
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,37,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 531
                self.match(GameParser.BITSTRING)
                self.state = 532
                self.match(GameParser.L_ANGLE)
                self.state = 533
                self.integerExpression(0)
                self.state = 534
                self.match(GameParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 536
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
            self.state = 539
            self.match(GameParser.MODINT)
            self.state = 540
            self.match(GameParser.L_ANGLE)
            self.state = 541
            self.integerExpression(0)
            self.state = 542
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
            self.state = 544
            self.match(GameParser.GROUPELEM)
            self.state = 545
            self.match(GameParser.L_ANGLE)
            self.state = 546
            self.lvalue()
            self.state = 547
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
            self.state = 555
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,38,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 549
                self.match(GameParser.SET)
                self.state = 550
                self.match(GameParser.L_ANGLE)
                self.state = 551
                self.type_(0)
                self.state = 552
                self.match(GameParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 554
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
            self.state = 557
            _la = self._input.LA(1)
            if not(_la==60 or _la==61):
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
            self.state = 559
            self.match(GameParser.IMPORT)
            self.state = 560
            self.match(GameParser.FILESTRING)
            self.state = 563
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==54:
                self.state = 561
                self.match(GameParser.AS)
                self.state = 562
                self.match(GameParser.ID)


            self.state = 565
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
            self.state = 567
            _la = self._input.LA(1)
            if not(((((_la - 41)) & ~0x3f) == 0 and ((1 << (_la - 41)) & 33554947) != 0)):
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
                return self.precpred(self._ctx, 27)
         

            if predIndex == 1:
                return self.precpred(self._ctx, 26)
         

            if predIndex == 2:
                return self.precpred(self._ctx, 24)
         

            if predIndex == 3:
                return self.precpred(self._ctx, 23)
         

            if predIndex == 4:
                return self.precpred(self._ctx, 22)
         

            if predIndex == 5:
                return self.precpred(self._ctx, 21)
         

            if predIndex == 6:
                return self.precpred(self._ctx, 20)
         

            if predIndex == 7:
                return self.precpred(self._ctx, 19)
         

            if predIndex == 8:
                return self.precpred(self._ctx, 18)
         

            if predIndex == 9:
                return self.precpred(self._ctx, 17)
         

            if predIndex == 10:
                return self.precpred(self._ctx, 16)
         

            if predIndex == 11:
                return self.precpred(self._ctx, 15)
         

            if predIndex == 12:
                return self.precpred(self._ctx, 14)
         

            if predIndex == 13:
                return self.precpred(self._ctx, 13)
         

            if predIndex == 14:
                return self.precpred(self._ctx, 12)
         

            if predIndex == 15:
                return self.precpred(self._ctx, 31)
         

            if predIndex == 16:
                return self.precpred(self._ctx, 30)
         

    def type_sempred(self, localctx:TypeContext, predIndex:int):
            if predIndex == 17:
                return self.precpred(self._ctx, 14)
         

    def integerExpression_sempred(self, localctx:IntegerExpressionContext, predIndex:int):
            if predIndex == 18:
                return self.precpred(self._ctx, 6)
         

            if predIndex == 19:
                return self.precpred(self._ctx, 5)
         




