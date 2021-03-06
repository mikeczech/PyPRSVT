from PyPRSVT.ranking import rpc, distance_metrics
from PyPRSVT.ranking.features import rpc as feature_rpc
from PyPRSVT.gk import GK_WL as gk
from PyPRSVT.preprocessing.graphs import EdgeType
from PyPRSVT.preprocessing.ranking import Ranking
from ast import literal_eval
import pandas as pd
from sklearn import cross_validation
from os.path import isfile, join, exists
import argparse
import numpy as np
import networkx as nx
import random
import re
import itertools
import time
from tqdm import tqdm
import functools


__number_of_experiments__ = 5


def dump_gram(graph_paths, types, h_set, D_set, out_dir):
    graphs = []

    print('Reading graph representations.')

    for p in tqdm(graph_paths):
        if not isfile(p):
            raise ValueError('Graph {} not found.'.format(p))
        g = nx.read_gpickle(p)
        graphs.append(g)

    ret = {}
    h_D_product = list(itertools.product(h_set, D_set))
    matrix_computation_times = {}
    for i, (h, D) in enumerate(h_D_product):
        output_path = join(out_dir, 'K_h_{}_D_{}.gram'.format(h, D))
        ret[h, D] = output_path + '.npy'
        if not isfile(output_path + '.npy'):
            print('Computing normalized gram matrix for h={} and D={} ({} of {})'.format(h, D, i+1, len(h_D_product)), flush=True)
        else:
            print('{} already exists. Skipping...'.format(output_path + '.npy'))
            continue
        start_time = time.time()
        kernel = gk.GK_WL()
        K = kernel.compare_list_normalized(graphs, types, h, D)
        matrix_computation_times[h, D] = time.time() - start_time
        # saving matrix
        np.save(output_path, K)
    return ret, matrix_computation_times


def read_data(path):
    df = pd.DataFrame.from_csv(path)
    tools = []
    with open(path + '.tools') as f:
        tools.extend([x.strip() for x in f.readline().split(',')])
    return df, tools


def start_experiments(gram_paths, y, tools, h_set, D_set, folds=10):
    start_total_time = time.time()
    spearman = distance_metrics.SpearmansRankCorrelation(tools)
    scores = []
    training_times = []
    testing_times = []
    loo = cross_validation.KFold(len(y), folds, shuffle=True, random_state=random.randint(0, 100))
    for train_index, test_index in tqdm(list(loo)):
        y_train, y_test = y[train_index], y[test_index]
        clf = rpc.RPC(tools, spearman)
        start_training_time = time.time()
        clf.gram_fit(h_set, D_set, [0.001, 0.01, 0.1, 1, 10, 100, 1000], gram_paths, train_index, y_train)
        training_times.append(time.time() - start_training_time)
        start_testing_time = time.time()
        score = clf.score(gram_paths, test_index, train_index, y_test)
        testing_times.append(time.time() - start_testing_time)
        scores.append(score)
    total_time = time.time() - start_total_time
    h_list = []
    D_list = []
    C_list = []
    for (_, _), params in clf.params.items():
        h_list.append(params['h'])
        D_list.append(params['D'])
        C_list.append(params['C'])
    return np.mean(scores), total_time, np.mean(training_times), np.mean(testing_times), np.mean(h_list), np.mean(D_list), np.mean(C_list)


def start_verifolio_experiments(X, y, tools, folds=10):
    start_total_time = time.time()
    spearman = distance_metrics.SpearmansRankCorrelation(tools)
    scores = []
    training_times = []
    testing_times = []
    loo = cross_validation.KFold(len(y), folds, shuffle=True, random_state=random.randint(0, 100))
    for train_index, test_index in tqdm(list(loo)):
        X_train, X_test, y_train, y_test = X[train_index], X[test_index], y[train_index], y[test_index]
        clf = feature_rpc.RPC(tools, spearman)
        start_training_time = time.time()
        clf.fit(np.logspace(-3, 2, 6), [0.001, 0.01, 0.1, 1, 10, 100, 1000], X_train, y_train)
        training_times.append(time.time() - start_training_time)
        start_testing_time = time.time()
        score = clf.score(X_test, y_test)
        testing_times.append(time.time() - start_testing_time)
        scores.append(score)
    total_time = time.time() - start_total_time
    gamma_list = []
    C_list = []
    for (_, _), params in clf.params.items():
        gamma_list.append(params['gamma'])
        C_list.append(params['C'])
    return np.mean(scores), total_time, np.mean(training_times), np.mean(testing_times), np.mean(gamma_list), np.mean(C_list)


