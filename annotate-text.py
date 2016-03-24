import codecs
import sys
import re
import json
import csv
import numpy as np
import keras
from gensim.models.word2vec import Word2Vec
from keras.preprocessing.text import Tokenizer
from sklearn.kernel_ridge import KernelRidge
from corenlp import *

# Reading dictionary of affective words
affective = dict( )
for row in csv.DictReader(open("affective-ratings.csv")): affective[ row["Word"].lower() ] = np.array( [ float( row["V.Mean.Sum"] ) , float( row["A.Mean.Sum"] ) , float( row["D.Mean.Sum"] ) ] )

# Expand dictionary of affective words
embeddings_dim = 300
max_words = 100000
embeddings = dict( )
embeddings = Word2Vec.load_word2vec_format( "GoogleNews-vectors-negative300.bin.gz" , binary=True )
train_matrix = [ ]
train_labels = [ ]
for word,scores in affective.items():
  try:
    train_matrix.append( embeddings[word] )
    train_labels.append( scores )
  except: continue
model = KernelRidge( kernel='poly' , degree=4 )
model.fit( train_matrix , train_labels )
textdata = " ".join( open(sys.argv[1] + ".revised.txt",'r').readlines( ) )
tokenizer = Tokenizer(nb_words=max_words, filters=keras.preprocessing.text.base_filter(), lower=True, split=" ")
tokenizer.fit_on_texts(textdata)
for word,index in tokenizer.word_index.items():
  try:
    if not affective.has_key(word) : affective[word] = np.array( model.predict( np.array( embedding[word] ).reshape(1, -1) )[0] )
  except: affective[word] = np.array( [ 5.0 , 5.0 , 5.0 ] )

# Read a list of exception patterns
exceptions = dict( )
for row in open("fairytales-corpus-regexner.txt").readlines():
  row = row.split("\t")
  if " " not in row[0]: exceptions[ row[0] ] = row[1]

