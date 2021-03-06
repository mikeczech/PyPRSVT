import requests
import json
import pandas as pd
from tqdm import tqdm

VERIFOLIO_URL = r'http://192.168.2.108:5000/extract'

def extract_features(sourcefile):
    """
    Todo
    :param sourcefile:
    :return:
    """
    with open(sourcefile) as f:
        resp = requests.post(VERIFOLIO_URL, files={'file': f})
    if not resp.ok:
        raise requests.ConnectionError('Could not communicate with verifolio service')
    return json.loads(resp.text)


def create_feature_df(sourcefiles):
    """
    Todo
    :param sourcefiles:
    :return:
    """

    print('Extracting features...', flush=True)

    data = []
    for s in tqdm(sourcefiles):
        features = extract_features(s)
        metrics = features['loop_metrics']
        metrics.update(features['role_metrics'])
        data.append(metrics)
    return pd.DataFrame(data, index=sourcefiles)


def create_features_labels_df(feature_df, labels_df):
    """
    Todo
    :param feature_df:
    :param labels_df:
    :return:
    """
    return pd.concat([feature_df, labels_df], axis=1)
