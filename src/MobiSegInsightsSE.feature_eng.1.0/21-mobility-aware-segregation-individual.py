import sys
import subprocess
import os
import pandas as pd
import sqlalchemy
import numpy as np
import ast
from p_tqdm import p_map


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


class MobiSegAggregationIndividual:
    def __init__(self):
        self.mobi_metrics = None
        self.socio_metrics = None
        self.individual_data = None
        self.mobi_data = None
        self.zonal_seg = None
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']

    def load_individual_data(self):
        print('Loading individual mobility metrics and socio-economic attributes by housing grids...')
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
        self.mobi_metrics = pd.read_sql(sql='''SELECT * FROM mobility.indi_mobi_metrics_p;''', con=engine)
        self.socio_metrics = pd.read_sql(sql='''SELECT zone, income_evenness
                                                FROM segregation.resi_seg_grid;''', con=engine).\
            rename(columns={'income_evenness': 'evenness_income_resi'})
        df_sup = pd.read_sql(sql='''SELECT zone, "Lowest income group", "Not Sweden"
                                    FROM grid_stats;''', con=engine)
        self.socio_metrics = self.socio_metrics.loc[self.socio_metrics.zone.isin(self.mobi_metrics.zone), :]
        self.socio_metrics = pd.merge(self.socio_metrics, df_sup, on='zone', how='left')

        print('Add car ownership information by individual home deso zone')
        df_cars = pd.read_csv(os.path.join(ROOT_dir, 'dbs/DeSO/vehicles_2019.csv'), encoding='latin-1')
        df_cars = df_cars.loc[df_cars['status'] == 'totalt', :]
        df_deso = pd.read_sql("""SELECT deso, befolkning FROM zones;""", con=engine)
        df_cars = pd.merge(df_cars, df_deso.rename(columns={'deso': 'region'}), on='region', how='left')
        df_cars.loc[:, 'car_ownership'] = df_cars['2019'] / df_cars['befolkning']
        self.mobi_metrics = pd.merge(self.mobi_metrics, df_cars[['region', 'car_ownership']], on='region')

        print('Collect individual data: mobi + socio.')
        self.individual_data = pd.merge(self.mobi_metrics, self.socio_metrics, on='zone', how='left')

        print('Add individual residential accessibility metrics')
        df_access = pd.read_sql("""SELECT uid, cum_jobs, cum_stops FROM built_env.access_grid;""",
                                con=engine)
        self.individual_data = pd.merge(self.individual_data, df_access, on='uid', how='left')
        print(self.individual_data.iloc[0])

        print('Load mobility data...')
        self.mobi_data = pd.read_sql(sql='''SELECT uid, holiday, weekday, wt_total, deso, time_span
                                            FROM segregation.mobi_seg_deso_raw;''', con=engine)
        print(self.mobi_data.iloc[0])

    def load_zonal_data(self):
        print('Load income unevenness at DeSO zones...')
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
        self.zonal_seg = pd.read_sql(sql='''SELECT weekday, holiday, deso, time_seq, num_unique_uid, evenness_income
                                            FROM segregation.mobi_seg_deso;''', con=engine)

    def aggregating_metrics_indi(self):
        grps = ['weekday', 'holiday', 'uid']
        df_g = self.mobi_data[grps].drop_duplicates(subset=grps)
        df_g.loc[:, 'gp'] = np.random.randint(1, 31, df_g.shape[0])
        self.mobi_data = pd.merge(self.mobi_data, df_g, on=grps, how='left')
        print('Calculate metrics of each spatiotemporal unit')

        def time_seq_median(data):
            return pd.Series({"time_seq": data.time_seq.values[0],
                              'evenness_income': data.evenness_income.median(),
                              'num_coexistence': data.num_unique_uid.mean()})

        def by_time(data):
            return data.groupby(['weekday', 'holiday', 'uid']).apply(time_seq_median).reset_index()

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
            df = pd.merge(df, self.zonal_seg, on=['weekday', 'holiday', 'deso', 'time_seq'], how='left')

            print(f'Calculate an average day individually by weekday and holiday.')
            rstl = p_map(by_time, [g for _, g in df.groupby('time_seq', group_keys=True)])
            df = pd.concat(rstl)

            print(f'Merge individual attributes.')
            df = pd.merge(df, self.individual_data, on='uid', how='left')
            engine = sqlalchemy.create_engine(
                f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
            df.to_sql('mobi_seg_deso_individual', engine, schema='segregation', index=False,
                      method='multi', if_exists='append', chunksize=10000)


if __name__ == '__main__':
    # Aggregating metrics individually (experienced segregation)
    seg_indi = MobiSegAggregationIndividual()
    seg_indi.load_individual_data()
    seg_indi.load_zonal_data()
    seg_indi.aggregating_metrics_indi()