# Process the textual contents
textdata = "" 
file1 = open(sys.argv[1] + ".revised.txt",'r')
with file1 as myfile: textdata = re.sub( ">", "&gt;" , re.sub("<" , "&lt;" , re.sub( "&" , "&amp;" , re.sub( "   +", "\n\n" , re.sub( "\t" , " ", re.sub( "\r" , "" ,  "".join( myfile.readlines() ) ) ) ) ) ) )
corenlp = StanfordCoreNLP( )
file2 = open(sys.argv[1] + ".annotated.tsv",'w')
file3 = open(sys.argv[1] + ".annotated.xml",'w')
print >>file2, "PARAGRAPH NUMBER\tENTITY TYPE\tENTITY\tCO-OCCURRING NOUNS\tCO-OCCURRING ADJECTIVES\tCO-OCCURRING VERBS\tVALENCE\tAROUSAL\tDOMINANCE\tSENTENCE"
print >>file3, "<document name='" + sys.argv[1] + "'>"
parnum = 0
sys.stdout.write("Processing text...")
try:
  for paragraph in re.split("\n\n", textdata):
    sys.stdout.write('.')
    sys.stdout.flush()
    paragraph = re.sub("\n" , " ", re.sub( "#", "", re.sub( "\\\\n" , " ", re.sub("\ufeff", "" , paragraph ) ) ) ).strip( )
    if paragraph.startswith("u'"): paragraph = re.sub("'$" , "" , re.sub( "u'", "", paragraph ) ).strip( )
    paragraph = re.sub("'" , '"', paragraph ).strip( )
    results = {'sentences': [ ] }
    try: results = json.loads( corenlp.parse( paragraph ) )
    except: results = {'sentences': [ ] }
    entities = [ ]
    for sent in results["sentences"]:
      sentence = str( sent["text"] ).strip( )
      prevtag = "-"
      entity = None
      start = None
      end = None
      entities = [ ]
      nouns = [ ]
      adjectives = [ ]
      verbs = [ ]
      emotion = [ ]
      for word in sent["words"]:
        if affective.has_key( word[0] ): emotion.append( np.array( affective[word[0]] ) )
        elif affective.has_key( word[0].lower() ): emotion.append( np.array( affective[word[0].lower()] ) )
        elif affective.has_key( word[1]["Lemma"] ): emotion.append( np.array( affective[word[1]["Lemma"]] ) )
        elif affective.has_key( word[1]["Lemma"].lower() ): emotion.append( np.array( affective[word[1]["Lemma"].lower()] ) )
        if word[1]["PartOfSpeech"].startswith( "J" ) and word[1]["NamedEntityTag"] == "O" : adjectives.append( str( word[1]["Lemma"].lower() ) )
        if word[1]["PartOfSpeech"].startswith( "N" ) and word[1]["NamedEntityTag"] == "O" : nouns.append( str( word[1]["Lemma"].lower() ) )
        if word[1]["PartOfSpeech"].startswith( "V" ) and word[1]["NamedEntityTag"] == "O" : verbs.append( str( word[1]["Lemma"].lower() ) )
        if word[1]["NamedEntityTag"] == "PERSON" or word[1]["NamedEntityTag"] == "LOCATION" or exceptions.has_key( word[0] ):
          if exceptions.has_key( word[0] ): word[1]["NamedEntityTag"] = exceptions[ word[0] ]
          if entity is None: 
            start = word[1]["CharacterOffsetBegin"]
            entity = word[0]
          elif word[1]["NamedEntityTag"] == prevtag: entity = entity + " " + word[0]
          else:
            entities.append( ( prevtag , entity , int ( start ) , int ( end ) ) )
            entity = word[0]
            start = word[1]["CharacterOffsetBegin"]
        elif not( entity is None ):
          entities.append( ( prevtag , entity , int ( start ) , int ( end ) ) )
          entity = None
        prevtag = word[1]["NamedEntityTag"]
        end = word[1]["CharacterOffsetEnd"]      
      if not( entity is None ):
        entities.append( ( prevtag , entity , int( start ) , int ( end ) ) )
        entity = None
      if len( emotion ) > 0: emotion = np.mean( np.array( emotion ) , axis=0 )
      else: emotion = [ 5.0 , 5.0 , 5.0 ]
      nouns = set(nouns)
      adjectives = set(adjectives)
      verbs = set(verbs)
      entities = [ ( a, b, c, d, ";".join(nouns), ";".join(adjectives) , ";".join(verbs) , str( emotion[0] ) , str( emotion[1] ) , str( emotion[2] ) , sentence ) for ( a, b, c, d ) in entities ] 
    for entity in entities: print >>file2, str( repr(parnum) +"\t" + entity[0] + "\t" + entity[1] + "\t" + entity[4] + "\t" + entity[5] + "\t" + entity[6] + "\t" + entity[7] + "\t" + entity[8] + "\t" + entity[9] + "\t" + entity[10] )
    if len( entities ) == 0: print >>file3, "\t<paragraph num_entities='0' num='" + repr(parnum) + "'>" + paragraph + "</paragraph>"
    else:
      paddingsize = 0
      for pos in range( len( entities ) ):
        start = entities[pos][2]
        end = entities[pos][3]
        replacement = "<entity type='" + entities[pos][0] + "' common-nouns='" + entities[pos][4] + "' adjectives='" + entities[pos][5] + "' verbs='" + entities[pos][6] + "' valence='" + entities[pos][7] + "' arousal='" + entities[pos][8] + "' dominance='" + entities[pos][9] + "'>" + entities[pos][1] + "</entity>"
        paragraph = paragraph[:start + paddingsize] + replacement + paragraph[end + paddingsize:]
        paddingsize = paddingsize + len( replacement ) - len( entities[pos][1] )
      print >>file3, "\t<paragraph num_entities='" + repr( len( entities ) ) + "' num='" + repr(parnum) + "'>" + paragraph + "</paragraph>"
    parnum += 1
    file2.flush( )
    file3.flush( )
  print >>file3, "</document>"
except:
  print >>file3, "</document>"
  print >>file3, "<!--"
  print >>file3, "Unexpected error:", sys.exc_info()[0]
  print >>file3, "-->"
  file1.close()
  file2.close()
  file3.close()  
  raise
file1.close()
file2.close()
file3.close()
