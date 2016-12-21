"""
Compare n system responses to a key using tp,fp,fn,wl
Usage: python compare_n_sys_responses.py key_file.conll response_file1.conll response_file2.conll ...
author: Don Tuggener
"""

import re,sys,pdb
from collections import defaultdict, Counter

# ===================================================================== #

""" SETTINGS """

# Language
lang='ENG'  # GER or ENG

if lang=='GER':
    # German TuebaD/Z
    noun_pos_tags=['NN','NE']   
    pronoun_pos_tags=['PPER','PPOSAT','PRELS','PDS','PRELAT']
    pos_index=4 # Index of the POS tag, i.e. the nth column in the CoNLL format, counting from 0
    lexem_index=6   # Index of the lexem/lemma
    
if lang=='ENG':
    # English CoNLL 2012
    noun_pos_tags=['NN','NNS','NNP','NNPS']   
    pronoun_pos_tags=['PRP','PRP$']   
    pos_index=4
    lexem_index=3

# Antecedent requirement
# 'any': mention has an ante that is in key chain
# 'nominal': mention's closest nominal ante is in key chain
ante_require='nominal'
print >> sys.stderr, 'Using', ante_require, 'antecedent criterion'

trace=False #stop at tracing points

# ===================================================================== #

""" LOADING """

all_key=re.split('#end document[^\n]*',open(sys.argv[1],'r').read())    #split documents at lines starting with "#end document", consume everything except newline
if re.match('\n+',all_key[-1]): del all_key[-1]                         #splitting artefacts
response_files=sys.argv[2:]
response_docs=defaultdict(list)
for res in response_files:
    all_res1=re.split('#end document[^\n]*',open(res,'r').read())
    if re.match('\n+',all_res1[-1]): del all_res1[-1]
    response_docs[res]=all_res1

doc_ids=[]                                                              #document names
docs=defaultdict(lambda:defaultdict(dict))

for doc in all_key:
    if not doc.lstrip().startswith('#begin'):
        print "No '#begin document...' at key document beginning"       #every doc should start with that
        pdb.set_trace()
    else:
        key=re.sub('\n{3,}','\n\n',doc)                                 #normalize multiple newlines
        key=key.lstrip().split('\n')                                    #lstrip to remove newlines at document beginning    
        docid=re.search('#begin document ([^\n]+)',key[0]).group(1)
        docs['key'][docid]=key
        doc_ids.append(docid)

for res,res_docs in response_docs.items():
    for doc in res_docs:
        if not doc.lstrip().startswith('#begin'):
            print "No '#begin document...' at response document beginning"
            pdb.set_trace()
        else:
            res_doc=re.sub('\n{3,}','\n\n',doc)
            res_doc=res_doc.lstrip().split('\n')
            docid=re.search('#begin document ([^\n]+)',res_doc[0]).group(1)
            docs[res][docid]=res_doc

# ===================================================================== #

""" FUNCTIONS """

def get_coref(key):
    """
    Return dict of coreference sets. Mentions are lists; pronoun mentions are of length 5, noun mentions of length 3.
    Store line number, mention token start and end id, PoS tag and lexem for each mention.
    PoS tag and lexem only for single word terms, multi-word terms are considered nouns and their lexem is not stored.
    """
    key_sets=defaultdict(list)
    line_nr=0
    for line in key:
        line_nr+=1
        if line.startswith('#') or line=='': token_nr=1 #new document or new sentence                       
        elif not line.endswith('-') and not line.endswith('_'): #coreference information
            line=re.split(' +|\t',line) #mutliple spaces and tab separation for robustness
            ids=line[-1].strip().split('|')
            for id_str in ids:            
                id_int=re.search('\d+',id_str).group()  #numeric coref id                
                if id_str.startswith('(') and id_str.endswith(')'): #single word term                    
                    key_sets[id_int].append([line_nr,token_nr,token_nr,line[pos_index],line[lexem_index]])
                elif id_str.startswith('('):    #start of multiple word term
                    key_sets[id_int].append([line_nr,token_nr]) #add an incomplete mention, i.e. only sentence number and token start id
                elif id_str.endswith(')'):  #end of multi word term
                    for m in key_sets[id_int]:  #find the open mention in the chain
                        if len(m)==2: 
                            m.append(token_nr)  #and append token end id
                            break                        
            token_nr+=1            
        else: token_nr+=1
    return key_sets