def read_gram_paths(gram_dir_path):
    gram_paths = {}
    with open(join(gram_dir_path, 'all.txt')) as f:
        for l in f:
            m = re.match(r"([0-9]+),([0-9]+),(.+)\n", l)
            if m is not None:
                h, D, path = int(m.group(1)), int(m.group(2)), m.group(3)
                gram_paths[h, D] = path
            else:
                raise ValueError('Invalid all.txt file?')
    return gram_paths


def write_dump_statistics(file, gram_times):
    with open(file, 'w') as f:
        total_time = 0
        for (h, D), t in gram_times.items():
            f.write('h {}, D {}: {} seconds\n'.format(h, D, t))
            total_time += t
        f.write('Total time: {} seconds\n'.format(total_time))


def write_experiments_statistics(file, score_list, total_times_list, training_times, testing_times, h_list, D_list, C_list):
    with open(file, 'w') as f:
        f.write('Accuracy: {} (Std: {})\n'.format(np.mean(score_list), np.std(score_list)))
        f.write('Total time: {} seconds (Std: {})\n'.format(np.mean(total_times_list), np.std(total_times_list)))
        f.write('Average training time: {} seconds (Std: {})\n'.format(np.mean(training_times), np.std(training_times)))
        f.write('Average testing time: {} seconds (Std: {})\n'.format(np.mean(testing_times), np.std(testing_times)))
        f.write('Average h: {} (Std: {})\n'.format(np.mean(h_list), np.std(h_list)))
        f.write('Average D: {} (Std: {})\n'.format(np.mean(D_list), np.std(D_list)))
        f.write('Average C: {} (Std: {})\n'.format(np.mean(C_list), np.std(C_list)))


def write_verifolio_experiments_statistics(file, score_list, total_times_list, training_times, testing_times, gamma_list, C_list):
    with open(file, 'w') as f:
        f.write('Accuracy: {} (Std: {})\n'.format(np.mean(score_list), np.std(score_list)))
        f.write('Total time: {} seconds (Std: {})\n'.format(np.mean(total_times_list), np.std(total_times_list)))
        f.write('Average training time: {} seconds (Std: {})\n'.format(np.mean(training_times), np.std(training_times)))
        f.write('Average testing time: {} seconds (Std: {})\n'.format(np.mean(testing_times), np.std(testing_times)))
        f.write('Average gamma: {} (Std: {})\n'.format(np.mean(gamma_list), np.std(gamma_list)))
        f.write('Average C: {} (Std: {})\n'.format(np.mean(C_list), np.std(C_list)))



