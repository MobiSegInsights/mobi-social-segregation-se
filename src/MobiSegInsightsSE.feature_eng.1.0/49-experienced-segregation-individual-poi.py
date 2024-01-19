import sys
from pathlib import Path
import os
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
import pandas as pd
import sqlalchemy
import numpy as np
import ast
import random
from tqdm import tqdm
from p_tqdm import p_map
from sklearn.neighbors import KDTree


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
        self.resi = None
        self.gdf_pois = None
        self.zonal_seg = None
        self.tree = None
        self.deso_sim_matrix = None
        self.zones = None
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']

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

    def load_individual_data(self, grp_num=30, test=False, save_raw=False):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        print('Load mobility data and add pois.')
        self.zones = gpd.GeoDataFrame.from_postgis(sql="""SELECT deso, hex_id, geom FROM spatial_units;""",
                                                   con=engine)
        if test:
            self.mobi_data = pd.read_sql(sql='''SELECT uid, lat, lng, holiday, weekday, wt_total, deso, time_span
                                                FROM segregation.mobi_seg_deso_raw
                                                LIMIT 1000000;''', con=engine)
        else:
            self.mobi_data = pd.read_sql(sql='''SELECT uid, lat, lng, holiday, weekday, wt_total, deso, time_span
                                                FROM segregation.mobi_seg_deso_raw;''', con=engine)
        gdf_stops = preprocess.df2gdf_point(self.mobi_data, 'lng', 'lat', crs=4326, drop=False)
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
        self.mobi_data = pd.merge(gdf_stops, self.gdf_pois[['osm_id', 'Tag']], on='osm_id', how='left')
        columns2keep = ['uid', 'deso', 'home', 'osm_id', 'Tag', 'dist', 'holiday', 'weekday', 'wt_total', 'time_span']
        self.mobi_data = self.mobi_data[columns2keep]
        print(self.mobi_data.iloc[0])

        # Group users
        random.seed(1)
        uids = self.mobi_data.uid.unique()
        gps = np.random.randint(1, grp_num + 1, len(uids))
        gp_dict = dict(zip(uids, gps))
        self.mobi_data.loc[:, 'gp'] = self.mobi_data['uid'].apply(lambda x: gp_dict[x])

        if test:
            print('Test mode, only look at 10000 users.')
            self.mobi_data = self.mobi_data.loc[self.mobi_data['gp'] == 1, :]
        print(self.mobi_data.iloc[0])
        if (not test) & save_raw:
            print('Save mobility data at poi level.')
            self.mobi_data.to_sql('mobi_seg_poi_raw', engine, schema='segregation', index=False,
                                  method='multi', if_exists='append', chunksize=10000)

    def load_zonal_data(self):
        print('Load segregation metrics at the poi level...')
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        zonal_seg_ = pd.read_sql(sql='''SELECT osm_id, time_seq, ice_birth, weekday, holiday
                                            FROM segregation.mobi_seg_poi;''', con=engine)
        self.zonal_seg = dict()
        lbs = [['w0h0', 'w0h1'], ['w1h0', 'w1h1']]
        for weekday in (0, 1):
            for holiday in (0, 1):
                temp_ = zonal_seg_.loc[(zonal_seg_.weekday == weekday) & (zonal_seg_.holiday == holiday)].\
                    drop(columns=['weekday', 'holiday'])
                self.zonal_seg[lbs[weekday][holiday]] = temp_.pivot(index='time_seq',
                                                                    columns='osm_id',
                                                                    values='ice_birth')
        print('Load residential segregation for being at home...')
        self.resi = pd.read_sql(sql='''SELECT region AS deso, ice AS ice_r
                                       FROM segregation.resi_seg_deso
                                       WHERE var='birth_region';''', con=engine)
        self.resi = dict(zip(self.resi.deso, self.resi.ice_r))

    def aggregating_metrics_indi(self):
        def time_seq_median(data):
            return pd.Series({"time_seq": data.time_seq.values[0],
                              'ice_birth': data.ice_birth.median()})

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

            def poi_time_to_seg(row):
                if row['home'] == 0:
                    try:
                        x = self.zonal_seg[f"w{int(row['weekday'])}h{int(row['holiday'])}"].\
                            loc[(row['time_seq'], row['osm_id'])]
                    except:
                        x = 9
                else:
                    try:
                        x = self.resi[row['deso']]
                    except:
                        x = 9
                return x
            tqdm.pandas()
            df.loc[:, 'ice_birth'] = df.progress_apply(lambda row: poi_time_to_seg(row), axis=1)
            share = len(df.loc[df.ice_birth == 9, :]) / len(df) * 100
            print(f"Share of missing values: {share} %.")
            df = df.loc[df.ice_birth != 9, :]
            print(f'Calculate an average day individually by weekday and holiday.')
            rstl = p_map(by_time, [g for _, g in df.groupby('time_seq', group_keys=True)])
            df = pd.concat(rstl)

            engine = sqlalchemy.create_engine(
                f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
            df.to_sql('mobi_seg_poi_individual', engine, schema='segregation', index=False,
                      method='multi', if_exists='append', chunksize=10000)


if __name__ == '__main__':
    # Aggregating metrics individually (experienced segregation)
    seg_indi = MobiSegAggregationIndividual()
    seg_indi.poi_data_loader()
    seg_indi.load_individual_data(grp_num=12, test=False, save_raw=True)
    seg_indi.load_zonal_data()
    seg_indi.aggregating_metrics_indi()
