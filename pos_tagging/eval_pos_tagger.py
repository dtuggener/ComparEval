"""
Evaluate pos tagger
-calculate Accuracy per pos tag and list errors
-count number of sentences where all pos tags are correct
-see usage()
author: don.tuggener@gmail.com
""" 

import sys
from collections import defaultdict

""" Settings """
pos_index = 1	# Set the index of the pos column in the CoNLL files

""" Loading, initializing, and sanity checks """
def usage():
	print >> sys.stderr, '* Usage: python eval_pos_tagger.py gold_file tagger_file'
	print >> sys.stderr, '* Format in files: One token per line, token and pos tag, separated by tab, i.e.:'
	print >> sys.stderr, '* token\tpos_tag'
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
eval_pos = defaultdict(lambda: defaultdict(int))	# e.g. eval_pos['NN']['correct'] = 9; eval_pos['NN']['cases'] = 10
eval_errors = defaultdict(int) # e.g. eval_errors[('VVFIN','VVINF')] = 10
all_sents, correct_sents = 0, 0
all_pos_correct = True	# control variable to check whether all pos tags in a sentence are correct

# Enumerate and zip lines in key and response
for i, (key_line, res_line) in enumerate(zip(key, res), 1):

	sys.stderr.write('\rLines: '+str(i)); sys.stderr.flush()

	key_line = key_line.strip()
	if key_line == '': 
		all_sents += 1
		if all_pos_correct: correct_sents += 1
		all_pos_correct = True
		continue	# Sentence delimiter, skip

	key_line = key_line.split('\t')
	res_line = res_line.strip().split('\t')

	gold_pos = key_line[pos_index]
	res_pos = res_line[pos_index]

	eval_pos[gold_pos]['cases'] += 1
	if gold_pos == res_pos: eval_pos[gold_pos]['correct'] += 1
	else: 
		eval_errors[(gold_pos, res_pos)] += 1
		all_pos_correct = False

sys.stderr.write('\n\n')

""" Calculate scores """
# Overall accuracy: correct / cases
cases = sum( eval_pos[pos]['cases'] for pos in eval_pos )
correct = sum( eval_pos[pos]['correct'] for pos in eval_pos )
print 'Overall accuracy:\t', "{0:.2f}".format( 100. * correct / cases ), '(' + str(correct) + '/' + str(cases) + ')'
print

# Correctly tagged sentences
print 'Correctly tagged sentences:\t', "{0:.2f}".format( 100. * correct_sents / all_sents ), '(' + str(correct_sents) + '/' + str(all_sents) + ')'
print

# Accuracy per pos tag, most frequent first
print 'Accuracy per pos tag (sorted by frequency of the tag):'
sorted_pos = sorted( [ (eval_pos[pos]['cases'], pos) for pos in eval_pos ], reverse = True )
for count, pos in sorted_pos:
	print '%-10s' % pos,
	print '%-10s' % "{0:.2f}".format( 100. * eval_pos[pos]['correct'] / eval_pos[pos]['cases'] ),
	print '(' + str(eval_pos[pos]['correct']) + '/' + str(eval_pos[pos]['cases']) + ')'
print

# Errors, most frequent first
print 'Errors (Percentages of all errors):'
errors = sum( eval_errors.values() )
sorted_errors = sorted( [ (eval_errors[err], err) for err in eval_errors ], reverse = True )
for count, err in sorted_errors:
	print '%-20s' % ' -> '.join((err[0], err[1])),
	print '%-10s' % "{0:.2f}".format( 100. * count / errors ),
	print '(' + str(count) + '/' + str(errors) + ')'