def main():
    parser = argparse.ArgumentParser(description='Label Ranking')
    parser.add_argument('-g', '--dump_gram', type=str, required=False)
    parser.add_argument('--features', type=str, required=False)
    parser.add_argument('--gram_dir', type=str, required=False)
    parser.add_argument('-t', '--types', type=int, nargs='+', required=False)
    parser.add_argument('--h_set', type=int, nargs='+', required=False)
    parser.add_argument('--D_set', type=int, nargs='+', required=False)
    parser.add_argument('-e', '--experiments', type=str, required=False)
    parser.add_argument('-o', '--out', type=str, required=False)
    parser.add_argument('--combine_grams', type=str, nargs='+', required=False)
    args = parser.parse_args()

    # Precompute gram matrices
    if all([args.dump_gram, args.gram_dir, args.types, args.h_set, args.D_set]):

        print('Write gram matrices of {} to {}.'.format(args.dump_gram, args.gram_dir), flush=True)

        if not all([EdgeType(t) in EdgeType for t in args.types]):
            raise ValueError('Unknown edge type detected')
        if not exists(args.gram_dir):
            raise ValueError('Given directory does not exist')
        df, tools = read_data(args.dump_gram)
        graph_series = df['graph_representation']
        types = [EdgeType(t) for t in args.types]
        gram_paths, times = dump_gram(graph_series.tolist(), types, args.h_set, args.D_set, args.gram_dir)
        with open(join(args.gram_dir, 'all.txt'), 'w') as f:
            for (h, D), v in gram_paths.items():
                f.write('{},{},{}\n'.format(h, D, v))
        write_dump_statistics(join(args.gram_dir, 'gram.statistics'), times)


    # Perform experiments
    elif all([args.experiments, args.gram_dir, args.h_set, args.D_set, args.out]):
        if not exists(args.gram_dir):
            raise ValueError('Given directory does not exist')
        gram_paths = read_gram_paths(args.gram_dir)
        df, tools = read_data(args.experiments)
        y = np.array([Ranking(literal_eval(r)) for r in df['ranking'].tolist()])

        score_list = []
        total_time_list = []
        training_time_list = []
        testing_time_list = []
        h_mean_list = []
        D_mean_list = []
        C_mean_list = []
        for i in list(range(__number_of_experiments__)):

            print('Starting experiment {} of {}'.format(i+1, __number_of_experiments__), flush=True)

            score, total_time, training_time, testing_time, h, D, C = start_experiments(gram_paths, y, tools, args.h_set, args.D_set)
            score_list.append(score)
            total_time_list.append(total_time)
            training_time_list.append(training_time)
            testing_time_list.append(testing_time)
            h_mean_list.append(h)
            D_mean_list.append(D)
            C_mean_list.append(C)
        write_experiments_statistics(args.out, score_list, total_time_list, training_time_list, testing_time_list, h_mean_list, D_mean_list, C_mean_list)

    elif all([args.combine_grams, args.out, args.h_set, args.D_set]):

        print('Combining gram matrices.')

        gram_paths_list = []
        for gram_dir_path in tqdm(args.combine_grams):
            gram_paths = read_gram_paths(gram_dir_path)
            gram_paths_list.append(gram_paths)
        h_D_product = list(itertools.product(args.h_set, args.D_set))
        ret = {}
        for i, (h, D) in enumerate(h_D_product):
            grams = []
            for gram_paths in gram_paths_list:
                grams.append(np.load(gram_paths[h, D]))
            new_gram = functools.reduce(np.add, grams)
            new_gram = np.divide(new_gram, len(grams))
            output_path = join(args.out, 'K_h_{}_D_{}.gram'.format(h, D))
            np.save(output_path, new_gram)
            ret[h, D] = output_path + '.npy'
        with open(join(args.out, 'all.txt'), 'w') as f:
            for (h, D), v in ret.items():
                f.write('{},{},{}\n'.format(h, D, v))

    # Perform experiment with verifolio feature vectors
    elif all([args.features, args.out]):
        df, tools = read_data(args.features)
        y = np.array([Ranking(literal_eval(r)) for r in df['ranking'].tolist()])
        feature_df = df.drop('ranking', 1).drop('property_type', 1)
        X = feature_df.as_matrix()

        score_list = []
        total_time_list = []
        training_time_list = []
        testing_time_list = []
        gamma_mean_list = []
        C_mean_list = []
        for i in list(range(__number_of_experiments__)):

            print('Starting Verifolio experiment {} of {}'.format(i+1, __number_of_experiments__), flush=True)

            score, total_time, training_time, testing_time, gamma, C = start_verifolio_experiments(X, y, tools)
            score_list.append(score)
            total_time_list.append(total_time)
            training_time_list.append(training_time)
            testing_time_list.append(testing_time)
            gamma_mean_list.append(gamma)
            C_mean_list.append(C)
        write_verifolio_experiments_statistics(args.out, score_list, total_time_list, training_time_list, testing_time_list, gamma_mean_list, C_mean_list)


    # Wrong arguments, therefore print usage
    else:
        parser.print_usage()
        quit()


if __name__ == '__main__':
    main()


