import sys
from pathlib import Path
import os
import pandas as pd
os.environ['USE_PYGEOS'] = '0'
import sqlalchemy
from tqdm import tqdm
import ast
from p_tqdm import p_map
import numpy as np
import random


ROOT_dir = Path(__file__).parent.parent.parent
sys.path.append(ROOT_dir)
sys.path.insert(0, os.path.join(ROOT_dir, 'lib'))

import preprocess as preprocess


def inter_count(data=None):
    f = data.loc[data['grp_r'] == 'F', 'wt_p'].sum()
    d = data.loc[data['grp_r'] == 'D', 'wt_p'].sum()
    n = data.loc[data['grp_r'] == 'N', 'wt_p'].sum()
    return pd.Series(dict(f=f, d=d, n=n))


def inter_count_sim(data=None):
    f = data.loc[data['grp_r'] == 'F', 'wt_p'].sum()
    d = data.loc[data['grp_r'] == 'D', 'wt_p'].sum()
    n = data.loc[data['grp_r'] == 'N', 'wt_p'].sum()
    time_seq = data.loc[:, 'time_seq'].values[0]
    return pd.Series(dict(f=f, d=d, n=n, time_seq=time_seq))


def inter_proccess(data):
    f = data['f'].sum()
    d = data['d'].sum()
    n = data['n'].sum()
    total = f + d + n
    return pd.Series(dict(f=f/total*100,
                          d=d/total*100,
                          n=n/total*100))


def inter_proccess_sim(data):
    f = np.nansum(data['f']*data['count'])
    d = np.nansum(data['d']*data['count'])
    n = np.nansum(data['n']*data['count'])
    total = f + d + n
    if total > 0:
        return pd.Series(dict(f=f/total*100,
                              d=d/total*100,
                              n=n/total*100))
    else:
        return pd.Series(dict(f=0, d=0, n=0))


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


