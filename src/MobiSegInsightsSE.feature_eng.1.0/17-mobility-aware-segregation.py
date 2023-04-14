import sys
import subprocess
import os
import pandas as pd
import sqlalchemy
import weighted
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

from lib import metrics as mt
from lib import preprocess as preprocess


class MobiSegAggregation:
    def __init__(self):
        self.mobi_metrics = None
        self.socio_metrics = None
        self.mobi_data = None
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']

    def load_data_and_process(self):
        print('Loading individual mobility metrics and socio-economic attributes by housing grids...')
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
        self.mobi_metrics = pd.read_sql(sql='''SELECT * FROM mobility.indi_mobi_metrics_p;''', con=engine)
        self.socio_metrics = pd.read_sql(sql='''SELECT zone, income_q1, income_q2, income_q3, income_q4
                                                FROM grids;''', con=engine)
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

        self.mobi_data = pd.read_sql(sql='''SELECT uid, holiday, weekday, wt_total, deso, time_span
                                            FROM segregation.mobi_seg_deso_raw;''', con=engine)

        print('Add individual mobility characteristics, e.g., rg...')
        self.mobi_data = pd.merge(self.mobi_data, self.mobi_metrics, on='uid', how='left')

        print('Add income quantiles')
        self.mobi_data = pd.merge(self.mobi_data, self.socio_metrics, on='zone', how='left')
        print(self.mobi_data.iloc[0])

        print('Add individual residential accessibility metrics')
        df_access = pd.read_sql("""SELECT uid, cum_jobs, cum_stops FROM built_env.access_grid;""",
                                con=engine)
        self.mobi_data = pd.merge(self.mobi_data, df_access, on='uid', how='left')
        print(self.mobi_data.iloc[0])

    def aggregating_metrics(self):
        cols = ['number_of_locations', 'number_of_visits',
                'average_displacement', 'radius_of_gyration',
                'median_distance_from_home', 'Not Sweden', 'Lowest income group',
                'cum_jobs', 'cum_stops', 'car_ownership']

        def income_evenness_agg(n=4, q_grps=None):
            suma = sum([abs(q - 1 / n) for q in q_grps])
            s_i = n / (2 * n - 2) * suma
            return s_i

        def unit_weighted_median(data):
            # hex_id_ = data.hex_id.values[0]
            # weekday_ = data['weekday'].values[0]
            # holiday_ = data.holiday.values[0]
            time_seq_ = data.time_seq.values[0]
            # Visiting strength measure
            num_visits, num_visits_wt = len(data), data.wt_total.sum()
            num_unique_uid = data.uid.nunique()
            metrics_dict = dict(time_seq=time_seq_,
                                num_visits=num_visits,
                                num_visits_wt=num_visits_wt,
                                num_unique_uid=num_unique_uid)
            # Mobility patterns and segregation measures
            for v in cols:
                metrics_dict[v] = weighted.median(data[v], data['wt_total'])
            # Modified aggregation of income unevenness
            q1, q2, q3, q4 = sum(data['income_q1'] * data['wt_total']), sum(data['income_q2'] * data['wt_total']),\
                             sum(data['income_q3'] * data['wt_total']), sum(data['income_q4'] * data['wt_total'])
            sum_ = sum((q1, q2, q3, q4))
            q1, q2, q3, q4 = q1/sum_, q2/sum_, q3/sum_, q4/sum_
            metrics_dict['evenness_income'] = income_evenness_agg(n=4, q_grps=(q1, q2, q3, q4))
            return pd.Series(metrics_dict)

        grps = ['weekday', 'holiday', 'deso']
        df_g = self.mobi_data[grps].drop_duplicates(subset=grps)
        df_g.loc[:, 'gp'] = np.random.randint(1, 6, df_g.shape[0])
        self.mobi_data = pd.merge(self.mobi_data, df_g, on=grps, how='left')
        print('Calculate metrics of each spatiotemporal unit')

        def by_time(data):
            return data.groupby(['weekday', 'holiday', 'deso']).apply(unit_weighted_median).reset_index()

        def span2seq(time_seq_list):
            seq = list(range(time_seq_list[0], time_seq_list[1] + 1))
            if len(time_seq_list) > 2:
                seq2 = list(range(time_seq_list[2], time_seq_list[3] + 1))
                seq = seq2 + seq
            return seq

        for gp_id, df in self.mobi_data.groupby('gp'):
            print(f'Processing group: {gp_id}.')
            df.loc[:, 'time_span'] = df.loc[:, 'time_span'].apply(lambda x: ast.literal_eval(
                x.replace("{", "(").replace("}", ")")
            ))
            df.loc[:, 'time_seq'] = df.loc[:, 'time_span'].apply(span2seq)
            df = df.explode('time_seq')
            df.drop(columns=['time_span'], inplace=True)
            rstl = p_map(by_time, [g for _, g in df.groupby('time_seq', group_keys=True)])
            df = pd.concat(rstl)
            engine = sqlalchemy.create_engine(
                f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
            df.to_sql('mobi_seg_deso', engine, schema='segregation', index=False,
                      method='multi', if_exists='append', chunksize=10000)


if __name__ == '__main__':
    flag = 2
    # Data prep.
    if flag == 1:
        print('Prepare mobility data for aggregating segregation metrics.')
        mobi_seg = mt.MobilitySegregationPlace()
        mobi_seg.load_home_seg_uid()
        mobi_seg.load_mobi_data(test=False, traj_format=False)
        mobi_seg.load_deso_zones()
        mobi_seg.mobi_data_weight_processing()
        mobi_seg.add_spatio_unit()
        mobi_seg.add_temporal_unit(num_groups=48, save=True)
        print(f'Length of data:{len(mobi_seg.mobi_data)}')
    if flag == 2:
        # Aggregating metrics
        seg_agg = MobiSegAggregation()
        seg_agg.load_data_and_process()
        seg_agg.aggregating_metrics()
