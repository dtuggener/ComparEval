"""
Evaluate dependency parser
-calculate unlabeled attachment accuracy (uas), label accuracy (las), and labeled attachement score
-calculate accuracy per dependency label and list errors
-count number of sentences where all labels are correct
-see usage()
author: don.tuggener@gmail.com
""" 

import pdb
import sys
from collections import defaultdict

""" Set the indexes of the relevant columns if not standard CoNLL """
gold_dep_index, gold_label_index = 6, 7	# index in the CoNLL format
#res_dep_index, res_label_index = 5, 6	# stanford
res_dep_index, res_label_index = 6, 7	# parsey mcparseface

""" Evaluate punctuation? """
skip_punct = True

""" Loading, initializing, and sanity checks """
def usage():
	print >> sys.stderr, '* Usage: python eval_dep_parse.py gold_file tagger_file'
	print >> sys.stderr, '* Format in files: conll'
	print >> sys.stderr, '* author: don.tuggener@gmail.com'

# Sanity check
if len(sys.argv) != 3:
	print >> sys.stderr, '* Too many or too few command line arguments!'
	usage()
	sys.exit()

key = open(sys.argv[1]).readlines()
res = open(sys.argv[2]).readlines()

# Sanity check
if not len(key) == len(res):
	print >> sys.stderr, '* Key and response do not have the same number of lines. Please align!'
	sys.exit()

""" Start counting """
eval_label = defaultdict(lambda: defaultdict(int))	# e.g. eval_label['nsubj']['correct'] = 9; eval_label['nsubj']['cases'] = 10
eval_errors = defaultdict(int) # e.g. eval_errors[('nsubj','dobj')] = 10
all_sents, correct_sents = 0, 0
all_labels_correct = True	# control variable to check whether all dep labels in a sentence are correct

# Enumerate and zip lines in key and response
for i, (key_line, res_line) in enumerate(zip(key, res), 1):

	sys.stderr.write('\rLines: '+str(i)); sys.stderr.flush()

	key_line = key_line.strip()
	
	if key_line == '':	# Sentence delimiter, check if the full sentence was parsed correctly
		all_sents += 1
		if all_labels_correct: correct_sents += 1
		all_labels_correct = True
		continue

	key_line = key_line.split('\t')
	res_line = res_line.strip().split('\t')

	gold_label, gold_dep = key_line[gold_label_index].lower(), key_line[gold_dep_index]
	if gold_label == 'punct' and skip_punct: continue	# skip evaluation of punctuation, see settings above 
	res_label, res_dep = res_line[res_label_index].lower(), res_line[res_dep_index]

	#if gold_label == res_label: eval_label[gold_label]['correct'] += 1	# label
	#if gold_dep == res_dep: eval_label[gold_label]['correct'] += 1	# attachment
	if (gold_dep, gold_label) == (res_dep, res_label): eval_label[gold_label]['correct'] += 1	# label + attachment
	else: 
		eval_errors[(gold_label, res_label)] += 1
		all_labels_correct = False

	eval_label[gold_label]['cases'] += 1

sys.stderr.write('\n\n')

""" Calculate scores """
# Overall accuracy: correct / cases
cases = sum( eval_label[label]['cases'] for label in eval_label )
correct = sum( eval_label[label]['correct'] for label in eval_label )
print 'Overall accuracy:\t', "{0:.2f}".format( 100. * correct / cases ), '(' + str(correct) + '/' + str(cases) + ')'
print

# Correctly tagged sentences
print 'Correctly labeled sentences:\t', "{0:.2f}".format( 100. * correct_sents / all_sents ), '(' + str(correct_sents) + '/' + str(all_sents) + ')'
print

# Accuracy per label, most frequent first
print 'Accuracy per label (sorted by frequency of the label):'
sorted_label = sorted( [ (eval_label[label]['cases'], label) for label in eval_label ], reverse = True )
for count, label in sorted_label:
	print '%-10s' % label,
	print '%-10s' % "{0:.2f}".format( 100. * eval_label[label]['correct'] / eval_label[label]['cases'] ),
	print '(' + str(eval_label[label]['correct']) + '/' + str(eval_label[label]['cases']) + ')'
print

# Errors, most frequent first
print 'Errors (Percentages of all errors):'
errors = sum( eval_errors.values() )
sorted_errors = sorted( [ (eval_errors[err], err) for err in eval_errors ], reverse = True )
for count, err in sorted_errors:
	print '%-20s' % ' -> '.join((err[0], err[1])),
	print '%-10s' % "{0:.2f}".format( 100. * count / errors ),
	print '(' + str(count) + '/' + str(errors) + ')'
