"""
Compare two system responses to a key using tp,fp,fn,wl
Usage: python scorer_mentions.py key_file.conll response_file1.conll response_file2.conll
"""

import re,sys,pdb
from collections import defaultdict, Counter
import copy

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

ttest=False
if ttest:
    from scipy.stats import ttest_rel, wilcoxon

# ===================================================================== #

""" FUNCTIONS """

def get_coref(doc): #we do it not only for doc, also for responses
    doc_sets={}
    for line in doc:                                                    #process doc file line by line
        if line.startswith('#'):                                        #new document
            sent_nr=1                                                   #reset sentence/token counters
            token_nr=1                
        elif line=='': 
            sent_nr+=1                                                  #newline, i.e. new sentence
            token_nr=1            
        elif not line.endswith('-') and not line.endswith('_'):         #we have coreference information
            line=re.split(' +|\t',line)                                 #allow both mutliple spaces and tab separation for robustness
            ids=line[-1].split('|')                                     #split coref annotation             
            for id in ids:                
                if id.startswith('(') and id.endswith(')'):             #single word term
                    id=re.search('\d+',id).group()                      #numeric coref id
                    #store sentence number, mention token start and end id, PoS tag and lexem 
                    #PoS tag and lexem only for SWTs, MWTs are considered nouns and their lexem is not stored
                    if id in doc_sets: doc_sets[id].append([sent_nr,token_nr,token_nr,line[pos_index],line[lexem_index]])
                    else: doc_sets[id]=[[sent_nr,token_nr,token_nr,line[pos_index],line[lexem_index]]]              
                elif id.startswith('('):                                #start of multiple word term
                    id=re.search('\d+',id).group()                      #add an incomplete mention, i.e. only sentence number and token start id
                    if id in doc_sets: doc_sets[id].append([sent_nr,token_nr])
                    else: doc_sets[id]=[[sent_nr,token_nr]]              
                elif id.endswith(')'):                                  #end of multi word term
                    id=re.search('\d+',id).group()
                    for m in doc_sets[id]:                              #find the open mention in the chain
                        if len(m)==2: 
                            m.append(token_nr)                          #and append token end id
                            break                        
            token_nr+=1            
        else: token_nr+=1
    return doc_sets  