class InteractionExtraction:
    def __init__(self):
        self.presence = None
        self.inter_zone = None
        self.zonal_interactions = None
        self.mobi_data = None
        self.hex_sim_matrix = None
        self.groups = pd.read_parquet(os.path.join(ROOT_dir, 'results/data4model_individual_hex_w1h0.parquet'))
        self.groups = self.groups[['uid', 'wt_p', 'grp_r', 'ice_r', 'grp', 'ice_e']]
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']
        print(self.groups.iloc[0])

    def interaction_zone(self, time_seq=1, test=False, save=False):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        if test:
            self.presence = pd.read_sql(sql=f"""SELECT uid, zone, count
                                                FROM bipartite_graph.hex_time
                                                WHERE time_seq={time_seq}
                                                LIMIT 100000;""", con=engine)
        else:
            self.presence = pd.read_sql(sql=f"""SELECT uid, zone, count
                                                FROM bipartite_graph.hex_time
                                                WHERE time_seq={time_seq};""", con=engine)
        self.presence = pd.merge(self.presence, self.groups[['uid', 'wt_p', 'grp_r']], on='uid', how='left')
        tqdm.pandas()
        self.inter_zone = self.presence.groupby('zone').progress_apply(inter_count).reset_index()
        self.inter_zone.loc[:, 'time_seq'] = time_seq
        if save:
            engine = sqlalchemy.create_engine(
                f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
            self.inter_zone.to_sql('hex_interactions',
                                   engine, schema='bipartite_graph', index=False,
                                   method='multi', if_exists='append', chunksize=10000)

    def interaction_zone_sim(self, test=False, save=False, sim=1):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        if test:
            self.presence = pd.read_sql(sql=f"""SELECT uid, zone, count, time_seq
                                                FROM bipartite_graph.hex_time_sim1
                                                WHERE sim={sim}
                                                LIMIT 100000;""", con=engine)
        else:
            self.presence = pd.read_sql(sql=f"""SELECT uid, zone, count, time_seq
                                                FROM bipartite_graph.hex_time_sim1
                                                WHERE sim={sim};""", con=engine)
        self.presence = pd.merge(self.presence, self.groups[['uid', 'wt_p', 'grp_r']], on='uid', how='left')

        def by_time(data):
            return data.groupby('zone').apply(inter_count_sim).reset_index()

        print('Get zonal interactions...')
        rstl = p_map(by_time, [g for _, g in self.presence.groupby('time_seq', group_keys=True)])
        self.inter_zone = pd.concat(rstl)

        # tqdm.pandas()
        # self.inter_zone = self.presence.groupby(['zone', 'time_seq']).progress_apply(inter_count).reset_index()
        if save:
            engine = sqlalchemy.create_engine(
                f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
            self.inter_zone.to_sql('hex_interactions_sim1', engine, schema='bipartite_graph', index=False,
                                   method='multi', if_exists='append', chunksize=10000)

    def load_saved_individual_data(self, test=False):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        if test:
            self.mobi_data = pd.read_sql(sql='''SELECT * FROM segregation.mobi_seg_hex_raw
                                                WHERE weekday=1 AND holiday=0
                                                LIMIT 100000;''', con=engine)
        else:
            self.mobi_data = pd.read_sql(sql='''SELECT * FROM segregation.mobi_seg_hex_raw
                                                WHERE weekday=1 AND holiday=0;''', con=engine)

    def load_saved_individual_data_sim(self, test=False, grp_num=5):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        if test:
            self.mobi_data = pd.read_sql(sql='''SELECT uid, hex_s, wt_total, time_span, "Tag"
                                                FROM segregation.mobi_seg_hex_raw_sim1_w1h0
                                                WHERE home = 0
                                                LIMIT 100000;''', con=engine)
        else:
            self.mobi_data = pd.read_sql(sql='''SELECT uid, hex_s, wt_total, time_span, "Tag"
                                                FROM segregation.mobi_seg_hex_raw_sim1_w1h0
                                                WHERE home = 0;''', con=engine)
        l = len(self.mobi_data)
        self.mobi_data.dropna(inplace=True)
        self.mobi_data = self.mobi_data.loc[self.mobi_data.hex_s != '', :]
        l_a = len(self.mobi_data)
        share = l_a / l * 100
        print(f"Share of remained rows: {share} %.")
        self.mobi_data.loc[:, 'weekday'] = 1
        self.mobi_data.loc[:, 'holiday'] = 0

        print(f'{len(self.mobi_data)} from {self.mobi_data.uid.nunique()} individual devices are loaded.')

        # Group users
        random.seed(1)
        uids = self.mobi_data.uid.unique()
        gps = np.random.randint(1, grp_num + 1, len(uids))
        gp_dict = dict(zip(uids, gps))
        self.mobi_data.loc[:, 'gp'] = self.mobi_data['uid'].apply(lambda x: gp_dict[x])

        if test:
            print('Test mode, only look at some users from some data.')
            self.mobi_data = self.mobi_data.loc[self.mobi_data['gp'] == 1, :]

        # Prepare simulated results
        tqdm.pandas()
        self.hex_sim_matrix = np.array(self.mobi_data['hex_s'].progress_apply(lambda x: sim_expand(x)).to_list())
        self.mobi_data.drop(columns=['hex_s'], inplace=True)
        print(f'{len(self.mobi_data)} rows loaded.')
        print(self.mobi_data.iloc[0])

    def load_zonal_interactions(self, col='hex'):
        if self.inter_zone is None:
            print('Load interactions at mixed-hexagon zones...')
            engine = sqlalchemy.create_engine(
                f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
            self.inter_zone = pd.read_sql(sql='''SELECT zone AS hex, time_seq, f, d, n
                                                 FROM bipartite_graph.hex_interactions;''', con=engine)
            self.zonal_interactions = dict()
            for v in ('f', 'd', 'n'):
                self.zonal_interactions[v] = self.inter_zone.pivot(index='time_seq', columns=col, values=v)
            print(self.zonal_interactions[v].head())

    def interaction_ind_sim(self, sim=1, save=True):
        df = pd.merge(self.presence[['uid', 'zone', 'time_seq', 'count']],
                      self.inter_zone,
                      on=['zone', 'time_seq'], how='left')
        # uid, zone, time_seq, count, f, d, n
        print('Get aggregated interaction statistics...')
        tqdm.pandas()
        df = df.groupby('uid').progress_apply(inter_proccess_sim).reset_index()
        df.loc[:, 'sim'] = sim
        if save:
            engine = sqlalchemy.create_engine(
                f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
            df.to_sql('hex_interactions_indi_sim1', engine, schema='bipartite_graph', index=False,
                      method='multi', if_exists='append', chunksize=10000)

    def interaction_ind(self, simulation=False, sim=0):
        def time_seq_agg(data):
            return pd.Series({"time_seq": data.time_seq.values[0],
                              'f': data['f'].sum(),
                              'd': data['d'].sum(),
                              'n': data['n'].sum()})

        def by_time(data):
            return data.groupby('uid').apply(time_seq_agg).reset_index()

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

            print(f'Merge zonal interactions.')
            if simulation:
                col_name = 'hex_s'
            else:
                col_name = 'hex'
            def hex_time_to_interactions(row, v='f'):
                try:
                    x = self.zonal_interactions[v].loc[(row['time_seq'], row[col_name])]
                except:
                    x = -9
                return x
            tqdm.pandas()
            for v in ('f', 'd', 'n'):
                df.loc[:, v] = df.progress_apply(lambda row: hex_time_to_interactions(row, v=v), axis=1)
            share = len(df.loc[df['f'] == -9, :]) / len(df) * 100
            print(f"Share of missing values: {share} %.")
            df = df.loc[(df['f'] != -9) & (df['d'] != -9) & (df['n'] != -9), :]
            print(f'Calculate an average day individually by weekday and holiday.')
            rstl = p_map(by_time, [g for _, g in df.groupby('time_seq', group_keys=True)])
            df = pd.concat(rstl)
            if simulation:
                df = df.groupby('uid').progress_apply(inter_proccess).reset_index()
                df.loc[:, 'sim'] = sim
            engine = sqlalchemy.create_engine(
                f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
            df.to_sql('hex_interactions_indi_sim1', engine, schema='bipartite_graph', index=False,
                      method='multi', if_exists='append', chunksize=10000)


if __name__ == '__main__':
    # Aggregating metrics individually (interactions records)
    inter_indi = InteractionExtraction()
    sim_res = True
    if sim_res:
        # inter_indi.load_saved_individual_data_sim(test=False, grp_num=5)
        for sim_id in range(1, 51):
            print(f'Process simulation {sim_id}...')
            inter_indi.interaction_zone_sim(sim=sim_id, test=False, save=False)
            # inter_indi.load_zonal_interactions(col='hex_s')
            inter_indi.interaction_ind_sim(sim=sim_id, save=True)
    else:
        # for time_seq in range(1, 49):
        #     print(f'Process timeslot {time_seq}:')
        #     inter_indi.interaction_zone(time_seq=time_seq, test=False, save=True)
        inter_indi.load_zonal_interactions()
        inter_indi.load_saved_individual_data(test=False)
        inter_indi.interaction_ind(simulation=False)
