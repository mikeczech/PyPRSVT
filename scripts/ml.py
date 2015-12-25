from PyPRSVT.ranking import rpc, distance_metrics
from PyPRSVT.gk import GK_WL as gk
from PyPRSVT.preprocessing.graphs import EdgeType
from PyPRSVT.preprocessing.ranking import Ranking
from ast import literal_eval
import pandas as pd
from sklearn import svm, cross_validation
from os.path import isfile, join, exists
import argparse
import numpy as np
import networkx as nx
import random
import re
import itertools


def precompute_gram(graph_paths, types, h, D):
    graphs = []
    for path in graph_paths:
        print('Processing graph' + path)
        if not isfile(path):
            raise ValueError('Graph not found.')
        g = nx.read_graphml(path)
        graphs.append(g)
    kernel = gk.GK_WL()
    K = kernel.compare_list_normalized(graphs, types, h, D)
    return K


def dump_gram(graph_paths, types, h_set, D_set, out_dir):
    gram_paths = {}
    for h, D in itertools.product(h_set, D_set):
        output_path = join(out_dir, 'K_h_{}_D_{}.gram'.format(h, D))
        K = precompute_gram(graph_paths, types, h, D)
        np.save(output_path, K)
        graph_paths[h, D] = output_path
    return gram_paths


def read_data(path):
    df = pd.DataFrame.from_csv(path)
    tools = []
    with open(path + '.tools') as f:
        tools.extend([x.strip() for x in f.readline().split(',')])
    return df, tools


def start_experiments(gram_paths, y, tools, h_set, D_set, folds=10):
    spearman = distance_metrics.SpearmansRankCorrelation(tools)
    scores = []
    loo = cross_validation.KFold(len(y), folds, shuffle=True, random_state=random.randint(0, 100))
    for train_index, test_index in loo:
        y_train, y_test = y[train_index], y[test_index]
        clf = rpc.RPC(tools, spearman)
        clf.fit(h_set, D_set, [1, 100, 1000], gram_paths, train_index, y_train)
        score = clf.score(gram_paths, test_index, y_test)
        scores.append(score)
    return np.mean(scores), np.std(scores)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Label Ranking')
    parser.add_argument('-g', '--dump_gram', type=str, required=False)
    parser.add_argument('--gram_dir', type=str, required=False)
    parser.add_argument('-t', '--types', type=int, nargs='+', required=False)
    parser.add_argument('-h', '--h_set', type=int, nargs='+', required=False)
    parser.add_argument('-D', '--D_set', type=int, nargs='+', required=False)
    parser.add_argument('-e', '--experiments', type=str, required=False)
    args = parser.parse_args()

    # Precompute gram matrices
    if all([args.dump_gram, args.gram_dir, args.types, args.h_set, args.D_set]):
        if not all([t in EdgeType for t in args.types]):
            raise ValueError('Unknown edge type detected')
        if not exists(args.gram_dir):
            raise ValueError('Given directory does not exist')
        df, tools = read_data(args.dump_gram)
        graph_series = df['graph_representation']
        gram_paths = dump_gram(graph_series.tolist(), args.types, args.h_set, args.D_set, args.gram_dir)
        with open(join(args.gram_dir, 'all.txt', 'w')) as f:
            for (h, D), v in gram_paths:
                f.write('{},{},{}\n'.formal(h, D, v))

    # Perform experiments
    if all([args.experiments, args.gram_dir, args.h_set, args.D_set]):
        if not exists(args.gram_dir):
            raise ValueError('Given directory does not exist')
        gram_paths = {}
        with open(join(args.gram_dir, 'all.txt')) as f:
            for l in f:
                m = re.match(r"([0-9]+),([0-9]+),(.+)\n", l)
                if m is not None:
                    h, D, path = m.group(1), m.group(2), m.group(3)
                    gram_paths[h, D] = path
        df, tools = read_data(args.experiments)
        y = np.array([Ranking(literal_eval(r)) for r in df['ranking'].tolist()])
        mean, std = start_experiments(gram_paths, y, tools, args.h_set, args.D_set)
        print('Mean: {}, Std: {}'.format(mean, std))

    # Wrong arguments, therefore print usage
    else:
        parser.print_usage()
        quit()

