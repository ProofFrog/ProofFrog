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
        4,1,84,730,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,2,33,
        7,33,2,34,7,34,2,35,7,35,2,36,7,36,2,37,7,37,2,38,7,38,2,39,7,39,
        2,40,7,40,2,41,7,41,2,42,7,42,1,0,5,0,88,8,0,10,0,12,0,91,9,0,1,
        0,1,0,1,0,1,0,1,1,1,1,5,1,99,8,1,10,1,12,1,102,9,1,1,2,1,2,1,2,1,
        2,3,2,108,8,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,3,1,3,1,3,1,
        3,1,3,3,3,124,8,3,1,3,1,3,1,3,3,3,129,8,3,1,3,1,3,1,3,3,3,134,8,
        3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,4,1,4,1,4,5,4,146,8,4,10,4,12,4,
        149,9,4,1,5,1,5,1,5,1,5,1,5,3,5,156,8,5,1,6,1,6,1,6,5,6,161,8,6,
        10,6,12,6,164,9,6,1,6,1,6,1,6,1,6,1,6,3,6,171,8,6,1,7,5,7,174,8,
        7,10,7,12,7,177,9,7,1,8,1,8,1,8,1,8,1,8,1,9,1,9,1,9,1,10,1,10,1,
        10,1,10,1,10,1,10,1,10,5,10,194,8,10,10,10,12,10,197,9,10,1,11,1,
        11,1,11,1,11,1,11,1,11,1,11,1,11,3,11,207,8,11,1,11,1,11,1,11,3,
        11,212,8,11,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,12,1,
        12,1,12,1,13,1,13,1,13,1,13,1,14,1,14,3,14,232,8,14,1,14,1,14,1,
        14,1,15,1,15,1,15,1,15,1,16,1,16,1,16,1,16,1,17,1,17,1,17,1,17,3,
        17,249,8,17,1,17,1,17,1,17,1,17,1,17,1,18,1,18,1,18,5,18,259,8,18,
        10,18,12,18,262,9,18,1,18,4,18,265,8,18,11,18,12,18,266,1,18,1,18,
        1,18,5,18,272,8,18,10,18,12,18,275,9,18,1,18,5,18,278,8,18,10,18,
        12,18,281,9,18,1,18,4,18,284,8,18,11,18,12,18,285,3,18,288,8,18,
        1,19,1,19,1,19,4,19,293,8,19,11,19,12,19,294,1,19,1,19,1,19,1,19,
        1,19,1,19,5,19,303,8,19,10,19,12,19,306,9,19,1,19,1,19,1,19,1,19,
        1,20,1,20,1,20,3,20,315,8,20,1,21,1,21,1,21,1,21,1,22,1,22,1,22,
        1,23,1,23,5,23,326,8,23,10,23,12,23,329,9,23,1,23,1,23,1,24,1,24,
        1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,
        1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,
        1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,
        1,24,1,24,1,24,1,24,1,24,3,24,379,8,24,1,24,1,24,1,24,1,24,1,24,
        1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,
        1,24,5,24,400,8,24,10,24,12,24,403,9,24,1,24,1,24,3,24,407,8,24,
        1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,1,24,
        1,24,1,24,1,24,1,24,1,24,1,24,1,24,3,24,429,8,24,1,25,1,25,1,25,
        3,25,434,8,25,1,25,1,25,1,25,1,25,1,25,1,25,5,25,442,8,25,10,25,
        12,25,445,9,25,1,26,1,26,1,27,5,27,450,8,27,10,27,12,27,453,9,27,
        1,27,1,27,1,27,1,27,3,27,459,8,27,1,27,1,27,1,28,1,28,1,28,5,28,
        466,8,28,10,28,12,28,469,9,28,1,29,1,29,1,29,1,29,1,29,1,29,1,29,
        1,29,1,29,1,29,1,29,1,29,1,29,1,29,5,29,485,8,29,10,29,12,29,488,
        9,29,3,29,490,8,29,1,29,1,29,1,29,1,29,1,29,5,29,497,8,29,10,29,
        12,29,500,9,29,3,29,502,8,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,
        1,29,1,29,1,29,1,29,1,29,1,29,1,29,3,29,518,8,29,1,29,1,29,1,29,
        1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,
        1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,
        1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,
        1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,3,29,
        574,8,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,1,29,5,29,584,8,29,10,
        29,12,29,587,9,29,1,30,1,30,1,30,5,30,592,8,30,10,30,12,30,595,9,
        30,1,31,1,31,1,31,1,32,1,32,1,32,3,32,603,8,32,1,32,1,32,1,33,1,
        33,1,33,1,33,1,33,1,33,1,33,1,33,1,33,1,33,1,33,1,33,1,33,1,33,1,
        33,1,33,1,33,1,33,1,33,1,33,1,33,1,33,1,33,1,33,1,33,1,33,1,33,1,
        33,1,33,1,33,4,33,637,8,33,11,33,12,33,638,1,33,1,33,1,33,1,33,1,
        33,1,33,1,33,3,33,648,8,33,1,33,1,33,5,33,652,8,33,10,33,12,33,655,
        9,33,1,34,1,34,1,34,1,34,1,34,1,34,1,34,1,34,3,34,665,8,34,1,34,
        1,34,1,34,1,34,1,34,1,34,1,34,1,34,1,34,1,34,1,34,1,34,5,34,679,
        8,34,10,34,12,34,682,9,34,1,35,1,35,1,35,1,35,1,35,1,35,3,35,690,
        8,35,1,36,1,36,1,36,1,36,1,36,1,36,3,36,698,8,36,1,37,1,37,1,37,
        1,37,1,37,1,38,1,38,1,38,1,38,1,38,1,39,1,39,1,39,1,39,1,39,1,39,
        3,39,716,8,39,1,40,1,40,1,41,1,41,1,41,1,41,3,41,724,8,41,1,41,1,
        41,1,42,1,42,1,42,0,3,58,66,68,43,0,2,4,6,8,10,12,14,16,18,20,22,
        24,26,28,30,32,34,36,38,40,42,44,46,48,50,52,54,56,58,60,62,64,66,
        68,70,72,74,76,78,80,82,84,0,4,2,0,21,21,36,36,1,0,73,74,1,0,75,
        76,3,0,54,55,63,63,81,81,801,0,89,1,0,0,0,2,100,1,0,0,0,4,103,1,
        0,0,0,6,118,1,0,0,0,8,147,1,0,0,0,10,155,1,0,0,0,12,162,1,0,0,0,
        14,175,1,0,0,0,16,178,1,0,0,0,18,183,1,0,0,0,20,186,1,0,0,0,22,211,
        1,0,0,0,24,213,1,0,0,0,26,225,1,0,0,0,28,231,1,0,0,0,30,236,1,0,
        0,0,32,240,1,0,0,0,34,244,1,0,0,0,36,287,1,0,0,0,38,289,1,0,0,0,
        40,311,1,0,0,0,42,316,1,0,0,0,44,320,1,0,0,0,46,323,1,0,0,0,48,428,
        1,0,0,0,50,433,1,0,0,0,52,446,1,0,0,0,54,451,1,0,0,0,56,462,1,0,
        0,0,58,517,1,0,0,0,60,588,1,0,0,0,62,596,1,0,0,0,64,599,1,0,0,0,
        66,647,1,0,0,0,68,664,1,0,0,0,70,689,1,0,0,0,72,697,1,0,0,0,74,699,
        1,0,0,0,76,704,1,0,0,0,78,715,1,0,0,0,80,717,1,0,0,0,82,719,1,0,
        0,0,84,727,1,0,0,0,86,88,3,82,41,0,87,86,1,0,0,0,88,91,1,0,0,0,89,
        87,1,0,0,0,89,90,1,0,0,0,90,92,1,0,0,0,91,89,1,0,0,0,92,93,3,2,1,
        0,93,94,3,6,3,0,94,95,5,0,0,1,95,1,1,0,0,0,96,99,3,4,2,0,97,99,3,
        34,17,0,98,96,1,0,0,0,98,97,1,0,0,0,99,102,1,0,0,0,100,98,1,0,0,
        0,100,101,1,0,0,0,101,3,1,0,0,0,102,100,1,0,0,0,103,104,5,1,0,0,
        104,105,3,84,42,0,105,107,5,19,0,0,106,108,3,56,28,0,107,106,1,0,
        0,0,107,108,1,0,0,0,108,109,1,0,0,0,109,110,5,20,0,0,110,111,5,4,
        0,0,111,112,3,64,32,0,112,113,5,2,0,0,113,114,3,32,16,0,114,115,
        5,15,0,0,115,116,3,36,18,0,116,117,5,16,0,0,117,5,1,0,0,0,118,119,
        5,5,0,0,119,123,5,24,0,0,120,121,5,9,0,0,121,122,5,24,0,0,122,124,
        3,8,4,0,123,120,1,0,0,0,123,124,1,0,0,0,124,128,1,0,0,0,125,126,
        5,6,0,0,126,127,5,24,0,0,127,129,3,12,6,0,128,125,1,0,0,0,128,129,
        1,0,0,0,129,133,1,0,0,0,130,131,5,12,0,0,131,132,5,24,0,0,132,134,
        3,14,7,0,133,130,1,0,0,0,133,134,1,0,0,0,134,135,1,0,0,0,135,136,
        5,7,0,0,136,137,5,24,0,0,137,138,3,18,9,0,138,139,5,8,0,0,139,140,
        5,24,0,0,140,141,3,20,10,0,141,7,1,0,0,0,142,143,3,10,5,0,143,144,
        5,23,0,0,144,146,1,0,0,0,145,142,1,0,0,0,146,149,1,0,0,0,147,145,
        1,0,0,0,147,148,1,0,0,0,148,9,1,0,0,0,149,147,1,0,0,0,150,156,3,
        40,20,0,151,152,3,62,31,0,152,153,5,39,0,0,153,154,3,58,29,0,154,
        156,1,0,0,0,155,150,1,0,0,0,155,151,1,0,0,0,156,11,1,0,0,0,157,158,
        3,64,32,0,158,159,5,23,0,0,159,161,1,0,0,0,160,157,1,0,0,0,161,164,
        1,0,0,0,162,160,1,0,0,0,162,163,1,0,0,0,163,170,1,0,0,0,164,162,
        1,0,0,0,165,166,5,10,0,0,166,167,7,0,0,0,167,168,3,58,29,0,168,169,
        5,23,0,0,169,171,1,0,0,0,170,165,1,0,0,0,170,171,1,0,0,0,171,13,
        1,0,0,0,172,174,3,16,8,0,173,172,1,0,0,0,174,177,1,0,0,0,175,173,
        1,0,0,0,175,176,1,0,0,0,176,15,1,0,0,0,177,175,1,0,0,0,178,179,3,
        64,32,0,179,180,5,13,0,0,180,181,5,84,0,0,181,182,5,23,0,0,182,17,
        1,0,0,0,183,184,3,64,32,0,184,185,5,23,0,0,185,19,1,0,0,0,186,187,
        3,22,11,0,187,195,5,23,0,0,188,189,3,22,11,0,189,190,5,23,0,0,190,
        194,1,0,0,0,191,194,3,24,12,0,192,194,3,26,13,0,193,188,1,0,0,0,
        193,191,1,0,0,0,193,192,1,0,0,0,194,197,1,0,0,0,195,193,1,0,0,0,
        195,196,1,0,0,0,196,21,1,0,0,0,197,195,1,0,0,0,198,199,3,30,15,0,
        199,200,5,4,0,0,200,201,3,64,32,0,201,202,5,2,0,0,202,203,3,32,16,
        0,203,212,1,0,0,0,204,207,3,30,15,0,205,207,3,64,32,0,206,204,1,
        0,0,0,206,205,1,0,0,0,207,208,1,0,0,0,208,209,5,2,0,0,209,210,3,
        32,16,0,210,212,1,0,0,0,211,198,1,0,0,0,211,206,1,0,0,0,212,23,1,
        0,0,0,213,214,5,11,0,0,214,215,5,19,0,0,215,216,3,84,42,0,216,217,
        5,14,0,0,217,218,3,68,34,0,218,219,5,62,0,0,219,220,3,68,34,0,220,
        221,5,20,0,0,221,222,5,15,0,0,222,223,3,20,10,0,223,224,5,16,0,0,
        224,25,1,0,0,0,225,226,5,6,0,0,226,227,3,58,29,0,227,228,5,23,0,
        0,228,27,1,0,0,0,229,232,3,30,15,0,230,232,3,64,32,0,231,229,1,0,
        0,0,231,230,1,0,0,0,232,233,1,0,0,0,233,234,5,26,0,0,234,235,3,84,
        42,0,235,29,1,0,0,0,236,237,3,64,32,0,237,238,5,26,0,0,238,239,3,
        84,42,0,239,31,1,0,0,0,240,241,3,64,32,0,241,242,5,26,0,0,242,243,
        5,3,0,0,243,33,1,0,0,0,244,245,5,65,0,0,245,246,3,84,42,0,246,248,
        5,19,0,0,247,249,3,56,28,0,248,247,1,0,0,0,248,249,1,0,0,0,249,250,
        1,0,0,0,250,251,5,20,0,0,251,252,5,15,0,0,252,253,3,36,18,0,253,
        254,5,16,0,0,254,35,1,0,0,0,255,256,3,40,20,0,256,257,5,23,0,0,257,
        259,1,0,0,0,258,255,1,0,0,0,259,262,1,0,0,0,260,258,1,0,0,0,260,
        261,1,0,0,0,261,264,1,0,0,0,262,260,1,0,0,0,263,265,3,44,22,0,264,
        263,1,0,0,0,265,266,1,0,0,0,266,264,1,0,0,0,266,267,1,0,0,0,267,
        288,1,0,0,0,268,269,3,40,20,0,269,270,5,23,0,0,270,272,1,0,0,0,271,
        268,1,0,0,0,272,275,1,0,0,0,273,271,1,0,0,0,273,274,1,0,0,0,274,
        279,1,0,0,0,275,273,1,0,0,0,276,278,3,44,22,0,277,276,1,0,0,0,278,
        281,1,0,0,0,279,277,1,0,0,0,279,280,1,0,0,0,280,283,1,0,0,0,281,
        279,1,0,0,0,282,284,3,38,19,0,283,282,1,0,0,0,284,285,1,0,0,0,285,
        283,1,0,0,0,285,286,1,0,0,0,286,288,1,0,0,0,287,260,1,0,0,0,287,
        273,1,0,0,0,288,37,1,0,0,0,289,290,5,68,0,0,290,292,5,15,0,0,291,
        293,3,44,22,0,292,291,1,0,0,0,293,294,1,0,0,0,294,292,1,0,0,0,294,
        295,1,0,0,0,295,296,1,0,0,0,296,297,5,69,0,0,297,298,5,24,0,0,298,
        299,5,17,0,0,299,304,3,84,42,0,300,301,5,25,0,0,301,303,3,84,42,
        0,302,300,1,0,0,0,303,306,1,0,0,0,304,302,1,0,0,0,304,305,1,0,0,
        0,305,307,1,0,0,0,306,304,1,0,0,0,307,308,5,18,0,0,308,309,5,23,
        0,0,309,310,5,16,0,0,310,39,1,0,0,0,311,314,3,62,31,0,312,313,5,
        28,0,0,313,315,3,58,29,0,314,312,1,0,0,0,314,315,1,0,0,0,315,41,
        1,0,0,0,316,317,3,62,31,0,317,318,5,28,0,0,318,319,3,58,29,0,319,
        43,1,0,0,0,320,321,3,54,27,0,321,322,3,46,23,0,322,45,1,0,0,0,323,
        327,5,15,0,0,324,326,3,48,24,0,325,324,1,0,0,0,326,329,1,0,0,0,327,
        325,1,0,0,0,327,328,1,0,0,0,328,330,1,0,0,0,329,327,1,0,0,0,330,
        331,5,16,0,0,331,47,1,0,0,0,332,333,3,66,33,0,333,334,3,84,42,0,
        334,335,5,23,0,0,335,429,1,0,0,0,336,337,3,66,33,0,337,338,3,50,
        25,0,338,339,5,28,0,0,339,340,3,58,29,0,340,341,5,23,0,0,341,429,
        1,0,0,0,342,343,3,66,33,0,343,344,3,50,25,0,344,345,5,39,0,0,345,
        346,3,58,29,0,346,347,5,23,0,0,347,429,1,0,0,0,348,349,3,50,25,0,
        349,350,5,28,0,0,350,351,3,58,29,0,351,352,5,23,0,0,352,429,1,0,
        0,0,353,354,3,50,25,0,354,355,5,39,0,0,355,356,3,58,29,0,356,357,
        5,23,0,0,357,429,1,0,0,0,358,359,3,66,33,0,359,360,3,50,25,0,360,
        361,5,38,0,0,361,362,5,17,0,0,362,363,3,50,25,0,363,364,5,18,0,0,
        364,365,3,66,33,0,365,366,5,23,0,0,366,429,1,0,0,0,367,368,3,50,
        25,0,368,369,5,38,0,0,369,370,5,17,0,0,370,371,3,50,25,0,371,372,
        5,18,0,0,372,373,3,66,33,0,373,374,5,23,0,0,374,429,1,0,0,0,375,
        376,3,58,29,0,376,378,5,19,0,0,377,379,3,60,30,0,378,377,1,0,0,0,
        378,379,1,0,0,0,379,380,1,0,0,0,380,381,5,20,0,0,381,382,5,23,0,
        0,382,429,1,0,0,0,383,384,5,50,0,0,384,385,3,58,29,0,385,386,5,23,
        0,0,386,429,1,0,0,0,387,388,5,60,0,0,388,389,5,19,0,0,389,390,3,
        58,29,0,390,391,5,20,0,0,391,401,3,46,23,0,392,393,5,70,0,0,393,
        394,5,60,0,0,394,395,5,19,0,0,395,396,3,58,29,0,396,397,5,20,0,0,
        397,398,3,46,23,0,398,400,1,0,0,0,399,392,1,0,0,0,400,403,1,0,0,
        0,401,399,1,0,0,0,401,402,1,0,0,0,402,406,1,0,0,0,403,401,1,0,0,
        0,404,405,5,70,0,0,405,407,3,46,23,0,406,404,1,0,0,0,406,407,1,0,
        0,0,407,429,1,0,0,0,408,409,5,61,0,0,409,410,5,19,0,0,410,411,5,
        48,0,0,411,412,3,84,42,0,412,413,5,28,0,0,413,414,3,58,29,0,414,
        415,5,62,0,0,415,416,3,58,29,0,416,417,5,20,0,0,417,418,3,46,23,
        0,418,429,1,0,0,0,419,420,5,61,0,0,420,421,5,19,0,0,421,422,3,66,
        33,0,422,423,3,84,42,0,423,424,5,63,0,0,424,425,3,58,29,0,425,426,
        5,20,0,0,426,427,3,46,23,0,427,429,1,0,0,0,428,332,1,0,0,0,428,336,
        1,0,0,0,428,342,1,0,0,0,428,348,1,0,0,0,428,353,1,0,0,0,428,358,
        1,0,0,0,428,367,1,0,0,0,428,375,1,0,0,0,428,383,1,0,0,0,428,387,
        1,0,0,0,428,408,1,0,0,0,428,419,1,0,0,0,429,49,1,0,0,0,430,434,3,
        84,42,0,431,434,3,64,32,0,432,434,5,72,0,0,433,430,1,0,0,0,433,431,
        1,0,0,0,433,432,1,0,0,0,434,443,1,0,0,0,435,436,5,26,0,0,436,442,
        3,84,42,0,437,438,5,17,0,0,438,439,3,58,29,0,439,440,5,18,0,0,440,
        442,1,0,0,0,441,435,1,0,0,0,441,437,1,0,0,0,442,445,1,0,0,0,443,
        441,1,0,0,0,443,444,1,0,0,0,444,51,1,0,0,0,445,443,1,0,0,0,446,447,
        7,1,0,0,447,53,1,0,0,0,448,450,3,52,26,0,449,448,1,0,0,0,450,453,
        1,0,0,0,451,449,1,0,0,0,451,452,1,0,0,0,452,454,1,0,0,0,453,451,
        1,0,0,0,454,455,3,66,33,0,455,456,3,84,42,0,456,458,5,19,0,0,457,
        459,3,56,28,0,458,457,1,0,0,0,458,459,1,0,0,0,459,460,1,0,0,0,460,
        461,5,20,0,0,461,55,1,0,0,0,462,467,3,62,31,0,463,464,5,25,0,0,464,
        466,3,62,31,0,465,463,1,0,0,0,466,469,1,0,0,0,467,465,1,0,0,0,467,
        468,1,0,0,0,468,57,1,0,0,0,469,467,1,0,0,0,470,471,6,29,-1,0,471,
        472,5,42,0,0,472,518,3,58,29,31,473,474,5,44,0,0,474,475,3,58,29,
        0,475,476,5,44,0,0,476,518,1,0,0,0,477,478,5,30,0,0,478,518,3,58,
        29,26,479,518,3,50,25,0,480,489,5,17,0,0,481,486,3,58,29,0,482,483,
        5,25,0,0,483,485,3,58,29,0,484,482,1,0,0,0,485,488,1,0,0,0,486,484,
        1,0,0,0,486,487,1,0,0,0,487,490,1,0,0,0,488,486,1,0,0,0,489,481,
        1,0,0,0,489,490,1,0,0,0,490,491,1,0,0,0,491,518,5,18,0,0,492,501,
        5,15,0,0,493,498,3,58,29,0,494,495,5,25,0,0,495,497,3,58,29,0,496,
        494,1,0,0,0,497,500,1,0,0,0,498,496,1,0,0,0,498,499,1,0,0,0,499,
        502,1,0,0,0,500,498,1,0,0,0,501,493,1,0,0,0,501,502,1,0,0,0,502,
        503,1,0,0,0,503,518,5,16,0,0,504,518,3,66,33,0,505,506,5,78,0,0,
        506,518,3,70,35,0,507,508,5,79,0,0,508,518,3,70,35,0,509,518,5,77,
        0,0,510,518,5,80,0,0,511,518,3,80,40,0,512,518,5,71,0,0,513,514,
        5,19,0,0,514,515,3,58,29,0,515,516,5,20,0,0,516,518,1,0,0,0,517,
        470,1,0,0,0,517,473,1,0,0,0,517,477,1,0,0,0,517,479,1,0,0,0,517,
        480,1,0,0,0,517,492,1,0,0,0,517,504,1,0,0,0,517,505,1,0,0,0,517,
        507,1,0,0,0,517,509,1,0,0,0,517,510,1,0,0,0,517,511,1,0,0,0,517,
        512,1,0,0,0,517,513,1,0,0,0,518,585,1,0,0,0,519,520,10,29,0,0,520,
        521,5,43,0,0,521,584,3,58,29,29,522,523,10,28,0,0,523,524,5,27,0,
        0,524,584,3,58,29,29,525,526,10,27,0,0,526,527,5,31,0,0,527,584,
        3,58,29,28,528,529,10,25,0,0,529,530,5,29,0,0,530,584,3,58,29,26,
        531,532,10,24,0,0,532,533,5,30,0,0,533,584,3,58,29,25,534,535,10,
        23,0,0,535,536,5,33,0,0,536,584,3,58,29,24,537,538,10,22,0,0,538,
        539,5,34,0,0,539,584,3,58,29,23,540,541,10,21,0,0,541,542,5,22,0,
        0,542,584,3,58,29,22,543,544,10,20,0,0,544,545,5,21,0,0,545,584,
        3,58,29,21,546,547,10,19,0,0,547,548,5,35,0,0,548,584,3,58,29,20,
        549,550,10,18,0,0,550,551,5,36,0,0,551,584,3,58,29,19,552,553,10,
        17,0,0,553,554,5,63,0,0,554,584,3,58,29,18,555,556,10,16,0,0,556,
        557,5,59,0,0,557,584,3,58,29,17,558,559,10,15,0,0,559,560,5,40,0,
        0,560,584,3,58,29,16,561,562,10,14,0,0,562,563,5,37,0,0,563,584,
        3,58,29,15,564,565,10,13,0,0,565,566,5,64,0,0,566,584,3,58,29,14,
        567,568,10,12,0,0,568,569,5,41,0,0,569,584,3,58,29,13,570,571,10,
        33,0,0,571,573,5,19,0,0,572,574,3,60,30,0,573,572,1,0,0,0,573,574,
        1,0,0,0,574,575,1,0,0,0,575,584,5,20,0,0,576,577,10,32,0,0,577,578,
        5,17,0,0,578,579,3,68,34,0,579,580,5,24,0,0,580,581,3,68,34,0,581,
        582,5,18,0,0,582,584,1,0,0,0,583,519,1,0,0,0,583,522,1,0,0,0,583,
        525,1,0,0,0,583,528,1,0,0,0,583,531,1,0,0,0,583,534,1,0,0,0,583,
        537,1,0,0,0,583,540,1,0,0,0,583,543,1,0,0,0,583,546,1,0,0,0,583,
        549,1,0,0,0,583,552,1,0,0,0,583,555,1,0,0,0,583,558,1,0,0,0,583,
        561,1,0,0,0,583,564,1,0,0,0,583,567,1,0,0,0,583,570,1,0,0,0,583,
        576,1,0,0,0,584,587,1,0,0,0,585,583,1,0,0,0,585,586,1,0,0,0,586,
        59,1,0,0,0,587,585,1,0,0,0,588,593,3,58,29,0,589,590,5,25,0,0,590,
        592,3,58,29,0,591,589,1,0,0,0,592,595,1,0,0,0,593,591,1,0,0,0,593,
        594,1,0,0,0,594,61,1,0,0,0,595,593,1,0,0,0,596,597,3,66,33,0,597,
        598,3,84,42,0,598,63,1,0,0,0,599,600,3,84,42,0,600,602,5,19,0,0,
        601,603,3,60,30,0,602,601,1,0,0,0,602,603,1,0,0,0,603,604,1,0,0,
        0,604,605,5,20,0,0,605,65,1,0,0,0,606,607,6,33,-1,0,607,648,3,78,
        39,0,608,648,5,46,0,0,609,648,5,47,0,0,610,611,5,49,0,0,611,612,
        5,21,0,0,612,613,3,66,33,0,613,614,5,25,0,0,614,615,3,66,33,0,615,
        616,5,22,0,0,616,648,1,0,0,0,617,618,5,56,0,0,618,619,5,21,0,0,619,
        620,3,66,33,0,620,621,5,25,0,0,621,622,3,68,34,0,622,623,5,22,0,
        0,623,648,1,0,0,0,624,625,5,57,0,0,625,626,5,21,0,0,626,627,3,66,
        33,0,627,628,5,25,0,0,628,629,3,66,33,0,629,630,5,22,0,0,630,648,
        1,0,0,0,631,648,5,48,0,0,632,633,5,17,0,0,633,636,3,66,33,0,634,
        635,5,25,0,0,635,637,3,66,33,0,636,634,1,0,0,0,637,638,1,0,0,0,638,
        636,1,0,0,0,638,639,1,0,0,0,639,640,1,0,0,0,640,641,5,18,0,0,641,
        648,1,0,0,0,642,648,3,72,36,0,643,648,3,74,37,0,644,648,3,76,38,
        0,645,648,5,54,0,0,646,648,3,50,25,0,647,606,1,0,0,0,647,608,1,0,
        0,0,647,609,1,0,0,0,647,610,1,0,0,0,647,617,1,0,0,0,647,624,1,0,
        0,0,647,631,1,0,0,0,647,632,1,0,0,0,647,642,1,0,0,0,647,643,1,0,
        0,0,647,644,1,0,0,0,647,645,1,0,0,0,647,646,1,0,0,0,648,653,1,0,
        0,0,649,650,10,14,0,0,650,652,5,32,0,0,651,649,1,0,0,0,652,655,1,
        0,0,0,653,651,1,0,0,0,653,654,1,0,0,0,654,67,1,0,0,0,655,653,1,0,
        0,0,656,657,6,34,-1,0,657,665,3,50,25,0,658,665,5,80,0,0,659,665,
        5,77,0,0,660,661,5,19,0,0,661,662,3,68,34,0,662,663,5,20,0,0,663,
        665,1,0,0,0,664,656,1,0,0,0,664,658,1,0,0,0,664,659,1,0,0,0,664,
        660,1,0,0,0,665,680,1,0,0,0,666,667,10,8,0,0,667,668,5,27,0,0,668,
        679,3,68,34,9,669,670,10,7,0,0,670,671,5,31,0,0,671,679,3,68,34,
        8,672,673,10,6,0,0,673,674,5,29,0,0,674,679,3,68,34,7,675,676,10,
        5,0,0,676,677,5,30,0,0,677,679,3,68,34,6,678,666,1,0,0,0,678,669,
        1,0,0,0,678,672,1,0,0,0,678,675,1,0,0,0,679,682,1,0,0,0,680,678,
        1,0,0,0,680,681,1,0,0,0,681,69,1,0,0,0,682,680,1,0,0,0,683,690,3,
        50,25,0,684,690,5,80,0,0,685,686,5,19,0,0,686,687,3,68,34,0,687,
        688,5,20,0,0,688,690,1,0,0,0,689,683,1,0,0,0,689,684,1,0,0,0,689,
        685,1,0,0,0,690,71,1,0,0,0,691,692,5,52,0,0,692,693,5,21,0,0,693,
        694,3,68,34,0,694,695,5,22,0,0,695,698,1,0,0,0,696,698,5,52,0,0,
        697,691,1,0,0,0,697,696,1,0,0,0,698,73,1,0,0,0,699,700,5,53,0,0,
        700,701,5,21,0,0,701,702,3,68,34,0,702,703,5,22,0,0,703,75,1,0,0,
        0,704,705,5,55,0,0,705,706,5,21,0,0,706,707,3,50,25,0,707,708,5,
        22,0,0,708,77,1,0,0,0,709,710,5,45,0,0,710,711,5,21,0,0,711,712,
        3,66,33,0,712,713,5,22,0,0,713,716,1,0,0,0,714,716,5,45,0,0,715,
        709,1,0,0,0,715,714,1,0,0,0,716,79,1,0,0,0,717,718,7,2,0,0,718,81,
        1,0,0,0,719,720,5,51,0,0,720,723,5,84,0,0,721,722,5,67,0,0,722,724,
        5,81,0,0,723,721,1,0,0,0,723,724,1,0,0,0,724,725,1,0,0,0,725,726,
        5,23,0,0,726,83,1,0,0,0,727,728,7,3,0,0,728,85,1,0,0,0,58,89,98,
        100,107,123,128,133,147,155,162,170,175,193,195,206,211,231,248,
        260,266,273,279,285,287,294,304,314,327,378,401,406,428,433,441,
        443,451,458,467,486,489,498,501,517,573,583,585,593,602,638,647,
        653,664,678,680,689,697,715,723
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
                     "'Group'", "'GroupElem'", "'Array'", "'Function'", 
                     "'Primitive'", "'subsets'", "'if'", "'for'", "'to'", 
                     "'in'", "'union'", "'Game'", "'export'", "'as'", "'Phase'", 
                     "'oracles'", "'else'", "'None'", "'this'", "'deterministic'", 
                     "'injective'", "'true'", "'false'", "<INVALID>", "'0^'", 
                     "'1^'" ]

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
                      "MODINT", "GROUP", "GROUPELEM", "ARRAY", "FUNCTION", 
                      "PRIMITIVE", "SUBSETS", "IF", "FOR", "TO", "IN", "UNION", 
                      "GAME", "EXPORT", "AS", "PHASE", "ORACLES", "ELSE", 
                      "NONE", "THIS", "DETERMINISTIC", "INJECTIVE", "TRUE", 
                      "FALSE", "BINARYNUM", "ZEROS_CARET", "ONES_CARET", 
                      "INT", "ID", "WS", "LINE_COMMENT", "FILESTRING" ]

    RULE_program = 0
    RULE_proofHelpers = 1
    RULE_reduction = 2
    RULE_proof = 3
    RULE_lets = 4
    RULE_letEntry = 5
    RULE_assumptions = 6
    RULE_lemmas = 7
    RULE_lemmaEntry = 8
    RULE_theorem = 9
    RULE_gameList = 10
    RULE_gameStep = 11
    RULE_induction = 12
    RULE_stepAssumption = 13
    RULE_gameField = 14
    RULE_concreteGame = 15
    RULE_gameAdversary = 16
    RULE_game = 17
    RULE_gameBody = 18
    RULE_gamePhase = 19
    RULE_field = 20
    RULE_initializedField = 21
    RULE_method = 22
    RULE_block = 23
    RULE_statement = 24
    RULE_lvalue = 25
    RULE_methodModifier = 26
    RULE_methodSignature = 27
    RULE_paramList = 28
    RULE_expression = 29
    RULE_argList = 30
    RULE_variable = 31
    RULE_parameterizedGame = 32
    RULE_type = 33
    RULE_integerExpression = 34
    RULE_integerAtom = 35
    RULE_bitstring = 36
    RULE_modint = 37
    RULE_groupelem = 38
    RULE_set = 39
    RULE_bool = 40
    RULE_moduleImport = 41
    RULE_id = 42

    ruleNames =  [ "program", "proofHelpers", "reduction", "proof", "lets", 
                   "letEntry", "assumptions", "lemmas", "lemmaEntry", "theorem", 
                   "gameList", "gameStep", "induction", "stepAssumption", 
                   "gameField", "concreteGame", "gameAdversary", "game", 
                   "gameBody", "gamePhase", "field", "initializedField", 
                   "method", "block", "statement", "lvalue", "methodModifier", 
                   "methodSignature", "paramList", "expression", "argList", 
                   "variable", "parameterizedGame", "type", "integerExpression", 
                   "integerAtom", "bitstring", "modint", "groupelem", "set", 
                   "bool", "moduleImport", "id" ]

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
    GROUP=54
    GROUPELEM=55
    ARRAY=56
    FUNCTION=57
    PRIMITIVE=58
    SUBSETS=59
    IF=60
    FOR=61
    TO=62
    IN=63
    UNION=64
    GAME=65
    EXPORT=66
    AS=67
    PHASE=68
    ORACLES=69
    ELSE=70
    NONE=71
    THIS=72
    DETERMINISTIC=73
    INJECTIVE=74
    TRUE=75
    FALSE=76
    BINARYNUM=77
    ZEROS_CARET=78
    ONES_CARET=79
    INT=80
    ID=81
    WS=82
    LINE_COMMENT=83
    FILESTRING=84

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
            self.state = 89
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==51:
                self.state = 86
                self.moduleImport()
                self.state = 91
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 92
            self.proofHelpers()
            self.state = 93
            self.proof()
            self.state = 94
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
            self.state = 100
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==1 or _la==65:
                self.state = 98
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [1]:
                    self.state = 96
                    self.reduction()
                    pass
                elif token in [65]:
                    self.state = 97
                    self.game()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 102
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

        def id_(self):
            return self.getTypedRuleContext(ProofParser.IdContext,0)


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
            self.state = 103
            self.match(ProofParser.REDUCTION)
            self.state = 104
            self.id_()
            self.state = 105
            self.match(ProofParser.L_PAREN)
            self.state = 107
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & -8938554544795549696) != 0) or _la==72 or _la==81:
                self.state = 106
                self.paramList()


            self.state = 109
            self.match(ProofParser.R_PAREN)
            self.state = 110
            self.match(ProofParser.COMPOSE)
            self.state = 111
            self.parameterizedGame()
            self.state = 112
            self.match(ProofParser.AGAINST)
            self.state = 113
            self.gameAdversary()
            self.state = 114
            self.match(ProofParser.L_CURLY)
            self.state = 115
            self.gameBody()
            self.state = 116
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
            self.state = 118
            self.match(ProofParser.PROOF)
            self.state = 119
            self.match(ProofParser.COLON)
            self.state = 123
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==9:
                self.state = 120
                self.match(ProofParser.LET)
                self.state = 121
                self.match(ProofParser.COLON)
                self.state = 122
                self.lets()


            self.state = 128
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==6:
                self.state = 125
                self.match(ProofParser.ASSUME)
                self.state = 126
                self.match(ProofParser.COLON)
                self.state = 127
                self.assumptions()


            self.state = 133
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 130
                self.match(ProofParser.LEMMA)
                self.state = 131
                self.match(ProofParser.COLON)
                self.state = 132
                self.lemmas()


            self.state = 135
            self.match(ProofParser.THEOREM)
            self.state = 136
            self.match(ProofParser.COLON)
            self.state = 137
            self.theorem()
            self.state = 138
            self.match(ProofParser.GAMES)
            self.state = 139
            self.match(ProofParser.COLON)
            self.state = 140
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

        def letEntry(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ProofParser.LetEntryContext)
            else:
                return self.getTypedRuleContext(ProofParser.LetEntryContext,i)


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
            self.state = 147
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & -8938554544795549696) != 0) or _la==72 or _la==81:
                self.state = 142
                self.letEntry()
                self.state = 143
                self.match(ProofParser.SEMI)
                self.state = 149
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LetEntryContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return ProofParser.RULE_letEntry

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)



    class LetSampleContext(LetEntryContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.LetEntryContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def variable(self):
            return self.getTypedRuleContext(ProofParser.VariableContext,0)

        def SAMPLES(self):
            return self.getToken(ProofParser.SAMPLES, 0)
        def expression(self):
            return self.getTypedRuleContext(ProofParser.ExpressionContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLetSample" ):
                return visitor.visitLetSample(self)
            else:
                return visitor.visitChildren(self)


    class LetFieldContext(LetEntryContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.LetEntryContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def field(self):
            return self.getTypedRuleContext(ProofParser.FieldContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLetField" ):
                return visitor.visitLetField(self)
            else:
                return visitor.visitChildren(self)



    def letEntry(self):

        localctx = ProofParser.LetEntryContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_letEntry)
        try:
            self.state = 155
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,8,self._ctx)
            if la_ == 1:
                localctx = ProofParser.LetFieldContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 150
                self.field()
                pass

            elif la_ == 2:
                localctx = ProofParser.LetSampleContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 151
                self.variable()
                self.state = 152
                self.match(ProofParser.SAMPLES)
                self.state = 153
                self.expression(0)
                pass


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
        self.enterRule(localctx, 12, self.RULE_assumptions)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 162
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while ((((_la - 54)) & ~0x3f) == 0 and ((1 << (_la - 54)) & 134218243) != 0):
                self.state = 157
                self.parameterizedGame()
                self.state = 158
                self.match(ProofParser.SEMI)
                self.state = 164
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 170
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==10:
                self.state = 165
                self.match(ProofParser.CALLS)
                self.state = 166
                _la = self._input.LA(1)
                if not(_la==21 or _la==36):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 167
                self.expression(0)
                self.state = 168
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
        self.enterRule(localctx, 14, self.RULE_lemmas)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 175
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while ((((_la - 54)) & ~0x3f) == 0 and ((1 << (_la - 54)) & 134218243) != 0):
                self.state = 172
                self.lemmaEntry()
                self.state = 177
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
        self.enterRule(localctx, 16, self.RULE_lemmaEntry)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 178
            self.parameterizedGame()
            self.state = 179
            self.match(ProofParser.BY)
            self.state = 180
            self.match(ProofParser.FILESTRING)
            self.state = 181
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
        self.enterRule(localctx, 18, self.RULE_theorem)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 183
            self.parameterizedGame()
            self.state = 184
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
        self.enterRule(localctx, 20, self.RULE_gameList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 186
            self.gameStep()
            self.state = 187
            self.match(ProofParser.SEMI)
            self.state = 195
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & -9169328841326327744) != 0) or _la==81:
                self.state = 193
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [54, 55, 63, 81]:
                    self.state = 188
                    self.gameStep()
                    self.state = 189
                    self.match(ProofParser.SEMI)
                    pass
                elif token in [11]:
                    self.state = 191
                    self.induction()
                    pass
                elif token in [6]:
                    self.state = 192
                    self.stepAssumption()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 197
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
        self.enterRule(localctx, 22, self.RULE_gameStep)
        try:
            self.state = 211
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,15,self._ctx)
            if la_ == 1:
                localctx = ProofParser.ReductionStepContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 198
                self.concreteGame()
                self.state = 199
                self.match(ProofParser.COMPOSE)
                self.state = 200
                self.parameterizedGame()
                self.state = 201
                self.match(ProofParser.AGAINST)
                self.state = 202
                self.gameAdversary()
                pass

            elif la_ == 2:
                localctx = ProofParser.RegularStepContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 206
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
                if la_ == 1:
                    self.state = 204
                    self.concreteGame()
                    pass

                elif la_ == 2:
                    self.state = 205
                    self.parameterizedGame()
                    pass


                self.state = 208
                self.match(ProofParser.AGAINST)
                self.state = 209
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

        def id_(self):
            return self.getTypedRuleContext(ProofParser.IdContext,0)


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
        self.enterRule(localctx, 24, self.RULE_induction)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 213
            self.match(ProofParser.INDUCTION)
            self.state = 214
            self.match(ProofParser.L_PAREN)
            self.state = 215
            self.id_()
            self.state = 216
            self.match(ProofParser.FROM)
            self.state = 217
            self.integerExpression(0)
            self.state = 218
            self.match(ProofParser.TO)
            self.state = 219
            self.integerExpression(0)
            self.state = 220
            self.match(ProofParser.R_PAREN)
            self.state = 221
            self.match(ProofParser.L_CURLY)
            self.state = 222
            self.gameList()
            self.state = 223
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
        self.enterRule(localctx, 26, self.RULE_stepAssumption)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 225
            self.match(ProofParser.ASSUME)
            self.state = 226
            self.expression(0)
            self.state = 227
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

        def id_(self):
            return self.getTypedRuleContext(ProofParser.IdContext,0)


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
        self.enterRule(localctx, 28, self.RULE_gameField)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 231
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,16,self._ctx)
            if la_ == 1:
                self.state = 229
                self.concreteGame()
                pass

            elif la_ == 2:
                self.state = 230
                self.parameterizedGame()
                pass


            self.state = 233
            self.match(ProofParser.PERIOD)
            self.state = 234
            self.id_()
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

        def id_(self):
            return self.getTypedRuleContext(ProofParser.IdContext,0)


        def getRuleIndex(self):
            return ProofParser.RULE_concreteGame

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConcreteGame" ):
                return visitor.visitConcreteGame(self)
            else:
                return visitor.visitChildren(self)




    def concreteGame(self):

        localctx = ProofParser.ConcreteGameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 30, self.RULE_concreteGame)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 236
            self.parameterizedGame()
            self.state = 237
            self.match(ProofParser.PERIOD)
            self.state = 238
            self.id_()
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
        self.enterRule(localctx, 32, self.RULE_gameAdversary)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 240
            self.parameterizedGame()
            self.state = 241
            self.match(ProofParser.PERIOD)
            self.state = 242
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

        def id_(self):
            return self.getTypedRuleContext(ProofParser.IdContext,0)


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
        self.enterRule(localctx, 34, self.RULE_game)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 244
            self.match(ProofParser.GAME)
            self.state = 245
            self.id_()
            self.state = 246
            self.match(ProofParser.L_PAREN)
            self.state = 248
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & -8938554544795549696) != 0) or _la==72 or _la==81:
                self.state = 247
                self.paramList()


            self.state = 250
            self.match(ProofParser.R_PAREN)
            self.state = 251
            self.match(ProofParser.L_CURLY)
            self.state = 252
            self.gameBody()
            self.state = 253
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
        self.enterRule(localctx, 36, self.RULE_gameBody)
        self._la = 0 # Token type
        try:
            self.state = 287
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,23,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 260
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,18,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 255
                        self.field()
                        self.state = 256
                        self.match(ProofParser.SEMI) 
                    self.state = 262
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,18,self._ctx)

                self.state = 264 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 263
                    self.method()
                    self.state = 266 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & -8938554544795549696) != 0) or ((((_la - 72)) & ~0x3f) == 0 and ((1 << (_la - 72)) & 519) != 0)):
                        break

                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 273
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,20,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 268
                        self.field()
                        self.state = 269
                        self.match(ProofParser.SEMI) 
                    self.state = 275
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,20,self._ctx)

                self.state = 279
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while (((_la) & ~0x3f) == 0 and ((1 << _la) & -8938554544795549696) != 0) or ((((_la - 72)) & ~0x3f) == 0 and ((1 << (_la - 72)) & 519) != 0):
                    self.state = 276
                    self.method()
                    self.state = 281
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 283 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 282
                    self.gamePhase()
                    self.state = 285 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==68):
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
        self.enterRule(localctx, 38, self.RULE_gamePhase)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 289
            self.match(ProofParser.PHASE)
            self.state = 290
            self.match(ProofParser.L_CURLY)
            self.state = 292 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 291
                self.method()
                self.state = 294 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & -8938554544795549696) != 0) or ((((_la - 72)) & ~0x3f) == 0 and ((1 << (_la - 72)) & 519) != 0)):
                    break

            self.state = 296
            self.match(ProofParser.ORACLES)
            self.state = 297
            self.match(ProofParser.COLON)
            self.state = 298
            self.match(ProofParser.L_SQUARE)
            self.state = 299
            self.id_()
            self.state = 304
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==25:
                self.state = 300
                self.match(ProofParser.COMMA)
                self.state = 301
                self.id_()
                self.state = 306
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 307
            self.match(ProofParser.R_SQUARE)
            self.state = 308
            self.match(ProofParser.SEMI)
            self.state = 309
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
        self.enterRule(localctx, 40, self.RULE_field)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 311
            self.variable()
            self.state = 314
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==28:
                self.state = 312
                self.match(ProofParser.EQUALS)
                self.state = 313
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
        self.enterRule(localctx, 42, self.RULE_initializedField)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 316
            self.variable()
            self.state = 317
            self.match(ProofParser.EQUALS)
            self.state = 318
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
        self.enterRule(localctx, 44, self.RULE_method)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 320
            self.methodSignature()
            self.state = 321
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
        self.enterRule(localctx, 46, self.RULE_block)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 323
            self.match(ProofParser.L_CURLY)
            self.state = 327
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & -5478642139761311744) != 0) or ((((_la - 71)) & ~0x3f) == 0 and ((1 << (_la - 71)) & 2035) != 0):
                self.state = 324
                self.statement()
                self.state = 329
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 330
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
        self.enterRule(localctx, 48, self.RULE_statement)
        self._la = 0 # Token type
        try:
            self.state = 428
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,31,self._ctx)
            if la_ == 1:
                localctx = ProofParser.VarDeclStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 332
                self.type_(0)
                self.state = 333
                self.id_()
                self.state = 334
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 2:
                localctx = ProofParser.VarDeclWithValueStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 336
                self.type_(0)
                self.state = 337
                self.lvalue()
                self.state = 338
                self.match(ProofParser.EQUALS)
                self.state = 339
                self.expression(0)
                self.state = 340
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 3:
                localctx = ProofParser.VarDeclWithSampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 342
                self.type_(0)
                self.state = 343
                self.lvalue()
                self.state = 344
                self.match(ProofParser.SAMPLES)
                self.state = 345
                self.expression(0)
                self.state = 346
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 4:
                localctx = ProofParser.AssignmentStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 348
                self.lvalue()
                self.state = 349
                self.match(ProofParser.EQUALS)
                self.state = 350
                self.expression(0)
                self.state = 351
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 5:
                localctx = ProofParser.SampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 5)
                self.state = 353
                self.lvalue()
                self.state = 354
                self.match(ProofParser.SAMPLES)
                self.state = 355
                self.expression(0)
                self.state = 356
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 6:
                localctx = ProofParser.UniqueSampleStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 6)
                self.state = 358
                self.type_(0)
                self.state = 359
                self.lvalue()
                self.state = 360
                self.match(ProofParser.SAMPUNIQ)
                self.state = 361
                self.match(ProofParser.L_SQUARE)
                self.state = 362
                self.lvalue()
                self.state = 363
                self.match(ProofParser.R_SQUARE)
                self.state = 364
                self.type_(0)
                self.state = 365
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 7:
                localctx = ProofParser.UniqueSampleNoTypeStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 7)
                self.state = 367
                self.lvalue()
                self.state = 368
                self.match(ProofParser.SAMPUNIQ)
                self.state = 369
                self.match(ProofParser.L_SQUARE)
                self.state = 370
                self.lvalue()
                self.state = 371
                self.match(ProofParser.R_SQUARE)
                self.state = 372
                self.type_(0)
                self.state = 373
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 8:
                localctx = ProofParser.FunctionCallStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 8)
                self.state = 375
                self.expression(0)
                self.state = 376
                self.match(ProofParser.L_PAREN)
                self.state = 378
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & -8938532553488695296) != 0) or ((((_la - 71)) & ~0x3f) == 0 and ((1 << (_la - 71)) & 2035) != 0):
                    self.state = 377
                    self.argList()


                self.state = 380
                self.match(ProofParser.R_PAREN)
                self.state = 381
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 9:
                localctx = ProofParser.ReturnStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 9)
                self.state = 383
                self.match(ProofParser.RETURN)
                self.state = 384
                self.expression(0)
                self.state = 385
                self.match(ProofParser.SEMI)
                pass

            elif la_ == 10:
                localctx = ProofParser.IfStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 10)
                self.state = 387
                self.match(ProofParser.IF)
                self.state = 388
                self.match(ProofParser.L_PAREN)
                self.state = 389
                self.expression(0)
                self.state = 390
                self.match(ProofParser.R_PAREN)
                self.state = 391
                self.block()
                self.state = 401
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,29,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 392
                        self.match(ProofParser.ELSE)
                        self.state = 393
                        self.match(ProofParser.IF)
                        self.state = 394
                        self.match(ProofParser.L_PAREN)
                        self.state = 395
                        self.expression(0)
                        self.state = 396
                        self.match(ProofParser.R_PAREN)
                        self.state = 397
                        self.block() 
                    self.state = 403
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,29,self._ctx)

                self.state = 406
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==70:
                    self.state = 404
                    self.match(ProofParser.ELSE)
                    self.state = 405
                    self.block()


                pass

            elif la_ == 11:
                localctx = ProofParser.NumericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 11)
                self.state = 408
                self.match(ProofParser.FOR)
                self.state = 409
                self.match(ProofParser.L_PAREN)
                self.state = 410
                self.match(ProofParser.INTTYPE)
                self.state = 411
                self.id_()
                self.state = 412
                self.match(ProofParser.EQUALS)
                self.state = 413
                self.expression(0)
                self.state = 414
                self.match(ProofParser.TO)
                self.state = 415
                self.expression(0)
                self.state = 416
                self.match(ProofParser.R_PAREN)
                self.state = 417
                self.block()
                pass

            elif la_ == 12:
                localctx = ProofParser.GenericForStatementContext(self, localctx)
                self.enterOuterAlt(localctx, 12)
                self.state = 419
                self.match(ProofParser.FOR)
                self.state = 420
                self.match(ProofParser.L_PAREN)
                self.state = 421
                self.type_(0)
                self.state = 422
                self.id_()
                self.state = 423
                self.match(ProofParser.IN)
                self.state = 424
                self.expression(0)
                self.state = 425
                self.match(ProofParser.R_PAREN)
                self.state = 426
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
        self.enterRule(localctx, 50, self.RULE_lvalue)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 433
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,32,self._ctx)
            if la_ == 1:
                self.state = 430
                self.id_()
                pass

            elif la_ == 2:
                self.state = 431
                self.parameterizedGame()
                pass

            elif la_ == 3:
                self.state = 432
                self.match(ProofParser.THIS)
                pass


            self.state = 443
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,34,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 441
                    self._errHandler.sync(self)
                    token = self._input.LA(1)
                    if token in [26]:
                        self.state = 435
                        self.match(ProofParser.PERIOD)
                        self.state = 436
                        self.id_()
                        pass
                    elif token in [17]:
                        self.state = 437
                        self.match(ProofParser.L_SQUARE)
                        self.state = 438
                        self.expression(0)
                        self.state = 439
                        self.match(ProofParser.R_SQUARE)
                        pass
                    else:
                        raise NoViableAltException(self)
             
                self.state = 445
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,34,self._ctx)

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
        self.enterRule(localctx, 52, self.RULE_methodModifier)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 446
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
        self.enterRule(localctx, 54, self.RULE_methodSignature)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 451
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==73 or _la==74:
                self.state = 448
                self.methodModifier()
                self.state = 453
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 454
            self.type_(0)
            self.state = 455
            self.id_()
            self.state = 456
            self.match(ProofParser.L_PAREN)
            self.state = 458
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & -8938554544795549696) != 0) or _la==72 or _la==81:
                self.state = 457
                self.paramList()


            self.state = 460
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
        self.enterRule(localctx, 56, self.RULE_paramList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 462
            self.variable()
            self.state = 467
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==25:
                self.state = 463
                self.match(ProofParser.COMMA)
                self.state = 464
                self.variable()
                self.state = 469
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
        _startState = 58
        self.enterRecursionRule(localctx, 58, self.RULE_expression, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 517
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,42,self._ctx)
            if la_ == 1:
                localctx = ProofParser.NotExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 471
                self.match(ProofParser.NOT)
                self.state = 472
                self.expression(31)
                pass

            elif la_ == 2:
                localctx = ProofParser.SizeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 473
                self.match(ProofParser.VBAR)
                self.state = 474
                self.expression(0)
                self.state = 475
                self.match(ProofParser.VBAR)
                pass

            elif la_ == 3:
                localctx = ProofParser.MinusExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 477
                self.match(ProofParser.SUBTRACT)
                self.state = 478
                self.expression(26)
                pass

            elif la_ == 4:
                localctx = ProofParser.LvalueExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 479
                self.lvalue()
                pass

            elif la_ == 5:
                localctx = ProofParser.CreateTupleExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 480
                self.match(ProofParser.L_SQUARE)
                self.state = 489
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & -8938532553488695296) != 0) or ((((_la - 71)) & ~0x3f) == 0 and ((1 << (_la - 71)) & 2035) != 0):
                    self.state = 481
                    self.expression(0)
                    self.state = 486
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==25:
                        self.state = 482
                        self.match(ProofParser.COMMA)
                        self.state = 483
                        self.expression(0)
                        self.state = 488
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 491
                self.match(ProofParser.R_SQUARE)
                pass

            elif la_ == 6:
                localctx = ProofParser.CreateSetExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 492
                self.match(ProofParser.L_CURLY)
                self.state = 501
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & -8938532553488695296) != 0) or ((((_la - 71)) & ~0x3f) == 0 and ((1 << (_la - 71)) & 2035) != 0):
                    self.state = 493
                    self.expression(0)
                    self.state = 498
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la==25:
                        self.state = 494
                        self.match(ProofParser.COMMA)
                        self.state = 495
                        self.expression(0)
                        self.state = 500
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)



                self.state = 503
                self.match(ProofParser.R_CURLY)
                pass

            elif la_ == 7:
                localctx = ProofParser.TypeExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 504
                self.type_(0)
                pass

            elif la_ == 8:
                localctx = ProofParser.ZerosExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 505
                self.match(ProofParser.ZEROS_CARET)
                self.state = 506
                self.integerAtom()
                pass

            elif la_ == 9:
                localctx = ProofParser.OnesExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 507
                self.match(ProofParser.ONES_CARET)
                self.state = 508
                self.integerAtom()
                pass

            elif la_ == 10:
                localctx = ProofParser.BinaryNumExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 509
                self.match(ProofParser.BINARYNUM)
                pass

            elif la_ == 11:
                localctx = ProofParser.IntExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 510
                self.match(ProofParser.INT)
                pass

            elif la_ == 12:
                localctx = ProofParser.BoolExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 511
                self.bool_()
                pass

            elif la_ == 13:
                localctx = ProofParser.NoneExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 512
                self.match(ProofParser.NONE)
                pass

            elif la_ == 14:
                localctx = ProofParser.ParenExpContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 513
                self.match(ProofParser.L_PAREN)
                self.state = 514
                self.expression(0)
                self.state = 515
                self.match(ProofParser.R_PAREN)
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 585
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,45,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 583
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,44,self._ctx)
                    if la_ == 1:
                        localctx = ProofParser.ExponentiationExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 519
                        if not self.precpred(self._ctx, 29):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 29)")
                        self.state = 520
                        self.match(ProofParser.CARET)
                        self.state = 521
                        self.expression(29)
                        pass

                    elif la_ == 2:
                        localctx = ProofParser.MultiplyExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 522
                        if not self.precpred(self._ctx, 28):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 28)")
                        self.state = 523
                        self.match(ProofParser.TIMES)
                        self.state = 524
                        self.expression(29)
                        pass

                    elif la_ == 3:
                        localctx = ProofParser.DivideExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 525
                        if not self.precpred(self._ctx, 27):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 27)")
                        self.state = 526
                        self.match(ProofParser.DIVIDE)
                        self.state = 527
                        self.expression(28)
                        pass

                    elif la_ == 4:
                        localctx = ProofParser.AddExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 528
                        if not self.precpred(self._ctx, 25):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 25)")
                        self.state = 529
                        self.match(ProofParser.PLUS)
                        self.state = 530
                        self.expression(26)
                        pass

                    elif la_ == 5:
                        localctx = ProofParser.SubtractExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 531
                        if not self.precpred(self._ctx, 24):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 24)")
                        self.state = 532
                        self.match(ProofParser.SUBTRACT)
                        self.state = 533
                        self.expression(25)
                        pass

                    elif la_ == 6:
                        localctx = ProofParser.EqualsExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 534
                        if not self.precpred(self._ctx, 23):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 23)")
                        self.state = 535
                        self.match(ProofParser.EQUALSCOMPARE)
                        self.state = 536
                        self.expression(24)
                        pass

                    elif la_ == 7:
                        localctx = ProofParser.NotEqualsExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 537
                        if not self.precpred(self._ctx, 22):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 22)")
                        self.state = 538
                        self.match(ProofParser.NOTEQUALS)
                        self.state = 539
                        self.expression(23)
                        pass

                    elif la_ == 8:
                        localctx = ProofParser.GtExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 540
                        if not self.precpred(self._ctx, 21):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 21)")
                        self.state = 541
                        self.match(ProofParser.R_ANGLE)
                        self.state = 542
                        self.expression(22)
                        pass

                    elif la_ == 9:
                        localctx = ProofParser.LtExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 543
                        if not self.precpred(self._ctx, 20):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 20)")
                        self.state = 544
                        self.match(ProofParser.L_ANGLE)
                        self.state = 545
                        self.expression(21)
                        pass

                    elif la_ == 10:
                        localctx = ProofParser.GeqExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 546
                        if not self.precpred(self._ctx, 19):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 19)")
                        self.state = 547
                        self.match(ProofParser.GEQ)
                        self.state = 548
                        self.expression(20)
                        pass

                    elif la_ == 11:
                        localctx = ProofParser.LeqExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 549
                        if not self.precpred(self._ctx, 18):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 18)")
                        self.state = 550
                        self.match(ProofParser.LEQ)
                        self.state = 551
                        self.expression(19)
                        pass

                    elif la_ == 12:
                        localctx = ProofParser.InExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 552
                        if not self.precpred(self._ctx, 17):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 17)")
                        self.state = 553
                        self.match(ProofParser.IN)
                        self.state = 554
                        self.expression(18)
                        pass

                    elif la_ == 13:
                        localctx = ProofParser.SubsetsExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 555
                        if not self.precpred(self._ctx, 16):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 16)")
                        self.state = 556
                        self.match(ProofParser.SUBSETS)
                        self.state = 557
                        self.expression(17)
                        pass

                    elif la_ == 14:
                        localctx = ProofParser.AndExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 558
                        if not self.precpred(self._ctx, 15):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 15)")
                        self.state = 559
                        self.match(ProofParser.AND)
                        self.state = 560
                        self.expression(16)
                        pass

                    elif la_ == 15:
                        localctx = ProofParser.OrExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 561
                        if not self.precpred(self._ctx, 14):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 14)")
                        self.state = 562
                        self.match(ProofParser.OR)
                        self.state = 563
                        self.expression(15)
                        pass

                    elif la_ == 16:
                        localctx = ProofParser.UnionExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 564
                        if not self.precpred(self._ctx, 13):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 13)")
                        self.state = 565
                        self.match(ProofParser.UNION)
                        self.state = 566
                        self.expression(14)
                        pass

                    elif la_ == 17:
                        localctx = ProofParser.SetMinusExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 567
                        if not self.precpred(self._ctx, 12):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 12)")
                        self.state = 568
                        self.match(ProofParser.BACKSLASH)
                        self.state = 569
                        self.expression(13)
                        pass

                    elif la_ == 18:
                        localctx = ProofParser.FnCallExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 570
                        if not self.precpred(self._ctx, 33):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 33)")
                        self.state = 571
                        self.match(ProofParser.L_PAREN)
                        self.state = 573
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)
                        if (((_la) & ~0x3f) == 0 and ((1 << _la) & -8938532553488695296) != 0) or ((((_la - 71)) & ~0x3f) == 0 and ((1 << (_la - 71)) & 2035) != 0):
                            self.state = 572
                            self.argList()


                        self.state = 575
                        self.match(ProofParser.R_PAREN)
                        pass

                    elif la_ == 19:
                        localctx = ProofParser.SliceExpContext(self, ProofParser.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 576
                        if not self.precpred(self._ctx, 32):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 32)")
                        self.state = 577
                        self.match(ProofParser.L_SQUARE)
                        self.state = 578
                        self.integerExpression(0)
                        self.state = 579
                        self.match(ProofParser.COLON)
                        self.state = 580
                        self.integerExpression(0)
                        self.state = 581
                        self.match(ProofParser.R_SQUARE)
                        pass

             
                self.state = 587
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,45,self._ctx)

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
        self.enterRule(localctx, 60, self.RULE_argList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 588
            self.expression(0)
            self.state = 593
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==25:
                self.state = 589
                self.match(ProofParser.COMMA)
                self.state = 590
                self.expression(0)
                self.state = 595
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
        self.enterRule(localctx, 62, self.RULE_variable)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 596
            self.type_(0)
            self.state = 597
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
            return self.getTypedRuleContext(ProofParser.IdContext,0)


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
        self.enterRule(localctx, 64, self.RULE_parameterizedGame)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 599
            self.id_()
            self.state = 600
            self.match(ProofParser.L_PAREN)
            self.state = 602
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & -8938532553488695296) != 0) or ((((_la - 71)) & ~0x3f) == 0 and ((1 << (_la - 71)) & 2035) != 0):
                self.state = 601
                self.argList()


            self.state = 604
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


    class GroupTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def GROUP(self):
            return self.getToken(ProofParser.GROUP, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGroupType" ):
                return visitor.visitGroupType(self)
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


    class GroupElemTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def groupelem(self):
            return self.getTypedRuleContext(ProofParser.GroupelemContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGroupElemType" ):
                return visitor.visitGroupElemType(self)
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


    class FunctionTypeContext(TypeContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ProofParser.TypeContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def FUNCTION(self):
            return self.getToken(ProofParser.FUNCTION, 0)
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
            if hasattr( visitor, "visitFunctionType" ):
                return visitor.visitFunctionType(self)
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
        _startState = 66
        self.enterRecursionRule(localctx, 66, self.RULE_type, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 647
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,49,self._ctx)
            if la_ == 1:
                localctx = ProofParser.SetTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 607
                self.set_()
                pass

            elif la_ == 2:
                localctx = ProofParser.BoolTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 608
                self.match(ProofParser.BOOL)
                pass

            elif la_ == 3:
                localctx = ProofParser.VoidTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 609
                self.match(ProofParser.VOID)
                pass

            elif la_ == 4:
                localctx = ProofParser.MapTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 610
                self.match(ProofParser.MAP)
                self.state = 611
                self.match(ProofParser.L_ANGLE)
                self.state = 612
                self.type_(0)
                self.state = 613
                self.match(ProofParser.COMMA)
                self.state = 614
                self.type_(0)
                self.state = 615
                self.match(ProofParser.R_ANGLE)
                pass

            elif la_ == 5:
                localctx = ProofParser.ArrayTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 617
                self.match(ProofParser.ARRAY)
                self.state = 618
                self.match(ProofParser.L_ANGLE)
                self.state = 619
                self.type_(0)
                self.state = 620
                self.match(ProofParser.COMMA)
                self.state = 621
                self.integerExpression(0)
                self.state = 622
                self.match(ProofParser.R_ANGLE)
                pass

            elif la_ == 6:
                localctx = ProofParser.FunctionTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 624
                self.match(ProofParser.FUNCTION)
                self.state = 625
                self.match(ProofParser.L_ANGLE)
                self.state = 626
                self.type_(0)
                self.state = 627
                self.match(ProofParser.COMMA)
                self.state = 628
                self.type_(0)
                self.state = 629
                self.match(ProofParser.R_ANGLE)
                pass

            elif la_ == 7:
                localctx = ProofParser.IntTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 631
                self.match(ProofParser.INTTYPE)
                pass

            elif la_ == 8:
                localctx = ProofParser.ProductTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 632
                self.match(ProofParser.L_SQUARE)
                self.state = 633
                self.type_(0)
                self.state = 636 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 634
                    self.match(ProofParser.COMMA)
                    self.state = 635
                    self.type_(0)
                    self.state = 638 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==25):
                        break

                self.state = 640
                self.match(ProofParser.R_SQUARE)
                pass

            elif la_ == 9:
                localctx = ProofParser.BitStringTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 642
                self.bitstring()
                pass

            elif la_ == 10:
                localctx = ProofParser.ModIntTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 643
                self.modint()
                pass

            elif la_ == 11:
                localctx = ProofParser.GroupElemTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 644
                self.groupelem()
                pass

            elif la_ == 12:
                localctx = ProofParser.GroupTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 645
                self.match(ProofParser.GROUP)
                pass

            elif la_ == 13:
                localctx = ProofParser.LvalueTypeContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 646
                self.lvalue()
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 653
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,50,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = ProofParser.OptionalTypeContext(self, ProofParser.TypeContext(self, _parentctx, _parentState))
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_type)
                    self.state = 649
                    if not self.precpred(self._ctx, 14):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 14)")
                    self.state = 650
                    self.match(ProofParser.QUESTION) 
                self.state = 655
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,50,self._ctx)

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
        _startState = 68
        self.enterRecursionRule(localctx, 68, self.RULE_integerExpression, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 664
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [54, 55, 63, 72, 81]:
                self.state = 657
                self.lvalue()
                pass
            elif token in [80]:
                self.state = 658
                self.match(ProofParser.INT)
                pass
            elif token in [77]:
                self.state = 659
                self.match(ProofParser.BINARYNUM)
                pass
            elif token in [19]:
                self.state = 660
                self.match(ProofParser.L_PAREN)
                self.state = 661
                self.integerExpression(0)
                self.state = 662
                self.match(ProofParser.R_PAREN)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 680
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,53,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 678
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,52,self._ctx)
                    if la_ == 1:
                        localctx = ProofParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 666
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 8)")
                        self.state = 667
                        self.match(ProofParser.TIMES)
                        self.state = 668
                        self.integerExpression(9)
                        pass

                    elif la_ == 2:
                        localctx = ProofParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 669
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 7)")
                        self.state = 670
                        self.match(ProofParser.DIVIDE)
                        self.state = 671
                        self.integerExpression(8)
                        pass

                    elif la_ == 3:
                        localctx = ProofParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 672
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 6)")
                        self.state = 673
                        self.match(ProofParser.PLUS)
                        self.state = 674
                        self.integerExpression(7)
                        pass

                    elif la_ == 4:
                        localctx = ProofParser.IntegerExpressionContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_integerExpression)
                        self.state = 675
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 5)")
                        self.state = 676
                        self.match(ProofParser.SUBTRACT)
                        self.state = 677
                        self.integerExpression(6)
                        pass

             
                self.state = 682
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,53,self._ctx)

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
        self.enterRule(localctx, 70, self.RULE_integerAtom)
        try:
            self.state = 689
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [54, 55, 63, 72, 81]:
                self.enterOuterAlt(localctx, 1)
                self.state = 683
                self.lvalue()
                pass
            elif token in [80]:
                self.enterOuterAlt(localctx, 2)
                self.state = 684
                self.match(ProofParser.INT)
                pass
            elif token in [19]:
                self.enterOuterAlt(localctx, 3)
                self.state = 685
                self.match(ProofParser.L_PAREN)
                self.state = 686
                self.integerExpression(0)
                self.state = 687
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
        self.enterRule(localctx, 72, self.RULE_bitstring)
        try:
            self.state = 697
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,55,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 691
                self.match(ProofParser.BITSTRING)
                self.state = 692
                self.match(ProofParser.L_ANGLE)
                self.state = 693
                self.integerExpression(0)
                self.state = 694
                self.match(ProofParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 696
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
        self.enterRule(localctx, 74, self.RULE_modint)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 699
            self.match(ProofParser.MODINT)
            self.state = 700
            self.match(ProofParser.L_ANGLE)
            self.state = 701
            self.integerExpression(0)
            self.state = 702
            self.match(ProofParser.R_ANGLE)
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
            return self.getToken(ProofParser.GROUPELEM, 0)

        def L_ANGLE(self):
            return self.getToken(ProofParser.L_ANGLE, 0)

        def lvalue(self):
            return self.getTypedRuleContext(ProofParser.LvalueContext,0)


        def R_ANGLE(self):
            return self.getToken(ProofParser.R_ANGLE, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_groupelem

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGroupelem" ):
                return visitor.visitGroupelem(self)
            else:
                return visitor.visitChildren(self)




    def groupelem(self):

        localctx = ProofParser.GroupelemContext(self, self._ctx, self.state)
        self.enterRule(localctx, 76, self.RULE_groupelem)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 704
            self.match(ProofParser.GROUPELEM)
            self.state = 705
            self.match(ProofParser.L_ANGLE)
            self.state = 706
            self.lvalue()
            self.state = 707
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
        self.enterRule(localctx, 78, self.RULE_set)
        try:
            self.state = 715
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,56,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 709
                self.match(ProofParser.SET)
                self.state = 710
                self.match(ProofParser.L_ANGLE)
                self.state = 711
                self.type_(0)
                self.state = 712
                self.match(ProofParser.R_ANGLE)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 714
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
        self.enterRule(localctx, 80, self.RULE_bool)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 717
            _la = self._input.LA(1)
            if not(_la==75 or _la==76):
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
        self.enterRule(localctx, 82, self.RULE_moduleImport)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 719
            self.match(ProofParser.IMPORT)
            self.state = 720
            self.match(ProofParser.FILESTRING)
            self.state = 723
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==67:
                self.state = 721
                self.match(ProofParser.AS)
                self.state = 722
                self.match(ProofParser.ID)


            self.state = 725
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

        def GROUP(self):
            return self.getToken(ProofParser.GROUP, 0)

        def GROUPELEM(self):
            return self.getToken(ProofParser.GROUPELEM, 0)

        def getRuleIndex(self):
            return ProofParser.RULE_id

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitId" ):
                return visitor.visitId(self)
            else:
                return visitor.visitChildren(self)




    def id_(self):

        localctx = ProofParser.IdContext(self, self._ctx, self.state)
        self.enterRule(localctx, 84, self.RULE_id)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 727
            _la = self._input.LA(1)
            if not(((((_la - 54)) & ~0x3f) == 0 and ((1 << (_la - 54)) & 134218243) != 0)):
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
        self._predicates[29] = self.expression_sempred
        self._predicates[33] = self.type_sempred
        self._predicates[34] = self.integerExpression_sempred
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
         




