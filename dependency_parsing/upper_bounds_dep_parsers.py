"""
-Identify upper bound of parser combination
-count a token as correctly parsed if one of the parser has it right
author: don.tuggener@gmail.com
""" 

import pdb
import sys
from collections import defaultdict

""" Settings, loading, initializing, and sanity checks """

""" Set the indexes of the relevant columns if not standard CoNLL """
gold_dep_index, gold_label_index = 6, 7	# index in the CoNLL format
res_dep_index, res_label_index = 6, 7	# parsey mcparseface
#res1_dep_index, res1_label_index = 5, 6	# stanford
#res2_dep_index, res2_label_index = 5, 6	# stanford
#res2_dep_index, res2_label_index = 6, 7	# parsey mcparseface

""" Evaluate punctuation? """
skip_punct = True

def usage():
	print >> sys.stderr, '* Usage: python parser_combination_upper_bound.py gold_file parser_file1 parser_file2 parser_file3 ...'
	print >> sys.stderr, '* Format in files: CoNLL'
	print >> sys.stderr, '* author: don.tuggener@gmail.com'

if len(sys.argv) < 4:
	print >> sys.stderr, '* Provide at least one key and two response files!\n'
	usage()
	sys.exit()

key_file = sys.argv[1]
key = open(key_file).readlines()

responses = defaultdict(list)	# reponses[res1][lines]
for res in sys.argv[2:]: 
	responses[res] = open(res).readlines()
	if not len(responses[res]) == len(key):	# Sanity check
		print >> sys.stderr, '*',res, 'does not have the same number of lines as the key', key_file,' - Please align!'
		sys.exit()

""" Start counting """
eval_correct_tok = defaultdict(lambda: defaultdict(int))	# counter of correct labels per response, e.g. eval_correct_tok[res1]['NN'] = 9
tokens = 0
difficult_tokens = defaultdict(list)	# difficult_tokens['NN'] = [20, 30], i.e. line number of the tokens
all_sents, correct_sents = 0, 0
all_toks_correct = True

for i in range(len(key)):

	sys.stderr.write('\rLines: '+str(i)); sys.stderr.flush()

	key_line = key[i]
	key_line = key_line.strip()
	if key_line == '':	# Sentence delimiter, check if the full sentence was parsed correctly
		all_sents += 1
		if all_toks_correct: correct_sents += 1
		all_toks_correct = True
		continue

	key_line = key_line.split('\t')
	gold_dep_parent, gold_label = key_line[gold_dep_index], key_line[gold_label_index].lower()
	if gold_label == 'punct' and skip_punct: continue

	tokens += 1
	eval_correct_tok[key_file][gold_label] += 1	# For pos counting in the gold standard


	"""	
	# AS
	all_res_dep_parent_gold_label  = [ responses[res][i].strip().split('\t')[res_dep_index] for res in responses ]
	if gold_dep_parent in all_res_dep_parent_gold_label: eval_correct_tok['res'][gold_label] += 1	# At least one is right

	# LS
	all_res_dep_parent_gold_label  = [ responses[res][i].strip().split('\t')[res_label_index].lower() for res in responses ]
	if gold_label in all_res_dep_parent_gold_label: eval_correct_tok['res'][gold_label] += 1	# At least one is right
	"""
	# LAS
	all_res_dep_parent_gold_label  = [ (responses[res][i].strip().split('\t')[res_dep_index], responses[res][i].strip().split('\t')[res_label_index].lower()) for res in responses ]
	if (gold_dep_parent, gold_label) in all_res_dep_parent_gold_label: eval_correct_tok['res'][gold_label] += 1	# At least one is right
	else:
		"""
		print
		print key_line, all_res_dep_parent_gold_label
		#print key[i-5:i+5]
		print key[i-10:i]
		print key[i].strip()
		print key[i+1:i+9]
		pdb.set_trace()
		"""
		all_toks_correct = False
		difficult_tokens[gold_label].append(i)

sys.stderr.write('\n\n')

""" Evaluate """
print 'Upper bound of system combination:',
all_correct_labels = sum(eval_correct_tok['res'].values())
print "{0:.2f}".format( 100. * all_correct_labels / tokens ), '% (' + str(all_correct_labels) + '/' + str(tokens) + ')\t'

print

print 'Correctly labeled sentences:\t', "{0:.2f}".format( 100. * correct_sents / all_sents ), '(' + str(correct_sents) + '/' + str(all_sents) + ')'


# Accuracy per pos tag, most frequent first
print 'Accuracy per pos:'
sorted_pos = sorted( [ (count, pos) for pos,count  in eval_correct_tok[key_file].iteritems() ], reverse = True )
for count, pos in sorted_pos:
	print '%-10s' % pos,
	print '%-10s' % "{0:.2f}".format( 100. * eval_correct_tok['res'][pos] / eval_correct_tok[key_file][pos] ),
	print '(' + str(eval_correct_tok['res'][pos]) + '/' + str(eval_correct_tok[key_file][pos]) + ')'
"""
print

# Print erroneous token lines sorted by highest frequency of the pos
print 'Most difficult PoS tags, sorted by error frequency (and list of line numbers of the errors)' 
sorted_diffifult_tokens = sorted( [ (len(lines), pos) for pos, lines in difficult_tokens.iteritems()], reverse = True )
for len_lines, pos in sorted_diffifult_tokens:
	print pos, len_lines, ','.join( [ str(x) for x in difficult_tokens[pos] ])
"""
