import sys
from pathlib import Path
import os
os.environ['USE_PYGEOS'] = '0'
import pandas as pd
import sqlalchemy
import numpy as np
import ast
import random
from tqdm import tqdm
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

    def load_saved_individual_data(self, grp_num=8, test=False):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        print('Load saved mobility data.')
        if test:
            self.mobi_data = pd.read_sql(sql='''SELECT uid, hex_sd AS hex_s, wt_total, time_span, "Tag"
                                                FROM segregation.mobi_seg_hex_raw_sim2_w1h0
                                                WHERE home = 0
                                                LIMIT 100000;''', con=engine)
        else:
            self.mobi_data = pd.read_sql(sql='''SELECT uid, hex_sd AS hex_s, wt_total, time_span, "Tag"
                                                FROM segregation.mobi_seg_hex_raw_sim2_w1h0
                                                WHERE home = 0;''', con=engine)
        l = len(self.mobi_data)
        self.mobi_data.dropna(inplace=True)
        self.mobi_data = self.mobi_data.loc[self.mobi_data.hex_s != '', :]
        l_a = len(self.mobi_data)
        share = l_a / l * 100
        print(f"Share of remained rows: {share} %.")
        self.mobi_data.loc[:, 'weekday'] = 1
        self.mobi_data.loc[:, 'holiday'] = 0

        # Group users
        random.seed(1)
        uids = self.mobi_data.uid.unique()
        gps = np.random.randint(1, grp_num + 1, len(uids))
        gp_dict = dict(zip(uids, gps))
        self.mobi_data.loc[:, 'gp'] = self.mobi_data['uid'].apply(lambda x: gp_dict[x])

        tag_dict = {
            "Automotive Services (a)": "Mobility",
            "Education (a)": "Education",
            "Financial Services (a)": "Financial",
            "Food and Drink (a)": "Food, Drink, and Groceries",
            "Groceries and Food (a)": "Food, Drink, and Groceries",
            "Health and Beauty (a)": "Health and Wellness",
            "Healthcare (a)": "Health and Wellness",
            "Outdoor Recreation (a)": "Recreation",
            "Recreation (a)": "Recreation",
            "Religious Places (a)": "Religious",
            "Sports and Activities (a)": "Recreation",
            "Transportation (a)": "Mobility",
            "Artisan Workshops": "Recreation",
            "Automotive Services (s)": "Mobility",
            "Craft": "Retail",
            "Education (s)": "Education",
            "Entertainment (s)": "Recreation",
            "Fashion and Accessories (s)": "Retail",
            "Financial Services (s)": "Financial",
            "Food and Drink (s)": "Food, Drink, and Groceries",
            "Groceries and Food (s)": "Food, Drink, and Groceries",
            "Health and Beauty (s)": "Health and Wellness",
            "Healthcare (s)": "Health and Wellness",
            "Home and Living": "Retail",
            "Office (s)": "Office",
            "Outdoor Recreation (s)": "Recreation",
            "Recreation (s)": "Recreation",
            "Sports and Activities (s)": "Recreation",
            "Transportation (s)": "Mobility",
            "Shop": "Retail",
            "Tourism": "Recreation",
            "Office": "Office",
            "Leisure": "Recreation"
        }
        self.mobi_data.loc[:, 'poi_type'] = self.mobi_data['Tag'].map(tag_dict)

        # Add groups
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
        self.mobi_data.reset_index(drop=True, inplace=True)
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

    def aggregating_metrics_indi(self, by_type=False, save=True, sims=(1, 25)):
        def time_seq_median(data):
            return pd.Series({'ice_birth': data.ice_birth.median()})

        def span2seq(time_seq_list):
            seq = list(range(time_seq_list[0], time_seq_list[1] + 1))
            if len(time_seq_list) > 2:
                seq2 = list(range(time_seq_list[2], time_seq_list[3] + 1))
                seq = seq2 + seq
            return seq

        def hex_time_to_seg(row, field='hex'):
            try:
                x = self.zonal_seg.loc[(row['time_seq'], row[field])]
            except:
                x = 9
            return x

        # if sim > 0:
        #     self.mobi_data.loc[:, 'hex_s'] = self.hex_sim_matrix[:, sim - 1]

        for gp_id, df in self.mobi_data.groupby('gp'):
            def group_data_process(sim_no):
                data = df.copy()
                data.loc[:, 'hex_s'] = self.hex_sim_matrix[data.index, sim_no - 1]

                # Exploding on time sequence.
                data.loc[:, 'time_span'] = data.loc[:, 'time_span'].apply(lambda x: ast.literal_eval(
                    x.replace("{", "(").replace("}", ")")
                ))
                data.loc[:, 'time_seq'] = data.loc[:, 'time_span'].apply(span2seq)
                data = data.explode('time_seq')
                data.drop(columns=['time_span'], inplace=True)

                # Merge experienced segregation level
                data.loc[:, 'ice_birth'] = data.apply(lambda row: hex_time_to_seg(row, field='hex_s'), axis=1)

                if by_type:
                    grps = ['weekday', 'holiday', 'uid', 'poi_type']
                else:
                    grps = ['weekday', 'holiday', 'uid']
                data = data.groupby(grps + ['time_seq']).apply(time_seq_median).reset_index()
                data.loc[:, 'sim'] = sim_no
                if save:
                    engine = sqlalchemy.create_engine(
                        f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
                    data.to_sql('mobi_seg_hex_individual_by_type_sim2_w1h0',
                              engine, schema='segregation', index=False,
                              method='multi', if_exists='append', chunksize=10000)

            print(f'Processing group: {gp_id}.')
            p_map(group_data_process, [x for x in range(sims[0], sims[1] + 1)])


if __name__ == '__main__':
    # Aggregating metrics individually (experienced segregation)
    seg_indi = MobiSegAggregationIndividual()
    seg_indi.load_saved_individual_data(grp_num=6, test=False)  # dropped home activities
    seg_indi.load_zonal_data()
    seg_indi.aggregating_metrics_indi(by_type=True, save=True, sims=(1, 3))
