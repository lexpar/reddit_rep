"""
Natural language features defind on a single Comment.
"""

import logging

import nltk
from polyglot.detect import Detector
from textblob import TextBlob
from profanity_check import predict_prob as profanity
from hatesonar import Sonar
from comment import Comment, CommentFeatures
from feature_extraction.nl_sets import *

logging.basicConfig(filename='./output.log')
hatesonar = Sonar()

def compute_nl_features(c: Comment):
    c.stats = CommentFeatures()
    stats = c.stats

    stats['lang'] = comment_languge(c)
    stats['word_count'] = word_count(c)
    stats['score'] = c.score
    stats['controversial'] = c.controversial
    stats['prp_first'] = percent_first_pronouns(c)
    stats['prp_second'] = percent_second_pronouns(c)
    stats['prp_third'] = percent_third_pronouns(c)
    stats['sent'] = sentiment(c)
    stats['subj'] = subjectivity(c)
    stats['punc_ques'] = percent_punc_question(c)
    stats['punc_excl'] = percent_punc_exclamation(c)
    stats['punc_per'] = percent_punc_period(c)
    stats['punc'] = percent_punc(c)
    stats['profanity'] = profanity_prob(c)
    stats['hate_count'] = hate_count(c)
    stats['hedge_count'] = hedge_count(c)
    stats.update(hate_sonar(c))
    stats['is_deleted'] = ('[deleted]' == c.body or '[removed]' == c.body)


def _blob(comment: Comment):
    if comment.blob:
        return comment.blob
    else:
        blob = TextBlob(comment.body)
        comment.blob = blob
        return blob


def comment_languge(comment: Comment):
    if comment.body == '[deleted]':
        return 'en'
    if not comment.body:
        return 'un'

    try:
        d = Detector(comment.body, quiet=True)
    except:
        print(f"Failed to parse comment {comment.comment_id}")
        return 'un'

    if not d.reliable:
        return 'un'
    else:
        return d.languages[0].code


def word_count(comment: Comment):
    if not comment.body:
        return 0
    return len(_blob(comment).words)


def should_nl_bail(comment: Comment):
    if comment.stats.get('word_count') is None:
        raise Exception("Must calculate word count first.")

    if comment.stats['word_count'] == 0:
        return True

    if comment.stats['lang'] != 'en':
        return True

    return False


def percent_first_pronouns(comment: Comment):
    if should_nl_bail(comment):
        return None

    prp = [w.lower() for w,t in _blob(comment).tags if t == 'PRP']
    if len(prp) == 0:
        return 0
    prp_count = len([p for p in prp if p in eng_prp_first])
    return prp_count / len(prp)


def percent_second_pronouns(comment: Comment):
    if should_nl_bail(comment):
        return None

    prp = [w.lower() for w,t in _blob(comment).tags if t == 'PRP']
    if len(prp) == 0:
        return 0
    prp_count = len([p for p in prp if p in eng_prp_second])
    return prp_count / len(prp)


def percent_third_pronouns(comment: Comment):
    if should_nl_bail(comment):
        return None

    prp = [w.lower() for w,t in _blob(comment).tags if t == 'PRP']
    if len(prp) == 0:
        return 0
    prp_count = len([p for p in prp if p in eng_prp_third])
    return prp_count / len(prp)

def sentiment(comment: Comment):
    if should_nl_bail(comment):
        return None

    return _blob(comment).sentiment[0]

def subjectivity(comment: Comment):
    if should_nl_bail(comment):
        return None

    return _blob(comment).sentiment[1]

def percent_punc_question(comment: Comment):
    if should_nl_bail(comment):
        return None

    punc = [p for p in _blob(comment).tokens if p in eng_punc]
    if len(punc) == 0:
        return 0
    ques = [p for p in punc if p == '?']
    return len(ques) / len(punc)


def percent_punc_exclamation(comment: Comment):
    if should_nl_bail(comment):
        return None

    punc = [p for p in _blob(comment).tokens if p in eng_punc]
    if len(punc) == 0:
        return 0
    excl = [p for p in punc if p == '!']
    return len(excl) / len(punc)


def percent_punc_period(comment: Comment):
    if should_nl_bail(comment):
        return None

    punc = [p for p in _blob(comment).tokens if p in eng_punc]
    if len(punc) == 0:
        return 0
    per = [p for p in punc if p == '.']
    return len(per) / len(punc)


def percent_punc(comment: Comment):
    if should_nl_bail(comment):
        return None
    punc = [p for p in _blob(comment).tokens if p in eng_punc]
    if len(punc) == 0:
        return 0
    return len(punc)/len(_blob(comment).tokens)


def profanity_prob(comment: Comment):
    if should_nl_bail(comment):
        return None
    return float(profanity([comment.body])[0])

def hate_count(comment:Comment):
    if should_nl_bail(comment):
        return None
    count = 0
    just_text = " ".join(_blob(comment).words).lower()
    for term in eng_hate:
        if term in just_text:
            count += 1
    return count

def hedge_count(comment:Comment):
    if should_nl_bail(comment):
        return None
    count = 0
    just_text = " ".join(_blob(comment).words).lower()
    for term in eng_hedge:
        if term in just_text:
            count += 1
    return count

def hate_sonar(comment:Comment):
    if should_nl_bail(comment):
        return [('hate_conf',None), ('off_conf', None)]
    res = hatesonar.ping(comment.body)
    d = {}
    for class_results in res['classes']:
        d[class_results['class_name']] = class_results['confidence']
    return [('hate_conf', d['hate_speech']),
            ('off_conf', d['offensive_language'])]