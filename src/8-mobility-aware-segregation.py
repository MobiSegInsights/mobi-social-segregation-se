import sys
import subprocess
import os
import pandas as pd
import sqlalchemy
import weighted
import numpy as np
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
        self.mobi_data = None
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']

    def load_data_and_process(self):
        print('Loading individual mobility metrics and segregation measuring by housing...')
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
        self.mobi_metrics = pd.read_sql(sql='''SELECT * FROM segregation.indi_mobi_resi_seg_metrics;''', con=engine)
        self.mobi_data = pd.read_sql(sql='''SELECT * FROM segregation.mobi_seg_hexagons_raw;''', con=engine)

        print('Add individual segregation and mobility measuring...')
        df_indi_metrics = self.mobi_metrics.loc[self.mobi_metrics.uid.isin(self.mobi_data.uid.unique()), :]
        self.mobi_data = pd.merge(self.mobi_data, df_indi_metrics, on='uid', how='left')

        print('Add income quantiles')
        df_inc_grps = pd.read_csv("dbs/DeSO/income_2019.csv")
        self.mobi_data = pd.merge(self.mobi_data, df_inc_grps[['region', 'q1', 'q2', 'q3', 'q4']], on='region', how='left')

    def aggregating_metrics(self):
        cols = ['number_of_locations', 'number_of_visits',
                'average_displacement', 'radius_of_gyration',
                'median_distance_from_home', 'evenness_income', 'iso_income',
                'evenness_birth_region', 'iso_birth_region', 'evenness_background', 'iso_background',
                'Foreign background', 'Not Sweden', 'Lowest income group']

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
            num_unique_uid, num_pop = data.uid.nunique(), data.wt_p.sum()
            metrics_dict = dict(time_seq=time_seq_,
                                num_visits=num_visits,
                                num_visits_wt=num_visits_wt,
                                num_unique_uid=num_unique_uid,
                                num_pop=num_pop)
            # Mobility patterns and segregation measures
            for v in cols:
                metrics_dict[v] = weighted.median(data[v], data['wt_total'])
            # Modified aggregation of income unevenness
            q1, q2, q3, q4 = sum(data['q1'] * data['wt_total']), sum(data['q2'] * data['wt_total']),\
                             sum(data['q3'] * data['wt_total']), sum(data['q4'] * data['wt_total'])
            sum_ = sum((q1, q2, q3, q4))
            q1, q2, q3, q4 = q1/sum_, q2/sum_, q3/sum_, q4/sum_
            metrics_dict['evenness_income_r'] = income_evenness_agg(n=4, q_grps=(q1, q2, q3, q4))
            return pd.Series(metrics_dict)

        grps = ['weekday', 'holiday', 'time_seq', 'hex_id']
        df_g = self.mobi_data[grps].drop_duplicates(subset=grps)
        df_g.loc[:, 'gp'] = np.random.randint(1, 51, df_g.shape[0])
        self.mobi_data = pd.merge(self.mobi_data, df_g, on=grps, how='left')
        print('Calculate metrics of each spatiotemporal unit')

        def by_time(data):
            return data.groupby(['weekday', 'holiday', 'hex_id']).apply(unit_weighted_median).reset_index()
        for gp_id, df in self.mobi_data.groupby('gp'):
            rstl = p_map(by_time, [g for _, g in df.groupby('time_seq', group_keys=True)])
            df = pd.concat(rstl)
            engine = sqlalchemy.create_engine(
                f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
            df.to_sql('mobi_seg_hexagons', engine, schema='segregation', index=False,
                      method='multi', if_exists='append', chunksize=10000)


if __name__ == '__main__':
    flag = 2
    # Data prep.
    if flag == 1:
        print('Prepare mobility data for aggregating segregation metrics.')
        mobi_seg = mt.MobilitySegregationPlace()
        mobi_seg.load_home_seg_uid()
        mobi_seg.load_mobi_data(test=False)
        mobi_seg.load_hexagons_mobi_metrics()
        mobi_seg.mobi_data_processing()
        mobi_seg.add_spatio_unit()
        mobi_seg.add_temporal_unit(num_groups=48)
        print(f'Length of data:{len(mobi_seg.mobi_data)}')
    if flag == 2:
        # Aggregating metrics
        seg_agg = MobiSegAggregation()
        seg_agg.load_data_and_process()
        seg_agg.aggregating_metrics()
