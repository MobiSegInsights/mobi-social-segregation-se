import sys
from pathlib import Path
import os
import pandas as pd
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
import sqlalchemy
import ast
from tqdm import tqdm
import random
import numpy as np
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


class BipartiteGraphCreation:
    def __init__(self):
        self.spatial_units = None
        self.geolocations = None
        self.hex_sim_matrix = None
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']

    def load_zones_geolocations(self, test=False, grp_num=5):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        # Load spatial units (hexagons and deso zones)
        print('Load spatial units.')
        self.spatial_units = gpd.GeoDataFrame.from_postgis(sql="""SELECT deso, hex_id, geom FROM spatial_units;""",
                                                        con=engine)
        print('Load geolocations.')
        if test:
            self.geolocations = pd.read_sql(sql='''SELECT uid, hex_s, wt_total, time_span, "Tag"
                                                FROM segregation.mobi_seg_hex_raw_sim1_w1h0
                                                WHERE home = 0
                                                LIMIT 100000;''', con=engine)
        else:
            self.geolocations = pd.read_sql(sql='''SELECT uid, hex_s, wt_total, time_span, "Tag"
                                                FROM segregation.mobi_seg_hex_raw_sim1_w1h0
                                                WHERE home = 0;''', con=engine)
        l = len(self.geolocations)
        self.geolocations.dropna(inplace=True)
        self.geolocations = self.geolocations.loc[self.geolocations.hex_s != '', :]
        l_a = len(self.geolocations)
        share = l_a / l * 100
        print(f"Share of remained rows: {share} %.")
        self.geolocations.loc[:, 'weekday'] = 1
        self.geolocations.loc[:, 'holiday'] = 0

        print(f'{len(self.geolocations)} from {self.geolocations.uid.nunique()} individual devices are loaded.')

        # Group users
        random.seed(1)
        uids = self.geolocations.uid.unique()
        gps = np.random.randint(1, grp_num + 1, len(uids))
        gp_dict = dict(zip(uids, gps))
        self.geolocations.loc[:, 'gp'] = self.geolocations['uid'].apply(lambda x: gp_dict[x])

        if test:
            print('Test mode, only look at some users from some data.')
            self.geolocations = self.geolocations.loc[self.geolocations['gp'] == 1, :]

        # Prepare simulated results
        tqdm.pandas()
        self.hex_sim_matrix = np.array(self.geolocations['hex_s'].progress_apply(lambda x: sim_expand(x)).to_list())
        self.geolocations.drop(columns=['hex_s'], inplace=True)
        print(f'{len(self.geolocations)} rows loaded.')
        print(self.geolocations.iloc[0])

    def bipartite_graph_hex(self, sim=1):
        def link_strength(data):
            return pd.Series({'count': sum(data['wt_total'])})

        def link_strength_time_seq(data):
            return pd.Series({"time_seq": data.time_seq.values[0],
                              'count': sum(data['wt_total'])})

        def by_time(data):
            return data.groupby(['uid', 'hex_s']).apply(link_strength_time_seq).reset_index()

        def span2seq(time_seq_list):
            seq = list(range(time_seq_list[0], time_seq_list[1] + 1))
            if len(time_seq_list) > 2:
                seq2 = list(range(time_seq_list[2], time_seq_list[3] + 1))
                seq = seq2 + seq
            return seq

        if sim > 0:
            self.geolocations.loc[:, 'hex_s'] = self.hex_sim_matrix[:, sim - 1]

        for gp_id, df in self.geolocations.groupby('gp'):
            print(f'Processing group: {gp_id}.')
            print(f'Exploding on time sequence.')
            df.loc[:, 'time_span'] = df.loc[:, 'time_span'].apply(lambda x: ast.literal_eval(
                x.replace("{", "(").replace("}", ")")
            ))
            df.loc[:, 'time_seq'] = df.loc[:, 'time_span'].apply(span2seq)
            df = df.explode('time_seq')
            df.drop(columns=['time_span'], inplace=True)

            print("Count visitor-hexagon link strength (larger DeSO zones w/ hexagons).")
            rstl = p_map(by_time, [g for _, g in df.groupby('time_seq', group_keys=True)])
            g = pd.concat(rstl)
            g.rename(columns={'hex_s': 'zone'}, inplace=True)
            # tqdm.pandas()
            #g = df.groupby(['uid', 'hex_s', 'time_seq']).\
            #    progress_apply(link_strength).reset_index().\
            #    rename(columns={'hex_s': 'zone'})
            g.loc[:, 'sim'] = sim

            engine = sqlalchemy.create_engine(
                f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
            print("Save hexagon bipartite graph.")
            g.to_sql('hex_time_sim1', engine, schema='bipartite_graph', index=False,
                     method='multi', if_exists='append', chunksize=10000)


if __name__ == '__main__':
    bgc = BipartiteGraphCreation()
    bgc.load_zones_geolocations(test=False)
    for sim in range(14, 51):
        print(f'Process simulation {sim}...')
        bgc.bipartite_graph_hex(sim=sim)
