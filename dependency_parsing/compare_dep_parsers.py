"""
-Compare two dependency parsers to gold key
-Track transitions of pos tags from tagger 1 to tagger 2
-see usage()
author: don.tuggener@gmail.com
""" 

import pdb
import sys
from collections import defaultdict

""" Set the indexes of the relevant columns if not standard CoNLL """
gold_dep_index, gold_label_index = 6, 7	# index in the CoNLL format
res1_dep_index, res1_label_index = 5, 6	# stanford PCFG
res2_dep_index, res2_label_index = 5, 6	# stanford NN
#res2_dep_index, res2_label_index = 6, 7	# parsey mcparseface

""" Evaluate punctuation? """
skip_punct = True

""" Loading, initializing, and sanity checks """
def usage():
	print >> sys.stderr, '* Usage: python compare_dep_parsers.py gold_file parsed_file1 parsed_file2'
	print >> sys.stderr, '* Format in files: CoNLL; see indexes of dependency parent and grammatical label'
	print >> sys.stderr, '* author: don.tuggener@gmail.com'

# Sanity check
if len(sys.argv) != 4:
	print >> sys.stderr, '* Too many or too few command line arguments!\n'
	usage()
	sys.exit()

key_file, res1_file, res2_file = sys.argv[1], sys.argv[2], sys.argv[3]

key = open(key_file).readlines()
res1 = open(res1_file).readlines()
res2 = open(res2_file).readlines()

# Sanity check
if not len(key) == len(res1):
	print >> sys.stderr, '* Key and', res1_file,'do not have the same number of lines. Please align!'
	sys.exit() 
if not len(key) == len(res2):
	print >> sys.stderr, '* Key and', res2_file, 'do not have the same number of lines. Please align!'
	sys.exit()

""" Start counting """
eval_correct_toks = defaultdict(lambda: defaultdict(int))	# counter of correct labels per response, e.g. eval_correct_toks[res1]['nsubj'] = 9
new_errors = defaultdict(int)		# errors that tagger 2 introduces
changed_errors = defaultdict(int)	# errors that tagger 2 changes to other errors
corrections = defaultdict(int)		# corrections that tagger 2 introduces
tokens = 0

for i, (key_line, res_line1, res_line2) in enumerate(zip(key, res1, res2), 1):

	sys.stderr.write('\rLines: '+str(i)); sys.stderr.flush()

	key_line = key_line.strip()
	if key_line == '': continue	# Sentence delimiter, skip

	key_line = key_line.split('\t')
	res_line1 = res_line1.strip().split('\t')
	res_line2 = res_line2.strip().split('\t')

	# Read the dep parents and gram. labels
	try:
		gold_dep_parent, gold_label = key_line[gold_dep_index], key_line[gold_label_index].lower()
		res1_dep_parent, res1_label = res_line1[res1_dep_index], res_line1[res1_label_index].lower()
		res2_dep_parent, res2_label = res_line2[res2_dep_index], res_line2[res2_label_index].lower()
	except IndexError:
		print '\n* Cannot access CoNLL column. Did you set the CoNLL column indexes correctly for all input files?'
		sys.exit()

	if gold_label == 'punct' and skip_punct: continue	# skip evaluation of punctuation, see settings above 

	eval_correct_toks[key_file][gold_label] += 1	# for label counting in the gold standard

	if not (res1_dep_parent, res1_label) == (res2_dep_parent, res2_label):	# output is different
		if (res2_dep_parent, res2_label) == (gold_dep_parent, gold_label): 	# res2 is correct
			corrections[(res1_label, res2_label)] += 1
			eval_correct_toks[res2_file][gold_label] += 1
		elif (res1_dep_parent, res1_label) == (gold_dep_parent, gold_label):	#res1 is correct
			new_errors[(res1_label, res2_label)] += 1
			eval_correct_toks[res1_file][gold_label] += 1
		else: changed_errors[(gold_label, res1_label, res2_label)] += 1

	elif (gold_dep_parent, gold_label) == (res1_dep_parent, res1_label) == (res2_dep_parent, res2_label):	# both responses are correct
		eval_correct_toks[res1_file][gold_label] += 1
		eval_correct_toks[res2_file][gold_label] += 1

	tokens += 1

sys.stderr.write('\n\n')

""" Start comparing """
corrections_count = sum(corrections.values())
new_errors_count = sum(new_errors.values())
changed_errors_count = sum(changed_errors.values())
all_changes_count = corrections_count + new_errors_count + changed_errors_count

