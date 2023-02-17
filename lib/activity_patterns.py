import pandas as pd
import os
import sys
import subprocess
import numpy as np
import sqlalchemy
from tqdm import tqdm
from datetime import datetime


def get_repo_root():
    """Get the root directory of the repo."""
    dir_in_repo = os.path.dirname(os.path.abspath('__file__'))
    return subprocess.check_output('git rev-parse --show-toplevel'.split(),
                                   cwd=dir_in_repo,
                                   universal_newlines=True).rstrip()


ROOT_dir = get_repo_root()
sys.path.append(ROOT_dir)
sys.path.insert(0, ROOT_dir + '/lib')

from lib import preprocess as preprocess


class ActivityPatterns:
    def __init__(self):
        """
        :param month: 06, 07, 08, 12
        :type month: str
        :return: None
        :rtype: None
        """
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']
        self.data = None
        self.clusters = None

    def load_process_data(self):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
        self.data = pd.read_sql_query(
            sql="""SELECT uid, location_method, "TimeLocal", "leaving_TimeLocal", date, dur, month, cluster FROM 
            stops_subset;""",
            con=engine)
        self.data = preprocess.mobi_data_time_enrich(self.data)

    def aggregate_activity_temporal(self):
        # All records of stays
        all = list(self.data.loc[:, ['h_s', 'dur']].to_records(index=False))
        df_all = preprocess.cluster_tempo(pur='all', temps=all, norm=False)
        # Holiday
        holidays = list(self.data.loc[self.data.holiday == 1, ['h_s', 'dur']].to_records(index=False))
        df_holidays = preprocess.cluster_tempo(pur='holiday', temps=holidays, norm=False)
        # Non-holiday
        non_holidays = list(self.data.loc[self.data.holiday == 0, ['h_s', 'dur']].to_records(index=False))
        df_nholidays = preprocess.cluster_tempo(pur='non_holiday', temps=non_holidays, norm=False)
        return pd.concat([df_all, df_holidays, df_nholidays])

    def add_weight2records(self):
        tqdm.pandas()
        self.data = self.data.groupby('uid').progress_apply(preprocess.record_weights).reset_index(drop=True)

    def cluster_stats(self, top_n=3):
        def cluster_attrs(data):
            freq = len(data)
            freq_wt = sum(data.wt)
            dur = data.dur.sum()
            return pd.Series(dict(freq=freq, freq_wt=freq_wt, dur=dur))

        # Computing the statistics of clusters
        print('Computing statistics of clusters...')
        tqdm.pandas()
        self.clusters = self.data.groupby(['uid', 'cluster', 'holiday']).progress_apply(cluster_attrs).reset_index()
        self.clusters = self.clusters.sort_values(by=['uid', 'holiday', 'freq_wt'], ascending=[True, True, False])
        print('Saving clusters statistics...')
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
        self.clusters.to_sql('clusters', engine, schema='description', index=False, if_exists='replace',
                             method='multi', chunksize=5000)

        print(f'Selecting top {top_n} clusters individually...')
        tqdm.pandas()
        # Weighted top clusters
        df_top = self.clusters.loc[self.clusters.holiday == 0, :].groupby('uid').head(top_n).reset_index(drop=True)
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
        df_top.to_sql(f'clusters_top{top_n}_wt', engine, schema='description', index=False, if_exists='replace',
                      method='multi', chunksize=5000)

        # # Unweighted top clusters
        # self.clusters = self.clusters.sort_values(by=['uid', 'holiday', 'freq'], ascending=[True, True, False])
        # df_top = self.clusters.loc[self.clusters.holiday == 0, :].groupby('uid').head(top_n).reset_index(drop=True)
        # engine = sqlalchemy.create_engine(
        #     f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
        # df_top.to_sql(f'clusters_top{top_n}', engine, schema='description', index=False, if_exists='replace',
        #               method='multi', chunksize=5000)

    def activities_temporal(self, df_top=None):
        # Calculate temporal patterns of each cluster
        def cluster_tempo_agg(data):
            recs = list(data[['h_s', 'dur', 'wt']].to_records(index=False))
            df_tp = preprocess.cluster_tempo_weighted(temps=recs, prt=False)
            df_tp.loc[:, 'uid'] = data.uid.values[0]
            df_tp.loc[:, 'cluster'] = data.cluster.values[0]
            return df_tp

        print('Get records only for the input clusters of individuals...')
        self.data = pd.merge(self.data, df_top[['uid', 'cluster']], on=['uid', 'cluster'], how='inner')
        print('Extracting activity temporal profiles for top 3...')
        tqdm.pandas()
        df_tempo = self.data.groupby(['uid', 'cluster']).progress_apply(cluster_tempo_agg).reset_index(drop=True)
        df_tempo_list = preprocess.df2batches(df_tempo, chunk_size=10000000)
        del df_tempo
        for df in tqdm(df_tempo_list, desc='Saving temporal profiles'):
            engine = sqlalchemy.create_engine(
                f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
            df.to_sql('tempo_top3', engine, schema='description', index=False, if_exists='append',
                         method='multi', chunksize=5000)
