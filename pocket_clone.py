"""
Pcoket clone
take link,
    get text,
    display text, 
    display stats,

have multiple pages saved,
    archive pages,
    delete pages,

possible extras:
    links have tags,
"""

"""
TODO:
    remove pictures(css- have .visually-hidden be hidden) | get them to display
    add in summary, stats, markov chain to page
    add delete function

    make css - images are inv. articles are boxes. buttons are hidden till hover. 


"""
from flask import Flask, render_template, request, redirect, url_for, session
from playhouse.sqlite_ext import SqliteExtDatabase
from peewee import *
import nltk
import requests
import markovify
from readability import Document
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
import datetime

from bs4 import BeautifulSoup

app = Flask(__name__)



db = SqliteExtDatabase("Pocket_clone.db")

class User(Model):
    name = CharField()

    class Meta:
        database = db

class Article(Model):
    title = CharField()
    head = TextField()
    text = TextField()
    html_clean = TextField()
    summary = TextField()
    Markov = TextField()
    user = ForeignKeyField(User, related_name='articles')
    date_created = DateTimeField(default=datetime.datetime.now)
    num_chars = TextField()
    num_words = TextField()
    f_dist = TextField()
    link = TextField()

    class Meta:
        database = db


def get_article_doc(link):
    response = requests.get(link)
    doc = Document(response.text)
    return doc

def get_article_text(doc):
    soup = BeautifulSoup(doc.summary()) 
    text =  soup.get_text() 
    return text

def prepare_data(text):
    default_stopwords = set(nltk.corpus.stopwords.words('english'))
    words = nltk.word_tokenize(text)
    # Remove single-character tokens (mostly punctuation)
    words = [word for word in words if len(word) > 1]
    # Remove numbers
    words = [word for word in words if not word.isnumeric()]
    # Lowercase all words (default_stopwords are lowercase too)
    words = [word.lower() for word in words]
    # remove stopwords
    words = [word for word in words if word not in default_stopwords]
    return words

def get_stats(text):
    words = prepare_data(text)
    num_words = len(words)
    num_chars = len(text)
    fdist = nltk.FreqDist(words)
    f_dist = ""
    for word, count in fdist.most_common(10):
        f_dist += "<p> {} : {} </p>".format(word, count)
    return (num_chars, num_words, f_dist)


def get_summary(text):
    parser = PlaintextParser(text, Tokenizer("english"))
    summarizer = LexRankSummarizer()
    summary = summarizer(parser.document, 3) #Summarize the document with 5 sentences
    paragraph = ""
    for sentance in summary:
        paragraph += sentance._text
        paragraph += " "
    return paragraph

def markov_chain(text,n):
    try:
        text_model = markovify.Text(text)
        paragraph = ""
        # I might need to fix this...
        for _ in range(n):
            paragraph += text_model.make_sentence()
            paragraph += " "
        return paragraph
    except:
        return "Markov Chain Could Not Be Generated"


def make_article(link, u):
    doc = get_article_doc(link)
    title = doc.title()
    html_clean = doc.summary()
    text = get_article_text(doc)
    head = text[: 500]
    num_chars, num_words, f_dist = get_stats(text)
    summary = get_summary(text)
    markov = markov_chain(text, 5)
    Article.create(
        link = link,
        title= title,
        head = head,
        text = text,
        html_clean = html_clean,
        summary = summary,
        Markov = markov,
        num_chars = num_chars,
        num_words = num_words,
        f_dist = f_dist,
        user = u
    )


@app.before_request
def before_request():
    db.connect()
    db.create_tables([User, Article], safe=True)

@app.teardown_request
def teardown_request(exception):
    db.close()

@app.route("/")
def login():
    return render_template("login.html", error_text=False)

@app.route("/make_account")
def make_account_form():
    return render_template('create_account.html')

@app.route("/make_account/", methods=['POST'])
def make_account():
    User.create( name=request.form['username'] )
    return redirect("/")

@app.route("/get_user/", methods=['POST'])
def get_user():
    username = request.form['username']
    try:
        user = User.get(name=username)
    except:
        return render_template("login.html", error_text=True)

    session['user'] = user.id
    return redirect("/home")

@app.route("/home")
def home():
    user = User.get( id= session['user'] )
    return render_template("home.html", user=user,
                           articles=user.articles.order_by(-Article.date_created))

@app.route("/add_article/", methods=['POST'])
def add_article():
    user = User.get( id= session['user'] )
    make_article(request.form['link'], user)
    return redirect("/home")

@app.route("/add_recommended_article/<a>")
def add_recommended_artcle(a):
    user = User.get( id= session['user'] )
    article = Article.get(id=a)
    make_article( article.link, user)
    return redirect("/home")
    


@app.route("/<a>")
def view_article(a):
    try:
        article = Article.get(id=a)
        return render_template("article.html", article=article)
    except:
        return "error"

@app.route("/Recommended")
def recommended():
    try:
        recommended_user = User.get( name="recommended_user" )
        return render_template("recommended.html", 
                               articles=recommended_user.articles.order_by(-Article.date_created))
    except:
        return "Recommended articles not set up!"

@app.route("/delete/<a>")
def delete_article(a):
    article = Article.get(id=a)
    article.delete_instance()
    return redirect("/home")

@app.route("/extras/<a>")
def extras(a):
    try:
        article = Article.get(id=a)
        return render_template("extras.html", article=article)
    except:
        return "error"
if __name__ == "__main__":
    app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
    app.run(debug=True, host='0.0.0.0')