def classify_mention(key_m,cset,res_sets,ante_require):
    res_set1=[c for c in res_sets if key_m in c]          
    if res_set1==[]:                                             #key mention is not in the reponse -> false negative
        type_res='fn'
    elif len(res_set1)>1:                                        #key mention is in multiple response sets -> abort evaluation
        print 'Mention in multiple chains. Mention:',key_m
        print 'Response chains:'
        for c in res_set1: print c
        pdb.set_trace()
    else:
        #the mention is the chain starter in the response, but not in the key 
        #-> recall error, it is anaphoric in the key, but not in the response -> false negative
        res_set1=res_set1[0]
        if res_set1.index(key_m)==0:
            type_res='fn'
        else:                                                   #we have exactly one response chain containing the mention                 
            antes=res_set1[:res_set1.index(key_m)]   
            key_antes=cset[:cset.index(key_m)]

            if ante_require=='any':            
                #any res_ante is a key_ante
                try: 
                    next(a for a in antes if a in key_antes)   
                    type_res='tp'
                except StopIteration: 
                    type_res='wl'  

            if ante_require=='nominal':
                #closest nominal ante is correct
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
            #immediate res ante is also immediate key ante
            if res_set1[res_set1.index(key_m)-1]==cset[cset.index(key_m)-1]: type_res='tp'
            else: type_res='wl'

            #immediate res_ante is a key ante
            if res_set1[res_set1.index(key_m)-1] in key_antes: type_res='tp'
            else: type_res='wl'
            """
            
    return type_res

# ===================================================================== #

""" MAIN """

# Input document processing
all_key=re.split('#end document[^\n]*',open(sys.argv[1],'r').read())    #split documents at lines starting with "#end document", consume everything except newline
all_res1=re.split('#end document[^\n]*',open(sys.argv[2],'r').read())
all_res2=re.split('#end document[^\n]*',open(sys.argv[3],'r').read())
if re.match('\n+',all_key[-1]): del all_key[-1]                         #splitting artefacts
if re.match('\n+',all_res1[-1]): del all_res1[-1]
if re.match('\n+',all_res2[-1]): del all_res2[-1]

if len(all_key)!=len(all_res1) or len(all_key)!=len(all_res2) or len(all_res1)!=len(all_res2): 
    print 'Key and response file do not have the same number of documents.'
    pdb.set_trace()

doc_ids=[]                                                              #document names
docs={'key':{},'res1':{},'res2':{}}

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

for doc in all_res1:
    if not doc.lstrip().startswith('#begin'):
        print "No '#begin document...' at response document beginning"
        pdb.set_trace()
    else:
        res=re.sub('\n{3,}','\n\n',doc)
        res=res.lstrip().split('\n')
        docid=re.search('#begin document ([^\n]+)',res[0]).group(1)
        docs['res1'][docid]=res

for doc in all_res2:
    if not doc.lstrip().startswith('#begin'):
        print "No '#begin document...' at response document beginning"
        pdb.set_trace()
    else:
        res=re.sub('\n{3,}','\n\n',doc)
        res=res.lstrip().split('\n')
        docid=re.search('#begin document ([^\n]+)',res[0]).group(1)
        docs['res2'][docid]=res

# Start comparing
transitions=defaultdict(lambda: defaultdict(lambda:defaultdict(int)))
transitions_pronouns=defaultdict(lambda: defaultdict(int))
transitions_all_pronouns=defaultdict(int)
transitions_nouns=defaultdict(int)
unchanged_pronouns=defaultdict(int)
unchanged_nouns=defaultdict(int)
unchanged_pronouns_lemma=defaultdict(lambda: defaultdict(lambda:defaultdict(int)))
           
for doc in doc_ids:                                                     #for each document name in the key

    print >> sys.stderr, doc
    
    if not docs['key'].has_key(doc) or not docs['res1'].has_key(doc) or not docs['res2'].has_key(doc): 
        print doc,'either not in key or in response. Enter c to continue ommiting the documents or q to quit...'
        pdb.set_trace()
        continue                                                        #ommit documents not in key/res
        
    key=docs['key'][doc]
    res1=docs['res1'][doc]
    res2=docs['res2'][doc]
    if len(key)!=len(res1) or len(key)!=len(res2) or len(res2)!=len(res1): 
        print 'Key and response document have not the same number of lines.'    #could be problematic is the newline normalization is not perfect
        pdb.set_trace()
    
    #gather key and response sets
    key_sets=get_coref(key)
    res_sets1=get_coref(res1)
    res_sets2=get_coref(res2)
    
    #turn key and response into sorted list of lists    
    key_sets=sorted(key_sets.values())
    res_sets1=sorted(res_sets1.values())
    res_sets2=sorted(res_sets2.values())
    
    #Recall: we compare key to response mentions   
    for cset in key_sets:                                               #for every chain in the key
        if len(cset)==1: continue                                       #singleton, omit

        if ante_require == 'nominal':
            try: next(m for m in cset if len(m)==3 or m[3] in noun_pos_tags)    # noun in cset
            except StopIteration: continue    #no nouns, omit

        for key_m in cset[1:]:                                          #for every mention in the chain except the first one
            
            #determine POS tag of the mention:
            if len(key_m)==5 and not key_m[3] in noun_pos_tags: pos=key_m[3]   #single word term has length 5, mwt length 3
            else: pos='NOUN'
            
            if ante_require=='nominal':
                #no nominal ante for key_m -> cataphora, omit
                if [m for m in cset[:cset.index(key_m)] if len(m)==3 or m[3] in noun_pos_tags]==[]:
                    continue
            
            if pos in pronoun_pos_tags:
                lemma=re.search('[^|]+',key_m[-1].lower()).group()
                transitions[pos][lemma]['mentions']+=1
                transitions_pronouns[pos]['mentions']+=1
                transitions_all_pronouns['mentions']+=1
            elif pos=='NOUN':
                transitions_nouns['mentions']+=1

            type_res1=classify_mention(key_m,cset,res_sets1,ante_require)
            type_res2=classify_mention(key_m,cset,res_sets2,ante_require)  
            
            #determine transition type, update counts      
            transition = type_res1 + '->' + type_res2

            if transition in ['fn->tn', 'tn->fn']: pdb.set_trace()

            if not type_res1==type_res2:
                if pos in pronoun_pos_tags:
                    lemma=re.search('[^|]+',key_m[-1].lower()).group()
                    transitions[pos][lemma][transition]+=1
                    transitions_pronouns[pos][transition]+=1
                    transitions_all_pronouns[transition]+=1
                else:
                    transitions_nouns[transition]+=1
            else:
                if pos in pronoun_pos_tags:            
                    unchanged_pronouns[transition]+=1
                    lemma=re.search('[^|]+',key_m[-1].lower()).group()
                    unchanged_pronouns_lemma[pos][lemma][transition]+=1
                else:
                    unchanged_nouns[transition]+=1                   

    #Precision: find spurious mentions, i.e. response mentions that are not in the key
    for cset in res_sets1:  #for all chains in the reponse

        if len(cset)==1: continue   #singleton, ommit
        
        if ante_require=='nominal':
            try: next(m for m in cset if len(m)==3 or m[3] in noun_pos_tags)
            except StopIteration: continue  #no noun in set, ommit
        
        for res_m in cset[1:]:

            if ante_require=='nominal':
                try: next(m for m in cset[:cset.index(res_m)] if len(m)==3 or m[3] in noun_pos_tags)
                except StopIteration: continue  #no noun ante, ommit                    
            
            #is the mention in a key chain?
            key_set=[c for c in key_sets if res_m in c]
            if key_set==[] or key_set[0].index(res_m)==0:   #it's a false positive, no key chain or starter in the key                  

                #determine PoS
                if len(res_m)==5 and not res_m[3] in noun_pos_tags: pos=res_m[3]
                else: pos='NOUN'  

                if pos in pronoun_pos_tags:
                    lemma=re.search('[^|]+',res_m[-1].lower()).group()  # Disambiguate lemma: sein|seine -> sein
                    transitions[pos][lemma]['mentions']+=1
                    transitions_pronouns[pos]['mentions']+=1
                    transitions_all_pronouns['mentions']+=1
                elif pos=='NOUN':
                    transitions_nouns['mentions']+=1     

                #also resolved by sys 2?
                try:
                    res2cset=next(c for c in res_sets2 if res_m in c and c.index(res_m)!=0)
                    if ante_require=='nominal': next(m for m in res2cset[:res2cset.index(res_m)] if len(m)==3 or m[3] in noun_pos_tags) # Has a nominal ante?
                    transition='fp->fp'
                    if pos in pronoun_pos_tags:
                        unchanged_pronouns[transition]+=1
                        lemma=re.search('[^|]+',res_m[-1].lower()).group()
                        unchanged_pronouns_lemma[pos][lemma][transition]+=1
                    else:
                        unchanged_nouns[transition]+=1
                        
                #sys 2 did not resolve res_m, i.e. made the correct decision                        
                except:
                    transition='fp->tn'                
                    if pos in pronoun_pos_tags:
                        lemma=re.search('[^|]+',res_m[-1].lower()).group()
                        transitions[pos][lemma][transition]+=1
                        transitions_pronouns[pos][transition]+=1
                        transitions_all_pronouns[transition]+=1
                    else:
                        transitions_nouns[transition]+=1     

    #Precision: find spurious mentions, i.e. response mentions that are not in the key
    for cset in res_sets2:                                               #for all chains in the reponse

        if len(cset)==1: continue                                       #singleton, ommit
        
        if ante_require=='nominal':
            try: next(m for m in cset if len(m)==3 or m[3] in noun_pos_tags)
            except StopIteration: continue  #no noun in set, ommit          

        for res_m in cset[1:]:                     
            
            if ante_require=='nominal':
                try: next(m for m in cset[:cset.index(res_m)] if len(m)==3 or m[3] in noun_pos_tags)
                except StopIteration: continue  #no noun ante, ommit            
            
            key_set=[c for c in key_sets if res_m in c]                 #is the mention in a key chain?
            if key_set==[] or key_set[0].index(res_m)==0:

                if len(res_m)==5 and not res_m[3] in noun_pos_tags: pos=res_m[3]   #determine PoS
                else: pos='NOUN' 
                                               
                try:
                    res1cset=next(c for c in res_sets1 if res_m in c and c.index(res_m)!=0) #also resolved by sys 1, do nothing
                    #has a nominal ante?
                    if ante_require=='nominal': next(m for m in res1cset[:res1cset.index(res_m)] if len(m)==3 or m[3] in noun_pos_tags)                    
                    """
                    transition='fp->fp'                    
                    # We have already counted it above!
                    if pos in pronoun_pos_tags:
                        unchanged_pronouns[transition]+=1
                        lemma=re.search('[^|]+',res_m[-1].lower()).group()
                        unchanged_pronouns_lemma[pos][lemma][transition]+=1
                    else:
                        unchanged_nouns[transition]+=1
                    """                        
                except StopIteration:   #sys 1 did not resolve res_m, i.e. made the correct decision
                    transition='tn->fp'
                    if pos in pronoun_pos_tags:
                        lemma=re.search('[^|]+',res_m[-1].lower()).group()
                        transitions[pos][lemma][transition]+=1
                        transitions_pronouns[pos][transition]+=1
                        transitions_all_pronouns[transition]+=1
                    else:
                        transitions_nouns[transition]+=1     
                        
                    if pos in pronoun_pos_tags:
                        lemma=re.search('[^|]+',res_m[-1].lower()).group()
                        transitions[pos][lemma]['mentions']+=1
                        transitions_pronouns[pos]['mentions']+=1
                        transitions_all_pronouns['mentions']+=1
                    elif pos=='NOUN':
                        transitions_nouns['mentions']+=1                         

# categories of class transitions
errors=['tp->wl', 'tp->fp', 'tp->fn', 'tn->wl', 'tn->fp', 'tn->fn']
corrections=['wl->tp', 'fp->tp', 'fn->tp', 'wl->tn', 'fp->tn', 'fn->tn']
changed_errors=['fp->wl', 'fn->wl', 'wl->fp', 'fn->fp', 'wl->fn', 'fp->fn']
unchanged=['tp->tp','wl->wl','fp->fp','fn->fn','tn->tn']
"""
Some explanation:
fp->fn: occurs when response 1 resolves a set-inital (i.e. non-anaphoric) mention to another mention, and the second response does not resolve the mention at all.
fn->fp: first response does not resolve mention; second mention attaches it to an antecedent, instead of placing it as a set-initial mention
fn->tn: 
tn->fn:
"""
  
#Print output
all_transitions, all_mentions= 0, 0

if lang=='GER':
    # Normalize PPOSAT lemmas
    if 'seine' in transitions['PPOSAT']:
        for c in transitions['PPOSAT']['seine']: transitions['PPOSAT']['sein'][c]+=transitions['PPOSAT']['seine'][c]
    del transitions['PPOSAT']['seine']
    if 'ihre' in transitions['PPOSAT']:
        for c in transitions['PPOSAT']['ihre']: transitions['PPOSAT']['ihr'][c]+=transitions['PPOSAT']['ihre'][c]
    del transitions['PPOSAT']['ihre']    
    if 'seine' in unchanged_pronouns_lemma['PPOSAT']:
        for c in unchanged_pronouns_lemma['PPOSAT']['seine']: unchanged_pronouns_lemma['PPOSAT']['sein'][c]+=unchanged_pronouns_lemma['PPOSAT']['seine'][c]
    del unchanged_pronouns_lemma['PPOSAT']['seine']
    if 'ihre' in unchanged_pronouns_lemma['PPOSAT']:
        for c in unchanged_pronouns_lemma['PPOSAT']['ihre']: unchanged_pronouns_lemma['PPOSAT']['ihr'][c]+=unchanged_pronouns_lemma['PPOSAT']['ihre'][c]
    del unchanged_pronouns_lemma['PPOSAT']['ihre']
        
    # Sum of PPOSAT 
    transitions['PPOSAT']['3rd']=copy.deepcopy(transitions['PPOSAT']['sein'])
    for c in transitions['PPOSAT']['ihr']: transitions['PPOSAT']['3rd'][c]+=transitions['PPOSAT']['ihr'][c]
    unchanged_pronouns_lemma['PPOSAT']['3rd']=copy.deepcopy(unchanged_pronouns_lemma['PPOSAT']['sein'])
    for c in unchanged_pronouns_lemma['PPOSAT']['ihr']: unchanged_pronouns_lemma['PPOSAT']['3rd'][c]+=unchanged_pronouns_lemma['PPOSAT']['ihr'][c]

    # Sum 3rd person PPER
    transitions['PPER']['3rd']=copy.deepcopy(transitions['PPER']['er'])
    for c in transitions['PPER']['sie']: transitions['PPER']['3rd'][c]+=transitions['PPER']['sie'][c]
    unchanged_pronouns_lemma['PPER']['3rd']=copy.deepcopy(unchanged_pronouns_lemma['PPER']['er'])
    for c in unchanged_pronouns_lemma['PPER']['sie']: unchanged_pronouns_lemma['PPER']['3rd'][c]+=unchanged_pronouns_lemma['PPER']['sie'][c]

print '='*35
print 'Pronoun PoS and lemmas'
print '='*35

for p in transitions: 

    t_test_list_res1_pos, t_test_list_res2_pos = [], []

    if p in pronoun_pos_tags:

        print p
        pos_transitions,pos_mentions=0,0

        for lemma in transitions[p]:
        
            # Global count over all mentions
            all_mentions+=transitions[p][lemma]['mentions']     
            pos_mentions+=transitions[p][lemma]['mentions']
           
            if not transitions[p][lemma].keys()==['mentions']: # We have differences for that lemma
           
                lemma_transitions=0
                print '\t',lemma,'\tmentions:',transitions[p][lemma]['mentions']            
           
                """
                For t-test: create two lists, first representing res1, second res2
                Insert 1 in each list if mention has been processed correcty, i.e. either tp or tn
                Insert 0 in each list if mention has been processed incorrecty, i.e. either fp, fn, or wl
                """
                
                t_test_list_res1_lem, t_test_list_res2_lem = [], []
                
                for t,c in transitions[p][lemma].items():   # t is a specific transition, c its count for the given lemma

                    if not t=='mentions':                    
                       
                        print '\t\t',t,c

                        lemma_transitions+=c
                        if not lemma=='3rd':
                            # Increment transition count for all mentions, pos specific, and lemma specific
                            all_transitions+=c
                            pos_transitions+=c                        

                        # Add 1 or 0 to t_test_lists
                        trans=t.split('->')
                        if trans[0].startswith('t'): one_zero=1
                        else: one_zero=0
                        for x in range(c):  # Insert as many one_zeros as we have counts of that particluar transition t
                            t_test_list_res1_lem.append(one_zero)
                            t_test_list_res1_pos.append(one_zero)
                        if trans[1].startswith('t'): one_zero=1
                        else: one_zero=0 
                        for x in range(c): 
                            t_test_list_res2_lem.append(one_zero)
                            t_test_list_res2_pos.append(one_zero)
           
                if transitions[p][lemma]['mentions']!=0:
                    change=100. * lemma_transitions / transitions[p][lemma]['mentions']
                else:
                    change=100.
                print '\t\tDifference:', "{0:0.2f}".format(change),'%',
                
                if ttest:
                    # Expand t_test_lists by unchanged mentions
                    if p in unchanged_pronouns_lemma and lemma in unchanged_pronouns_lemma[p]:
                        for t,c in unchanged_pronouns_lemma[p][lemma].items():
                            trans=t.split('->')
                            if trans[0].startswith('t'): one_zero=1
                            else: one_zero=0
                            for x in range(c): 
                                t_test_list_res1_lem.append(one_zero)
                                t_test_list_res1_pos.append(one_zero)
                            if trans[1].startswith('t'): one_zero=1
                            else: one_zero=0 
                            for x in range(c): 
                                t_test_list_res2_lem.append(one_zero)            
                                t_test_list_res2_pos.append(one_zero)

                    t_test=ttest_rel(t_test_list_res1_lem,t_test_list_res2_lem)
                    print 'p =',t_test[1]
                else: print ''                    
        
        for t,c in transitions_pronouns[p].items():
            if not t=='mentions':
                print '\t',t,c
        print '\tOverall difference:',"{0:0.2f}".format(100.*pos_transitions/pos_mentions),'% (', pos_transitions,'/',pos_mentions,')',
        if ttest:
            t_test=ttest_rel(t_test_list_res1_pos,t_test_list_res2_pos)
            print 'p =',t_test[1]
        else: print ''
        
print '='*35

print

# Pronouns overall 
print 'All pronoun changes:'
all_transitions_pronouns_sum=float(sum([transitions_all_pronouns[x] for x in transitions_all_pronouns if not x=='mentions']))

print 'Corrections:',
sum_changes = sum([transitions_all_pronouns[c] for c in corrections if c in transitions_all_pronouns])
print "{0:0.2f}".format( (100.*sum_changes/all_transitions_pronouns_sum) ) ,'%','(',sum_changes,'/',all_transitions_pronouns_sum,')'
for c in corrections:
    if c in transitions_all_pronouns:
        print '\t',c,'\t',"{0:0.2f}".format(100.*transitions_all_pronouns[c]/all_transitions_pronouns_sum),'%\t',transitions_all_pronouns[c],'\t'      

print 'New errors:',
sum_changes = sum([transitions_all_pronouns[c] for c in errors if c in transitions_all_pronouns])
print "{0:0.2f}".format( (100.*sum_changes/all_transitions_pronouns_sum) ) ,'%','(',sum_changes,'/',all_transitions_pronouns_sum,')'
for c in errors:
    if c in transitions_all_pronouns:
        print '\t',c,'\t',"{0:0.2f}".format(100.*transitions_all_pronouns[c]/all_transitions_pronouns_sum),'%\t',transitions_all_pronouns[c],'\t'      

print 'Changed errors:',
sum_changes = sum([transitions_all_pronouns[c] for c in changed_errors if c in transitions_all_pronouns])
print "{0:0.2f}".format( (100.*sum_changes/all_transitions_pronouns_sum) ) ,'%','(',sum_changes,'/',all_transitions_pronouns_sum,')'
for c in changed_errors:
    if c in transitions_all_pronouns:
        print '\t',c,'\t',"{0:0.2f}".format(100.*transitions_all_pronouns[c]/all_transitions_pronouns_sum),'%\t',transitions_all_pronouns[c],'\t'      
print '='*35
print 'Overall pronoun difference:', "{0:0.2f}".format(100.*all_transitions/all_mentions),'%','(',all_transitions,'/',all_mentions,')'
print '='*35

print
# Nouns overall                
print 'All noun changes:'              
all_mentions+=transitions_nouns['mentions']    
local_transitions=0  
all_noun_transitions_sum=float(sum([transitions_nouns[x] for x in transitions_nouns if not x=='mentions']))

print 'Corrections:',
sum_changes = sum([transitions_nouns[c] for c in corrections if c in transitions_nouns])
print "{0:0.2f}".format( (100.*sum_changes/all_noun_transitions_sum) ) ,'%','(',sum_changes,'/',all_noun_transitions_sum,')'
for c in corrections:
    if c in transitions_nouns:
        print '\t',c,'\t',"{0:0.2f}".format(100.*transitions_nouns[c]/all_noun_transitions_sum),'%\t',transitions_nouns[c]
        all_transitions+=transitions_nouns[c]
        local_transitions+=transitions_nouns[c]

print 'New errors:',
sum_changes = sum([transitions_nouns[c] for c in errors if c in transitions_nouns])
print "{0:0.2f}".format( (100.*sum_changes/all_noun_transitions_sum) ) ,'%','(',sum_changes,'/',all_noun_transitions_sum,')'
for c in errors:
    if c in transitions_nouns:
        print '\t',c,'\t',"{0:0.2f}".format(100.*transitions_nouns[c]/all_noun_transitions_sum),'%\t',transitions_nouns[c]
        all_transitions+=transitions_nouns[c]
        local_transitions+=transitions_nouns[c]

print 'Changed errors:',
sum_changes = sum([transitions_nouns[c] for c in changed_errors if c in transitions_nouns])
print "{0:0.2f}".format( (100.*sum_changes/all_noun_transitions_sum) ) ,'%','(',sum_changes,'/',all_noun_transitions_sum,')'
for c in changed_errors:
    if c in transitions_nouns:
        print '\t',c,'\t',"{0:0.2f}".format(100.*transitions_nouns[c]/all_noun_transitions_sum),'%\t',transitions_nouns[c]
        all_transitions+=transitions_nouns[c]
        local_transitions+=transitions_nouns[c]
print '='*35
print 'Overall noun difference:',"{0:0.2f}".format((100.*local_transitions)/float(transitions_nouns['mentions'] )),
print '% (',local_transitions,'/',transitions_nouns['mentions'],')'  
print '='*35

print 

# All mentions
print 'All changes:'
# Overall change, sum all changes
all_changes = defaultdict(int)
for pronoun, lexemes in transitions.iteritems():
    for lexeme, trans in lexemes.iteritems():
        for t in trans:
            all_changes[t] += trans[t]

for t, c in transitions_nouns.iteritems():
    all_changes[t] += c

print 'Corrections:',
sum_corrections = sum([all_changes[c] for c in corrections if c in all_changes])
print "{0:0.2f}".format( (100.*sum_corrections/all_transitions) ) ,'%','(',sum_corrections,'/',all_transitions,')'
for c in corrections:
    if c in all_changes:
        print '\t',c,"{0:0.2f}".format( (100.*all_changes[c]/all_transitions) ) ,'%\t',all_changes[c]
print 'New errors:',
sum_new_errors = sum([all_changes[c] for c in errors if c in all_changes])
print "{0:0.2f}".format( (100.*sum_new_errors/all_transitions) ) ,'%','(',sum_new_errors,'/',all_transitions,')'
for c in errors:
    if c in all_changes:
        print '\t',c,"{0:0.2f}".format( (100.*all_changes[c]/all_transitions) ) ,'%\t',all_changes[c]
print 'Changed errors:',
sum_changed_errors = sum([all_changes[c] for c in changed_errors if c in all_changes])
print "{0:0.2f}".format( (100.*sum_changed_errors/all_transitions) ) ,'%','(',sum_changed_errors,'/',all_transitions,')'
for c in changed_errors:
    if c in all_changes:
        print '\t',c,"{0:0.2f}".format( (100.*all_changes[c]/all_transitions) ) ,'%\t',all_changes[c]

print '='*35
print 'Overall difference:', "{0:0.2f}".format( (100.*all_transitions/all_mentions) ),'%','(',all_transitions,'/',all_mentions,')'
print '='*35