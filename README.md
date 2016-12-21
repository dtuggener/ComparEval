# ComparEval - A toolkit for comparative evaluation of outputs of two or more NLP systems 

Implementations of the evaluation methods decribed in:

Tuggener, Don (2017). *A method for in-depth comparative evaluation: How (dis)similar are outputs of pos taggers, dependency parsers and coreference resolvers really?* In: Proceedings of EACL 2017. (to appear)

**TL;DR**: The method compares two (or more) system outputs to a gold standard and quantifies and highlights the differences between the outputs. Also, it can create upper bounds for system output combinations.

Currently supported are: POS tagging, dependecy parsing, and coreference resolution.

### Usage ###
Each supported task has two python scripts to perform the evaluation. To compare e.g. two POS tagger outputs, run:
```
python pos_tagging/compare_pos_taggers.py <gold_standard_file> <system_output1_file> <system_output2_file>
```
Accordingly, to calculate the upper bounds, run:
```
python pos_tagging/upper_bounds_pos_taggers.py <gold_standard_file> <system_output1_file> <system_output2_file> <system_output3_file> ...
```

The input format is CoNLL (i.e. one token per line). Set the column indexes of the relevant features (e.g. column index of the POS tags) at the beginning of the scripts if they don't match your CoNLL format (For coreference resolution, it is always the last column).

