import sys
from pathlib import Path
import os
import pandas as pd
import sqlalchemy
import numpy as np
import ast
from p_tqdm import p_map


ROOT_dir = Path(__file__).parent.parent.parent
sys.path.append(ROOT_dir)
sys.path.insert(0, os.path.join(ROOT_dir, 'lib'))

import preprocess as preprocess


class MobiSegAggregationIndividual:
    def __init__(self):
        self.mobi_data = None
        self.zonal_seg = None
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']

    def load_individual_data(self):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')

        print('Load mobility data with shifted DeSO code...')
        self.mobi_data = pd.read_sql(sql='''SELECT uid, wt_total, deso_s AS deso, time_span
                                            FROM segregation.mobi_seg_deso_raw_poi_w1h0;''', con=engine)
        print(self.mobi_data.iloc[0])

    def load_zonal_data(self):
        print('Load income unevenness at DeSO zones...')
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        self.zonal_seg = pd.read_sql(sql='''SELECT deso, time_seq, num_unique_uid, evenness_income, ice_birth
                                            FROM segregation.mobi_seg_deso
                                            WHERE weekday=1 AND holiday=0;''', con=engine)

    def aggregating_metrics_indi(self):
        self.mobi_data.loc[:, 'gp'] = np.random.randint(1, 31, self.mobi_data.shape[0])
        print('Calculate metrics of each temporal unit')

        def time_seq_median(data):
            return pd.Series({"time_seq": data.time_seq.values[0],
                              'evenness_income': data.evenness_income.median(),
                              'ice_birth': data.ice_birth.median(),
                              'num_coexistence': data.num_unique_uid.mean()})

        def by_time(data):
            return data.groupby('uid').apply(time_seq_median).reset_index()

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

            print(f'Merge experienced segregation level.')
            df = pd.merge(df, self.zonal_seg, on=['deso', 'time_seq'], how='left')

            print(f'Calculate an average day individually (weekday=1, holiday=0).')
            rstl = p_map(by_time, [g for _, g in df.groupby('time_seq', group_keys=True)])
            df = pd.concat(rstl)
            engine = sqlalchemy.create_engine(
                f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
            df.to_sql('mobi_seg_deso_individual_poi_w1h0', engine, schema='segregation', index=False,
                      method='multi', if_exists='append', chunksize=10000)


if __name__ == '__main__':
    # Aggregating metrics individually (experienced segregation)
    seg_indi = MobiSegAggregationIndividual()
    seg_indi.load_individual_data()
    seg_indi.load_zonal_data()
    seg_indi.aggregating_metrics_indi()
