import sys
from pathlib import Path
import os
import pandas as pd
os.environ['USE_PYGEOS'] = '0'
import sqlalchemy
from tqdm import tqdm
import ast
from p_tqdm import p_map


ROOT_dir = Path(__file__).parent.parent.parent
sys.path.append(ROOT_dir)
sys.path.insert(0, os.path.join(ROOT_dir, 'lib'))

import preprocess as preprocess


def inter_count(data=None):
    f = data.loc[data['grp_r'] == 'F', 'wt_p'].sum()
    d = data.loc[data['grp_r'] == 'D', 'wt_p'].sum()
    n = data.loc[data['grp_r'] == 'N', 'wt_p'].sum()
    return pd.Series(dict(f=f, d=d, n=n))


class InteractionExtraction:
    def __init__(self):
        self.presence = None
        self.inter_zone = None
        self.zonal_interactions = None
        self.mobi_data = None
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

    def load_zonal_interactions(self):
        print('Load interactions at mixed-hexagon zones...')
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        self.inter_zone = pd.read_sql(sql='''SELECT zone AS hex, time_seq, f, d, n
                                             FROM bipartite_graph.hex_interactions;''', con=engine)
        self.zonal_interactions = dict()
        for v in ('f', 'd', 'n'):
            self.zonal_interactions[v] = self.inter_zone.pivot(index='time_seq', columns='hex', values=v)
        print(self.zonal_interactions[v].head())

    def interaction_ind(self):
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

            def hex_time_to_interactions(row, v='f'):
                try:
                    x = self.zonal_interactions[v].loc[(row['time_seq'], row['hex'])]
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

            engine = sqlalchemy.create_engine(
                f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
            df.to_sql('hex_interactions_indi', engine, schema='bipartite_graph', index=False,
                      method='multi', if_exists='append', chunksize=10000)


if __name__ == '__main__':
    # Aggregating metrics individually (interactions records)
    inter_indi = InteractionExtraction()
    step = 1
    if step == 1:
        for time_seq in range(1, 49):
            print(f'Process timeslot {time_seq}:')
            inter_indi.interaction_zone(time_seq=time_seq, test=False, save=True)
    if step == 2:
        inter_indi.load_zonal_interactions()
        inter_indi.load_saved_individual_data(test=False)
        inter_indi.interaction_ind()
