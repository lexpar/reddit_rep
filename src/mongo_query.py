from pymongo import MongoClient
from collections import defaultdict
from typing import List

import comment
from comment import Comment, SubtreeStats
import feature_extraction as FE
from feature_extraction import SubtreeFeatures

MONGOURL = "mongodb://127.0.0.1:27017/?gssapiServiceName=mongodb"
client = MongoClient(MONGOURL)
comments_db = client.reddit.sampleComments

DATA_SIZE = 50_000


def load_all(cursor):
    """Pull everything a cursor returns into memory"""
    docs = []
    for doc in cursor[:DATA_SIZE]:
        docs.append(doc)
    return docs


def load_comments(comments_db):
    """Get all comments from the given db into memory"""
    cursor = comments_db.find({})
    docs = load_all(cursor)
    return [Comment(d) for d in docs]


def build_trees(comments):
    """Build discussion trees for the given comments"""
    by_parent = defaultdict(list)
    for c in comments:
        by_parent[c.parent_id].append(c)

    trees = []
    roots = [c for c in comments if c.parent_type == 'link']
    for c in roots:
        tree_root, tree_features = _build_rec_tree(c, by_parent)
        trees.append((tree_root, tree_features))
    return trees


def _build_rec_tree(c: Comment, by_parent) -> (Comment, SubtreeFeatures):
    subtree_featues = []
    for child in by_parent[c.comment_id]:
        subtree, features = _build_rec_tree(child, by_parent)
        subtree_featues.append(features)
        c.children.append(subtree)

    combined_features = SubtreeFeatures.combine(subtree_featues)
    _compute_features(c, combined_features)

    combined_features.update(c)
    return c, combined_features


def _compute_features(c: Comment, subtree_features: SubtreeFeatures):
    """Computes an associates aggregate features of this subtree"""
    stats = c.stats

    # Tree dimension features
    stats.size = FE.tree_size(c)
    stats.depth = FE.tree_depth(c)

    # Score based features
    stats.avg_score = FE.average_score(c, subtree_features)
    stats.std_dev_score = FE.std_dev_score(c, subtree_features)
    stats.min_score = FE.min_score(subtree_features)
    stats.max_score = FE.max_score(subtree_features)

    # Controversiality
    stats.percent_controversial = FE.percent_controversial(c,
                                                           subtree_features)


def print_tree(c: Comment, indent=0):
    indents = [" " for i in range(indent)]
    print("".join(indents) + c.body)
    for c in c.children:
        print_tree(c, indent=indent + 2)


def interactive():
    comments = load_comments(comments_db)
    trees = build_trees(comments)
    return comments, trees

# comments, trees = interactive()
