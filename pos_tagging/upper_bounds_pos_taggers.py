"""
-Identify upper bound of pos tagger combination
-count a token as correctly labeled if one of the taggers has it right
author: don.tuggener@gmail.com
""" 

import pdb
import sys
from collections import defaultdict

""" Settings """
pos_index = 1	# Set the index of the pos column in the CoNLL files

""" Loading, initializing, and sanity checks """
def usage():
	print >> sys.stderr, '* Usage: python compare_pos_taggers.py gold_file tagger_file1 tagger_file2 tagger_file3 ...'
	print >> sys.stderr, '* Format in files: One token per line, token and pos tag, separated by tab, i.e.:'
	print >> sys.stderr, '* token\tpos_tag'
	print >> sys.stderr, '* author: don.tuggener@gmail.com'

if len(sys.argv) < 3:
	print >> sys.stderr, '* Provide at least one key and one response files!\n'
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
eval_correct_pos = defaultdict(lambda: defaultdict(int))	# counter of correct labels per response, e.g. eval_correct_pos[res1]['NN'] = 9
tokens = 0
difficult_tokens = defaultdict(list)	# difficult_tokens['NN'] = [20, 30], i.e. line number of the tokens

for i in range(len(key)):

	sys.stderr.write('\rLines: '+str(i)); sys.stderr.flush()

	key_line = key[i]
	key_line = key_line.strip()
	if key_line == '': continue	# Sentence delimiter, skip

	tokens += 1

	key_line = key_line.split('\t')
	gold_pos = key_line[pos_index]
	all_res_pos = [ responses[res][i].strip().split('\t')[pos_index] for res in responses ]
	
	eval_correct_pos[key_file][gold_pos] += 1	# For pos counting in the gold standard
	if gold_pos in all_res_pos: eval_correct_pos['res'][gold_pos] += 1	# At least one is right
	else:
		"""
		print
		print key_line, all_res_pos
		#print key[i-5:i+5]
		print key[i-10:i]
		print key[i].strip()
		print key[i+1:i+9]
		pdb.set_trace()
		"""
		difficult_tokens[gold_pos].append(i)

sys.stderr.write('\n\n')

""" Evaluate """
print 'Upper bound of system combination:',
all_correct_labels = sum(eval_correct_pos['res'].values())
print "{0:.2f}".format( 100. * all_correct_labels / tokens ), '% (' + str(all_correct_labels) + '/' + str(tokens) + ')\t'

print

# Accuracy per pos tag, most frequent first
print 'Accuracy per pos:'
sorted_pos = sorted( [ (count, pos) for pos,count  in eval_correct_pos[key_file].iteritems() ], reverse = True )
for count, pos in sorted_pos:
	print '%-10s' % pos,
	print '%-10s' % "{0:.2f}".format( 100. * eval_correct_pos['res'][pos] / eval_correct_pos[key_file][pos] ),
	print '(' + str(eval_correct_pos['res'][pos]) + '/' + str(eval_correct_pos[key_file][pos]) + ')'

print

"""
print

# Print erroneous token lines sorted by highest frequency of the pos
print 'Most difficult PoS tags, sorted by error frequency (and list of line numbers of the errors)' 
sorted_diffifult_tokens = sorted( [ (len(lines), pos) for pos, lines in difficult_tokens.iteritems()], reverse = True )
for len_lines, pos in sorted_diffifult_tokens:
	print pos, len_lines, ','.join( [ str(x) for x in difficult_tokens[pos] ])
"""
