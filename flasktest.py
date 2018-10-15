#working copy 

import flask #from flask import Flask, render_template, request, flash
import numpy as np
import pandas as pd
import pickle
import re
from forms import EntryForm
from scipy.spatial.distance import cosine, euclidean
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF
import io
import base64
from wordcloud import WordCloud
import matplotlib.pyplot as plt
#---------- MODEL IN MEMORY ----------------#
#  more stop words
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer
import string
from nltk.tag import pos_tag

def noun_tokenizer(text):

    # remove punctuation
    punct = string.punctuation + '±−≤°≥“”'
    remove_punct = str.maketrans('', '', punct)
    text = text.translate(remove_punct)

    # remove digits and convert to lower case
    remove_digits = str.maketrans('', '', string.digits)
    text = text.lower().translate(remove_digits)

    # tokenize
    tokens = word_tokenize(text)

    is_noun = lambda pos: (pos == 'NN') | (pos == 'NNS') #only nouns - no proper nouns
    nouns = [word for (word, pos) in pos_tag(tokens) if is_noun(pos)]
    # remove stop words
    stop_words = stopwords.words('english')
    JAS_words = ['use', 'model', 'anim', 'method', 'result', 'kg', 'vs', 'treatment', 'mgkg', 'per', 'h', 'x']
    more_words = ['et', 'al', 'mg', 'cm', 'animals', 'animal', 'mm', 'experiment','treatments','containing', 'studies', 'added', 'sources', 'total', 'science', 'research', 'field', 'degree','report', 'greater', 'increased', 'decreased', 'less', 'use', 'production', 'agriculture']
    stop_words = stop_words + JAS_words + more_words
    tokens_stop = [y for y in tokens if y not in stop_words]

    # stem
    #stemmer = SnowballStemmer('english')
    #tokens_stem = [stemmer.stem(y) for y in tokens_stop] 

    return tokens_stop

# Load pickled corpus:
with open('jas_df.pkl', 'rb') as picklefile:
    jas_df = pickle.load(picklefile)
with open('jas_abstracts.pkl', 'rb') as picklefile:
    jas_abstracts = pickle.load(picklefile)

#Load NLP 
with open('JAS_vocab.pkl', 'rb') as picklefile:
    JAS_vocab = pickle.load(picklefile)
with open('JAS_nmf.pkl', 'rb') as picklefile:
    JAS_nmf = pickle.load(picklefile)
with open('JAS_tfidf.pkl', 'rb') as picklefile:
    JAS_tfidf = pickle.load(picklefile)
with open('JAS_vecs.pkl', 'rb') as picklefile:
    JAS_vecs = pickle.load(picklefile)

nmf_topic_words100 = [topic[:100] for topic in np.argsort(-JAS_nmf.components_)] #list of topics' indices for top 100 words
#create a dictionary of top 100 words?  and load that instead of JAS_vocab
    
#---------- FUNCTIONS IN MEMORY ----------------#    


    
def top_topics_for_article(art_num):
    a = np.where(JAS_vecs[art_num] > 0.01)[0] #list of indices where nmf coeff is over 0.01 for a given article
    b = JAS_vecs[art_num][JAS_vecs[art_num] > 0.01] # list of corresponding nmf coeffs for a given article
    return a,b

def topic_word_clouds(art_idx):
    '''input:
    art_idx = an article index
    rows = number of topics with nmf coeff > 0.01'''
    fig = plt.figure() # create figure to add subplots to
    #columns = 1
    #rows = len(art_indices)
    #for art_idx in art_indices:
    topic_nums, topic_coeffs = top_topics_for_article(art_idx) 
    rows = len(topic_nums)
    for i, topic_idx in enumerate(topic_nums):
        topic_words = " ".join([JAS_vocab[word_idx].strip() for word_idx in nmf_topic_words100[topic_idx]])
        wordcloud = WordCloud(collocations=False).generate(topic_words)
        fig.add_subplot(rows, 1, i+1)
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis("off")
    plt.tight_layout()
    
    img = io.BytesIO() #buffer
    plt.savefig(img, format='png') #save to buffer
    img.seek(0) #start at right spot
    plot_url = base64.b64encode(img.getvalue()).decode() #copied
    
    #topic_
    return plot_url


def filter_top5_recommender(article, vectorizer, NMF, vecs, metric, keyword=None, num_results=6):
    #tokenize given article using trained vectorizer
    tokens = vectorizer.transform(article)
    vec = NMF.transform(tokens)[0] #nmf.transform returns a nested list
    
    #select distance metric 
    if metric == 'C':
        dists = [cosine(vec, vecs[i]) for i in range(len(vecs))]
    else:
        dists = [euclidean(vec, vecs[i]) for i in range(len(vecs))]
    
    #Number of results to return
    if num_results:      
        num_results = int(num_results)
    else: 
        num_results = 6  #set default if not given
        
    #Filter or not?
    articles = []
    if keyword:        
        i = 0
        while len(articles) < num_results:
            idx = np.argsort(dists)[i] #search closest abstracts for the key word
            if re.search(re.compile('(?i){}'.format(keyword)), jas_abstracts[idx]): #if yes, add article
                cloud_plot = topic_word_clouds(idx)
                article = {'rank': i, 'distance': '%.3f' % dists[idx], 'title': jas_df['title'].iloc[idx],
                            'abstract_txt': jas_abstracts.iloc[idx], 'doi_link': jas_df['doi'].iloc[idx],
                            'cloud': cloud_plot}
                articles.append(article) 
            i += 1 #else, move on
    else:
        close_idx = np.argsort(dists)[:num_results] #just grab the closest abstracts
        for i, idx in enumerate(close_idx):
            cloud_plot = topic_word_clouds(idx)
            distance = '%.3f' % dists[idx]
            article = {'rank': i, 'distance': distance, 'title': jas_df['title'].iloc[idx],
                        'abstract_txt': jas_abstracts.iloc[idx], 'doi_link': jas_df['doi'].iloc[idx],
                        'cloud': cloud_plot}
            articles.append(article)
    return articles # a list of dictionaries
    

#---------- URLS AND WEB PAGES -------------#

# Initialize the app
app = flask.Flask(__name__)
app.secret_key = 'development key'

#Add enumerate function for jinga
@app.context_processor
def inject_enumerate():
    return dict(enumerate=enumerate)

# Homepage
@app.route("/")
def search_page():
    """
    Homepage: serve our search page, form.html
    """
    form = EntryForm()
    return flask.render_template('form.html', form = form)

# Get an example and return it's score from the predictor model
@app.route("/results", methods=["POST"])
def results():
    """
    When A POST request with json data is made to this uri,
    Read the example from the json, predict probability and
    send it with a response
    """
    # Get data from form that came with the request
    data = flask.request.form
    #has attributes og_abstract similarity keywords num_results
    result = filter_top5_recommender([data['og_abstract']], JAS_tfidf, JAS_nmf, JAS_vecs, 
                                       data['similarity'], keyword=data['keyword'], 
                                       num_results=data['num_results'])
    
    # Put the result in a nice dict so we can send it as json
    
    #return flask.render_template("results.html",result = result)

   
    return flask.render_template("results.html",result = result) #, plot_url = plot_url)
	#return '<img src="data:image/png;base64,{}">'.format(plot_url)




#--------- RUN WEB APP SERVER ------------#

# Start the app server on port 80

if __name__ == '__main__':
   app.run(debug = True)
# (The default website port)
app.run(host='0.0.0.0')
app.run(debug=True)