print 'Accuracy of the systems:'
for f in eval_correct_toks:
	if f == key_file: continue
	correct_toks = sum(eval_correct_toks[f].values())
	print f+':\t', "{0:.2f}".format( 100. * correct_toks / tokens ), '% (' + str(correct_toks) + '/' + str(tokens) + ')'

print

print 'Overall percentage of different labels between', sys.argv[2], 'and',sys.argv[3]+':\t', 
print "{0:.2f}".format( 100. * all_changes_count / tokens ), '% (' + str(all_changes_count) + '/' + str(tokens) + ')'
print 'of which are'
print "{0:.2f}".format( 100. * corrections_count / all_changes_count ), '% (' + str(corrections_count) + '/' + str(all_changes_count) + ')', 'corrections'
print "{0:.2f}".format( 100. * new_errors_count / all_changes_count ), '% (' + str(new_errors_count) + '/' + str(all_changes_count) + ')', 'new errors'
print "{0:.2f}".format( 100. * changed_errors_count / all_changes_count ), '% (' + str(changed_errors_count) + '/' + str(all_changes_count) + ')', 'changed errors'

print

sorted_corrections = sorted( [ (corrections[corr], corr, 'correction') for corr in corrections], reverse = True)
sorted_new_errors = sorted( [ (new_errors[err], err, 'new error') for err in new_errors], reverse = True)
sorted_changed_errors = sorted( [ (changed_errors[err], err, 'changed error') for err in changed_errors], reverse = True)

print 'Changes by type (sorted by frequency per type)'
print '\ncorrections:'
for change in sorted_corrections:
	print '%-20s' % ' -> '.join(change[1]),
	print "{0:.2f}".format( 100. * change[0] / corrections_count ), '% (' + str(change[0]) + '/' + str(corrections_count) + ')\t',
	print "{0:.2f}".format( 100. * change[0] / all_changes_count ), '% (' + str(change[0]) + '/' + str(all_changes_count) + ')\t'
print '\nnew errors:'
for change in sorted_new_errors:
	print '%-20s' % ' -> '.join(change[1]),
	print "{0:.2f}".format( 100. * change[0] / new_errors_count ), '% (' + str(change[0]) + '/' + str(new_errors_count) + ')\t',
	print "{0:.2f}".format( 100. * change[0] / all_changes_count ), '% (' + str(change[0]) + '/' + str(all_changes_count) + ')\t'
print '\nchanged errors:'	
for change in sorted_changed_errors:
	print '%-25s' % ' -> '.join(change[1]),
	print "{0:.2f}".format( 100. * change[0] / changed_errors_count ), '% (' + str(change[0]) + '/' + str(changed_errors_count) + ')\t',
	print "{0:.2f}".format( 100. * change[0] / all_changes_count ), '% (' + str(change[0]) + '/' + str(all_changes_count) + ')\t'

print 

all_changes = sorted( sorted_corrections + sorted_new_errors + sorted_changed_errors, reverse = True )
print 'Label changes by frequency:'
for change in all_changes:
	print '%-25s' % ' -> '.join(change[1]),
	print "{0:.2f}".format( 100. * change[0] / all_changes_count ), '% (' + str(change[0]) + '/' + str(all_changes_count) + ')\t', change[2]

print

print 'Accuracy differences per label (biggest difference first):'
acc_diffs = []
for pos in eval_correct_toks[key_file]:
	res1_acc = 100. * eval_correct_toks[res1_file][pos] / eval_correct_toks[key_file][pos]
	res2_acc = 100. * eval_correct_toks[res2_file][pos] / eval_correct_toks[key_file][pos]
	acc_diffs.append( (abs(res2_acc - res1_acc), res2_acc - res1_acc, res1_acc, res2_acc, pos, eval_correct_toks[key_file][pos] ) )

for acc_diff in sorted(acc_diffs, reverse = True):
	if acc_diff[1] > 0: print '+' + "{0:.2f}".format(acc_diff[1]),'\t',
	else: print "{0:.2f}".format(acc_diff[1]), '\t',
	for x in acc_diff[2:4]: print "{0:.2f}".format(x),'\t',
	#for x in acc_diff[1:4]: print "{0:.2f}".format(x),'\t',
	print '\t'.join(str(x) for x in acc_diff[-2:])