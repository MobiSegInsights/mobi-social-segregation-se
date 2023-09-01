import sys
from pathlib import Path
import os
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
import pandas as pd
import sqlalchemy
import wquantiles
import numpy as np
import ast
from tqdm import tqdm
from p_tqdm import p_map


ROOT_dir = Path(__file__).parent.parent.parent
sys.path.append(ROOT_dir)
sys.path.insert(0, os.path.join(ROOT_dir, 'lib'))

import preprocess as preprocess


class MobiSegAggregation:
    def __init__(self):
        # Auxiliary data
        self.access = None
        self.mobi_metrics = None
        self.socio_metrics = None
        # Mobility data
        self.mobi_data = None
        # Spatial unit
        self.zones = None
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']

    def load_aux_data(self):
        print('Loading individual mobility metrics and socio-economic attributes by housing grids...')
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        self.mobi_metrics = pd.read_sql(sql='''SELECT * FROM mobility.indi_mobi_metrics_p;''', con=engine)
        self.socio_metrics = pd.read_sql(sql='''SELECT zone, income_q1, income_q2, income_q3, income_q4, 
                                                birth_se, birth_other, pop
                                                FROM grids;''', con=engine)
        df_sup = pd.read_sql(sql='''SELECT zone, "Lowest income group", "Not Sweden", "Other"
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

        print('Load individual residential accessibility metrics (grid-level).')
        self.access = pd.read_sql("""SELECT uid, cum_jobs, cum_stops FROM built_env.access_grid;""",
                                  con=engine)

    def mobi_data_process(self, test=False):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        print('Load mobility data and add hexagons.')
        self.zones = gpd.GeoDataFrame.from_postgis(sql="""SELECT deso, hex_id, geom FROM spatial_units;""",
                                                   con=engine)
        if test:
            self.mobi_data = pd.read_sql(sql='''SELECT uid, lat, lng, holiday, weekday, wt_total, deso, time_span
                                                FROM segregation.mobi_seg_deso_raw
                                                LIMIT 1000000;''', con=engine)
        else:
            self.mobi_data = pd.read_sql(sql='''SELECT uid, lat, lng, holiday, weekday, wt_total, deso, time_span
                                                FROM segregation.mobi_seg_deso_raw;''', con=engine)
        columns2keep = ['uid', 'holiday', 'weekday', 'wt_total', 'time_span', 'deso']
        deso_list = self.zones.loc[self.zones['hex_id'] == '0', 'deso'].values
        hex_deso_list = self.zones.loc[self.zones['hex_id'] != '0', 'deso'].unique()
        geo_deso = self.mobi_data.loc[self.mobi_data['deso'].isin(deso_list), columns2keep]
        geo_hex = self.mobi_data.loc[self.mobi_data['deso'].isin(hex_deso_list), :]

        geo_deso.loc[:, 'hex'] = geo_deso.loc[:, 'deso']

        def find_hex(data):
            # uid, lat, lng, wt_total, dur, hex_id*
            deso = data.deso.values[0]
            d = data.copy()
            gdf_d = preprocess.df2gdf_point(d, x_field='lng', y_field='lat', crs=4326, drop=False)
            gdf_d = gpd.sjoin(gdf_d,
                              self.zones.loc[self.zones['deso'] == deso, :].drop(columns=['deso']),
                              how='inner')
            return gdf_d[['uid', 'holiday', 'weekday', 'wt_total', 'time_span', 'hex_id']].\
                rename(columns={'hex_id': 'hex'})

        print("Find hexagons for geolocations by DeSO zone.")
        tqdm.pandas()
        geo4graph = geo_hex.groupby('deso').progress_apply(find_hex).reset_index()
        if test:
            self.mobi_data = geo4graph
        else:
            self.mobi_data = pd.concat([geo4graph, geo_deso])

        print('Add individual mobility characteristics, e.g., rg...')
        self.mobi_data = pd.merge(self.mobi_data, self.mobi_metrics, on='uid', how='left')

        print('Add income quantiles')
        self.mobi_data = pd.merge(self.mobi_data, self.socio_metrics, on='zone', how='left')

        print('Add individual residential accessibility metrics')
        self.mobi_data = pd.merge(self.mobi_data, self.access, on='uid', how='left')

        self.mobi_data = self.mobi_data.drop(columns=['level_1'])
        print(self.mobi_data.iloc[0])

    def aggregating_metrics(self, test=False):
        cols = ['number_of_locations', 'number_of_visits',
                'average_displacement', 'radius_of_gyration', 'median_distance_from_home',
                'Not Sweden', 'Other', 'Lowest income group',
                'cum_jobs', 'cum_stops', 'car_ownership']

        def income_evenness_agg(n=4, q_grps=None):
            suma = sum([abs(q - 1 / n) for q in q_grps])
            s_i = n / (2 * n - 2) * suma
            return s_i

        def ice(ai=None, bi=None, popi=None, share_a=0.8044332515556147, share_b=0.11067529894925136):
            oi = popi - ai - bi
            share_o = 1 - share_a - share_b
            return (ai / share_a - bi / share_b) / (ai / share_a + bi / share_b + oi / share_o)

        def unit_weighted_median(data):
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
                metrics_dict[v] = wquantiles.median(data[v], data['wt_total'])
            # Modified aggregation of income unevenness
            q1, q2, q3, q4 = sum(data['income_q1'] * data['wt_total']), sum(data['income_q2'] * data['wt_total']),\
                             sum(data['income_q3'] * data['wt_total']), sum(data['income_q4'] * data['wt_total'])
            sum_ = sum((q1, q2, q3, q4))
            if sum_ != 0:
                q1, q2, q3, q4 = q1/sum_, q2/sum_, q3/sum_, q4/sum_
                metrics_dict['evenness_income'] = income_evenness_agg(n=4, q_grps=(q1, q2, q3, q4))
            else:
                metrics_dict['evenness_income'] = np.nan
            # Modified ICE
            ai, bi, popi = sum(data['birth_se'] * data['wt_total']), \
                         sum(data['birth_other'] * data['wt_total']), \
                         sum(data['pop'] * data['wt_total'])
            if sum((ai, bi, popi)) != 0:
                metrics_dict['ice_birth'] = ice(ai=ai, bi=bi, popi=popi)
            else:
                metrics_dict['ice_birth'] = np.nan
            return pd.Series(metrics_dict)

        grps = ['weekday', 'holiday', 'hex']
        df_g = self.mobi_data[grps].drop_duplicates(subset=grps)
        df_g.loc[:, 'gp'] = np.random.randint(1, 11, df_g.shape[0])
        self.mobi_data = pd.merge(self.mobi_data, df_g, on=grps, how='left')
        print('Calculate metrics of each spatiotemporal unit')

        def by_time(data):
            return data.groupby(['weekday', 'holiday', 'hex']).apply(unit_weighted_median).reset_index()

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
            if test:
                print(df.iloc[0])
            else:
                engine = sqlalchemy.create_engine(
                    f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
                df.to_sql('mobi_seg_hex', engine, schema='segregation', index=False,
                          method='multi', if_exists='append', chunksize=10000)


if __name__ == '__main__':
    seg_agg = MobiSegAggregation()
    seg_agg.load_aux_data()
    seg_agg.mobi_data_process(test=False)
    seg_agg.aggregating_metrics(test=False)
