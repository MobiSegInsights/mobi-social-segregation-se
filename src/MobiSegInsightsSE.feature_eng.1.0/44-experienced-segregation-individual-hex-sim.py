import sys
from pathlib import Path
import os
import pandas as pd
import sqlalchemy
import numpy as np
import ast
import random
from tqdm import tqdm
from statsmodels.stats.weightstats import DescrStatsW
from p_tqdm import p_map


ROOT_dir = Path(__file__).parent.parent.parent
sys.path.append(ROOT_dir)
sys.path.insert(0, os.path.join(ROOT_dir, 'lib'))

import preprocess as preprocess


def sim_expand(x):
    sim_list = []
    if ':' in x:
        sim_dict = ast.literal_eval(x)
        for k, v in sim_dict.items():
            sim_list += [k] * v
        random.Random(4).shuffle(sim_list)
    else:
        sim_list += [x] * 100
    return sim_list


class MobiSegAggregationIndividual:
    def __init__(self):
        self.mobi_data = None
        self.zonal_seg = None
        self.hex_sim_matrix = None
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']

    def load_individual_data(self, grp_num=30, test=False, drop_home=False):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')

        print('Load mobility data with shifted hex code...')
        self.mobi_data = pd.read_sql(sql='''SELECT uid, wt_total, hex, hex_sd AS hex_s, time_span
                                            FROM segregation.mobi_seg_hex_raw_sim2_w1h0;''', con=engine)
        # Group users
        random.seed(1)
        uids = self.mobi_data.uid.unique()
        gps = np.random.randint(1, grp_num + 1, len(uids))
        gp_dict = dict(zip(uids, gps))
        self.mobi_data.loc[:, 'gp'] = self.mobi_data['uid'].apply(lambda x: gp_dict[x])

        if test:
            print('Test mode, only look at 10000 users.')
            self.mobi_data = self.mobi_data.loc[self.mobi_data['gp'] == 1, :]

        if drop_home:
            self.mobi_data.dropna(inplace=True)
            self.mobi_data = self.mobi_data.loc[self.mobi_data.hex_s != '', :]
        else:
            self.mobi_data['hex_s'].fillna(self.mobi_data['hex'], inplace=True)
            self.mobi_data['hex_s'] = self.mobi_data.apply(lambda row:
                                                            row['hex'] if row['hex_s'] == '' else row['hex_s'],
                                                            axis=1)

        # For test
        tqdm.pandas()
        self.hex_sim_matrix = np.array(self.mobi_data['hex_s'].progress_apply(lambda x: sim_expand(x)).to_list())
        self.mobi_data.drop(columns=['hex_s'], inplace=True)
        print(f'{len(self.mobi_data)} rows loaded.')
        print(self.mobi_data.iloc[0])

    def load_zonal_data(self):
        print('Load nativity segregation levels at mixed-hexagon zones...')
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        self.zonal_seg = pd.read_sql(sql='''SELECT hex, time_seq, ice_birth
                                            FROM segregation.mobi_seg_hex
                                            WHERE weekday=1 AND holiday=0;''', con=engine)
        self.zonal_seg = self.zonal_seg.pivot(index='time_seq', columns='hex', values='ice_birth')

    def aggregating_metrics_indi(self, sim=1):
        def time_seq_median(data):
            return pd.Series({"time_seq": data.time_seq.values[0],
                              'ice_birth': data.ice_birth.median()})

        def by_time(data):
            return data.groupby('uid').apply(time_seq_median).reset_index()

        def span2seq(time_seq_list):
            seq = list(range(time_seq_list[0], time_seq_list[1] + 1))
            if len(time_seq_list) > 2:
                seq2 = list(range(time_seq_list[2], time_seq_list[3] + 1))
                seq = seq2 + seq
            return seq
        if sim > 0:
            self.mobi_data.loc[:, 'hex_s'] = self.hex_sim_matrix[:, sim - 1]

        for gp_id, df in self.mobi_data.groupby('gp'):
            print(f'Processing group: {gp_id}.')
            print(f'Exploding on time sequence.')
            df.loc[:, 'time_span'] = df.loc[:, 'time_span'].apply(lambda x: ast.literal_eval(
                x.replace("{", "(").replace("}", ")")
            ))
            df.loc[:, 'time_seq'] = df.loc[:, 'time_span'].apply(span2seq)
            df = df.explode('time_seq')
            df.drop(columns=['time_span'], inplace=True)

            print(f'Merge experienced segregation level.')

            def hex_time_to_seg(row, field='hex'):
                try:
                    x = self.zonal_seg.loc[(row['time_seq'], row[field])]
                except:
                    x = 9
                return x

            if sim == 0:
                df.loc[:, 'ice_birth'] = df.progress_apply(lambda row: hex_time_to_seg(row, field='hex'), axis=1)
            else:
                df.loc[:, 'ice_birth'] = df.progress_apply(lambda row: hex_time_to_seg(row, field='hex_s'), axis=1)
            share = len(df.loc[df.ice_birth == 9, :]) / len(df) * 100
            print(f"Share of missing values: {share} %.")
            df = df.loc[df.ice_birth != 9, :]

            print(f'Calculate an average day individually by weekday and holiday.')
            rstl = p_map(by_time, [g for _, g in df.groupby('time_seq', group_keys=True)])
            df = pd.concat(rstl)
            df.loc[:, 'sim'] = sim

            engine = sqlalchemy.create_engine(
                f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
            df.to_sql('mobi_seg_hex_individual_sim2_w1h0', engine, schema='segregation', index=False,
                      method='multi', if_exists='append', chunksize=10000)


if __name__ == '__main__':
    # Aggregating metrics individually (experienced segregation)
    seg_indi = MobiSegAggregationIndividual()
    seg_indi.load_individual_data(grp_num=6, test=False, drop_home=True)
    seg_indi.load_zonal_data()
    for i in range(1, 51):
        print(f'Calculating simulation {i}.')
        seg_indi.aggregating_metrics_indi(sim=i)