def classify_mention(key_m,cset,res_sets,ante_require):
    """ Return mention classification TP, FP, ... """
    res_set1=[c for c in res_sets if key_m in c]          
    if res_set1==[]:                                             #key mention is not in the reponse -> false negative
        type_res='fn'
    elif len(res_set1)>1:                                        #key mention is in multiple response sets -> abort evaluation
        print 'Mention in multiple chains. Mention:',key_m
        print 'Response chains:'
        for c in res_set1: print c
        pdb.set_trace()
    else:
        res_set1=res_set1[0]
        #the mention is the chain starter in the response, but not in the key 
        #-> recall error, it is anaphoric in the key, but not in the response -> false negative
        if res_set1.index(key_m)==0:
            type_res='fn'
        else:                                                   #we have exactly one response chain containing the mention                 
            antes=res_set1[:res_set1.index(key_m)]   
            key_antes=cset[:cset.index(key_m)]

            if ante_require=='any':            #any res_ante is a key_ante
                try: 
                    next(a for a in antes if a in key_antes)   
                    type_res='tp'
                except StopIteration: 
                    type_res='wl'  

            if ante_require=='nominal':
                #closest nominal ante is correct
                nominal_antes=[m for m in antes if len(m)==3 or m[3] in noun_pos_tags]
                if nominal_antes==[]:
                    type_res='fn'
                else:
                    if nominal_antes[-1] in key_antes:
                        type_res='tp'
                    else:                          
                        type_res='wl'     

                """
                # This requires the closest nominal response ante to be the same as the closest nominal key ante, which we don't want,
                # I.e. we only want the closest nominal response ante to be in the key chain
                try: key_nom_ante=next(a for a in key_antes if len(a)==3 or a[3] in noun_pos_tags)  #does key have a nominal ante?
                except StopIteration: key_nom_ante=[]
                try: res_nom_ante=next(a for a in antes if len(a)==3 or a[3] in noun_pos_tags)  #does res have a nominal ante?
                except StopIteration: res_nom_ante=[]    
                if key_nom_ante==[]:
                    if res_nom_ante==[]: type_res='tn'
                    else: type_res='fp'
                else:
                    if res_nom_ante==[]: type_res='fn'            
                    elif res_nom_ante in key_antes: type_res='tp'
                    else: type_res='wl'
                """

            """
            # Other possible criteria for antecedent
            #immediate res ante is also immediate key ante
            if res_set1[res_set1.index(key_m)-1]==cset[cset.index(key_m)-1]: type_res='tp'
            else: type_res='wl'

            #immediate res_ante is a key ante
            if res_set1[res_set1.index(key_m)-1] in key_antes: type_res='tp'
            else: type_res='wl'
            """
            
    return type_res  

# ===================================================================== #

""" COUNTING """

all_classifications=defaultdict(int)
all_classifications_pos=defaultdict(lambda: defaultdict(int))
           
for doc in doc_ids:                                                     #for each document name in the key

    print >> sys.stderr, doc
    key=docs['key'][doc]
    key_sets=get_coref(key)                 #gather key and response sets
    key_sets=sorted(key_sets.values())      #turn key and response into sorted list of lists    
    responses_coref=defaultdict(list)
    for res in response_files:
        tmp_coref=get_coref(docs[res][doc])
        responses_coref[res]=sorted(tmp_coref.values())

    for cset in key_sets:                                               #for every chain in the key
        if len(cset)==1: continue                                       #singleton, ommit

        if ante_require == 'nominal':
            try: next(m for m in cset if len(m)==3 or m[3] in noun_pos_tags)    # noun in cset
            except StopIteration: continue    #no nouns, omit
        
        for key_m in cset[1:]:                                          #for every mention in the chain except the first one
            
            if ante_require == 'nominal':   #no nominal ante for key_m -> cataphora, omit
                if [m for m in cset[:cset.index(key_m)] if len(m)==3 or m[3] in noun_pos_tags]==[]:# and pos in pronoun_pos_tags:
                    #cataphora+=1
                    continue

            #determine POS tag of the mention:
            pos=key_m[3] if len(key_m)==5 and not key_m[3] in noun_pos_tags else 'NOUN'
          
            classifications=defaultdict(str)            
            
            for res,res_coref in responses_coref.items():
                res_type=classify_mention(key_m,cset,res_coref,ante_require)
                classifications[res]=res_type
            all_classifications[tuple(sorted(classifications.values()))]+=1
            all_classifications_pos[pos][tuple(sorted(classifications.values()))]+=1


            if trace:
                # Some criteria for inspecting specific gold mentions:
                #if len(set(classifications.values()))>1:    #at leat two responses disagree
                #if len(set(classifications.values()))==len(response_files):    #all disagree
                #if len(set(classifications.values()))==1:    #all agree
                if not 'tp' in classifications.values():    #not one resolves it correctly
                #if set(classifications.values())==set(['tp']) and pos in ['PRP','PRP$'] and not key_m[-1].lower() in ['i','me','you']:
                #if set(classifications.values())==set(['wl']):  #all wrong linkages
                    print '\n',doc
                    print key_m,'in', cset                
                    for i in range(-1,key_m[2]-key_m[1]): print key[key_m[0]+i] #print the mention
                    print dict(classifications)
                    pdb.set_trace()

# ===================================================================== #

""" EVALUATION """

#Hypothetical upper bound for perfect system combination

sys.stderr.write('\n')

print 'Using', ante_require, 'antecedent criterion:\n'
print '='*38
print 'Mention type-based recall upper bound:'
print '='*38

sorted_pos = [(sum(counts.values()),pos) for pos, counts in all_classifications_pos.iteritems()]
sorted_pos.sort(reverse = True)
one_tp, mention_count = 0, 0
for pos_cases, pos in sorted_pos:
    correct = 0
    mention_count += pos_cases
    for classification, c in all_classifications_pos[pos].iteritems():
        if 'tp' in classification: correct += c
    print pos,'\t', "{0:0.2f}".format(100.*correct/pos_cases), '\t(',correct,'/',pos_cases,')'
    one_tp += correct

print 
print '='*50    
print 'Overall recall upper bound:', "{0:0.2f}".format( 100.* one_tp / mention_count ), '(',one_tp,'/',mention_count,')'
print '='*50

#print 'ALL classification configurations'
#for k,v in all_classifications.items(): print k,v           
