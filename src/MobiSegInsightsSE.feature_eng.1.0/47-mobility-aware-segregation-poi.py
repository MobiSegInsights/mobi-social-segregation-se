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
from p_tqdm import p_map
from sklearn.neighbors import KDTree


ROOT_dir = Path(__file__).parent.parent.parent
sys.path.append(ROOT_dir)
sys.path.insert(0, os.path.join(ROOT_dir, 'lib'))

import preprocess as preprocess


class MobiSegAggregationPOI:
    def __init__(self):
        # Auxiliary data
        self.access = None
        self.mobi_metrics = None
        self.socio_metrics = None
        # Mobility data
        self.gdf_stops = None
        # POIs
        self.tree = None
        self.gdf_pois = None
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
        self.access = pd.read_sql("""SELECT uid, cum_jobs_car, cum_jobs_pt FROM built_env.access2jobs;""", con=engine)

    def poi_data_loader(self):
        print('Load POI data.')
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        # POIs in Sweden
        self.gdf_pois = gpd.GeoDataFrame.from_postgis(sql="""SELECT osm_id, "Tag", geom FROM built_env.pois;""",
                                                      con=engine)
        self.gdf_pois = self.gdf_pois.to_crs(3006)
        self.gdf_pois.loc[:, 'y'] = self.gdf_pois.geom.y
        self.gdf_pois.loc[:, 'x'] = self.gdf_pois.geom.x

    def mobi_data_process(self, test=False):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        print('Load mobility data and add POIs.')
        if test:
            df_stops = pd.read_sql(sql='''SELECT uid, lat, lng, holiday, weekday, wt_total, deso, time_span
                                                FROM segregation.mobi_seg_deso_raw
                                                LIMIT 100000;''', con=engine)
        else:
            df_stops = pd.read_sql(sql='''SELECT uid, lat, lng, holiday, weekday, wt_total, deso, time_span
                                                FROM segregation.mobi_seg_deso_raw;''', con=engine)
        # columns2keep = ['uid', 'holiday', 'weekday', 'wt_total', 'time_span', 'deso']

        gdf_stops = preprocess.df2gdf_point(df_stops, 'lng', 'lat', crs=4326, drop=False)
        df_home = pd.read_sql(sql=f"""SELECT uid, lat, lng FROM home_p;""", con=engine)
        df_home.loc[:, 'home'] = 1
        gdf_stops = pd.merge(gdf_stops, df_home, on=['uid', 'lat', 'lng'], how='left')
        gdf_stops.fillna(0, inplace=True)

        # Process stops
        gdf_stops = gdf_stops.to_crs(3006)
        gdf_stops.loc[:, 'y'] = gdf_stops.geometry.y
        gdf_stops.loc[:, 'x'] = gdf_stops.geometry.x
        print(len(gdf_stops))
        gdf_stops.replace([np.inf, -np.inf], np.nan, inplace=True)
        gdf_stops.dropna(subset=["x", "y"], how="any", inplace=True)
        print("After processing infinite values", len(gdf_stops))

        # Find POI for each stop
        print('Find POI for each stop')
        self.tree = KDTree(self.gdf_pois[["y", "x"]], metric="euclidean")
        ind, dist = self.tree.query_radius(gdf_stops[["y", "x"]].to_records(index=False).tolist(),
                                      r=300, return_distance=True, count_only=False, sort_results=True)
        gdf_stops.loc[:, 'poi_num'] = [len(x) for x in ind]
        gdf_stops.loc[gdf_stops.poi_num > 0, 'osm_id'] = [self.gdf_pois.loc[x[0], 'osm_id'] for x in ind if len(x) > 0]
        gdf_stops.loc[gdf_stops.poi_num > 0, 'dist'] = [x[0] for x in dist if len(x) > 0]
        self.gdf_stops = pd.merge(gdf_stops, self.gdf_pois[['osm_id', 'Tag']], on='osm_id', how='left')

        print('Add individual mobility characteristics, e.g., rg...')
        self.gdf_stops = pd.merge(self.gdf_stops, self.mobi_metrics, on='uid', how='left')

        print('Add income quantiles')
        self.gdf_stops = pd.merge(self.gdf_stops, self.socio_metrics, on='zone', how='left')

        print('Add individual residential accessibility metrics')
        self.gdf_stops = pd.merge(self.gdf_stops, self.access, on='uid', how='left')

        self.gdf_stops = self.gdf_stops.loc[self.gdf_stops.home == 0, :]
        self.gdf_stops.drop(columns=['geometry', 'home', 'y', 'x', 'zone', 'region'], inplace=True)
        print(f"Number of stops: {len(self.gdf_stops)} with {self.gdf_stops.osm_id.nunique()} unique POIs.")
        print(self.gdf_stops.iloc[0])

    def aggregating_metrics(self, test=False):
        cols = ['number_of_locations', 'number_of_visits',
                'average_displacement', 'radius_of_gyration', 'median_distance_from_home',
                'Not Sweden', 'Other', 'Lowest income group',
                'cum_jobs_car', 'cum_jobs_pt', 'car_ownership']

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

        grps = ['weekday', 'holiday', 'osm_id']
        df_g = self.gdf_stops[grps].drop_duplicates(subset=grps)
        df_g.loc[:, 'gp'] = np.random.randint(1, 11, df_g.shape[0])
        self.gdf_stops = pd.merge(self.gdf_stops, df_g, on=grps, how='left')
        print('Calculate metrics of each spatiotemporal unit')

        def by_time(data):
            return data.groupby(['weekday', 'holiday', 'osm_id']).apply(unit_weighted_median).reset_index()

        def span2seq(time_seq_list):
            seq = list(range(time_seq_list[0], time_seq_list[1] + 1))
            if len(time_seq_list) > 2:
                seq2 = list(range(time_seq_list[2], time_seq_list[3] + 1))
                seq = seq2 + seq
            return seq

        for gp_id, df in self.gdf_stops.groupby('gp'):
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
                df.to_sql('mobi_seg_poi', engine, schema='segregation', index=False,
                          method='multi', if_exists='append', chunksize=10000)


if __name__ == '__main__':
    seg_agg = MobiSegAggregationPOI()
    seg_agg.load_aux_data()
    seg_agg.poi_data_loader()
    seg_agg.mobi_data_process(test=False)
    seg_agg.aggregating_metrics(test=False)
