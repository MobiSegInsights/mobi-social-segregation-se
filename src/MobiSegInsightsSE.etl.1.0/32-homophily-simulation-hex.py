import sys
from pathlib import Path
import os
import pandas as pd
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
import sqlalchemy
from collections import Counter
import random
from tqdm import tqdm
from p_tqdm import p_map
import numpy as np
from scipy.spatial import distance
from sklearn.neighbors import KDTree


ROOT_dir = Path(__file__).parent.parent.parent
sys.path.append(ROOT_dir)
sys.path.insert(0, os.path.join(ROOT_dir, 'lib'))

import preprocess as preprocess


class HomophilyHexSim:
    def __init__(self):
        self.gdf_stops = None
        self.gdf_pois = None
        self.df_home = None
        self.stops2shift = None
        self.zones = None
        self.tree = None
        self.df_d = pd.read_csv(os.path.join(ROOT_dir, 'results/distance_decay.csv'))
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']
        self.db_name_osm = preprocess.keys_manager['osmdb']['name']

    def poi_data_loader(self):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        # POIs in Sweden
        gdf_pois = gpd.GeoDataFrame.from_postgis(sql="""SELECT osm_id, "Tag", geom FROM built_env.pois;""", con=engine)
        gdf_pois = gdf_pois.to_crs(3006)
        gdf_pois.loc[:, 'y'] = gdf_pois.geom.y
        gdf_pois.loc[:, 'x'] = gdf_pois.geom.x

        # Find which hex zone each POI belongs to
        self.zones = gpd.GeoDataFrame.from_postgis(sql="""SELECT hex_id AS hex_s, deso, geom FROM spatial_units;""", con=engine)
        self.zones.loc[:, 'hex_id'] = self.zones.apply(lambda row: row['hex_s'] if row['hex_s'] != '0' else row['deso'], axis=1)
        self.gdf_pois = gpd.sjoin(gdf_pois,
                                  self.zones[['hex_id', 'geom']].rename(columns={'hex_id': 'hex_s'}).to_crs(3006)
                                  )
        self.gdf_pois = self.gdf_pois.reset_index(drop=True)

    def stop_data_loader(self, test=False):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        # Load stops and add home label
        if test:
            df_stops = pd.read_sql(sql=f"""SELECT uid, lat, lng, wt_total, time_span, deso
                                                   FROM segregation.mobi_seg_deso_raw
                                                   WHERE weekday=1 AND holiday=0
                                                   LIMIT 100000;""",
                                   con=engine)
        else:
            df_stops = pd.read_sql(sql=f"""SELECT uid, lat, lng, wt_total, time_span, deso
                                           FROM segregation.mobi_seg_deso_raw
                                           WHERE weekday=1 AND holiday=0;""",
                                   con=engine)
        gdf_stops = preprocess.df2gdf_point(df_stops, 'lng', 'lat', crs=4326, drop=False)
        self.df_home = pd.read_sql(sql=f"""SELECT uid, lat, lng
                                       FROM home_p;""",
                              con=engine)
        self.df_home.loc[:, 'home'] = 1
        gdf_stops = pd.merge(gdf_stops, self.df_home, on=['uid', 'lat', 'lng'], how='left')
        gdf_stops = gdf_stops.fillna(0)

        # Find hexagons for stops
        deso_list = self.zones.loc[self.zones['hex_s'] == '0', 'deso'].values
        hex_deso_list = self.zones.loc[self.zones['hex_s'] != '0', 'deso'].unique()
        geo_deso = gdf_stops.loc[gdf_stops['deso'].isin(deso_list), :]
        geo_hex = gdf_stops.loc[gdf_stops['deso'].isin(hex_deso_list), :]

        geo_deso.loc[:, 'hex'] = geo_deso.loc[:, 'deso']

        def find_hex(data):
            # uid, lat, lng, wt_total, dur, hex_id*
            deso = data.deso.values[0]
            gdf_d = data.copy()
            gdf_d = gpd.sjoin(gdf_d,
                              self.zones.loc[self.zones['deso'] == deso, :].drop(columns=['deso']).to_crs(4326),
                              how='inner')
            return gdf_d.rename(columns={'hex_s': 'hex'})

        print("Find hexagons for geolocations by DeSO zone.")
        tqdm.pandas()
        geo4graph = geo_hex.groupby('deso').progress_apply(find_hex).reset_index(drop=True)
        gdf_stops = pd.concat([geo4graph, geo_deso]).drop(columns=['index_right'])
        print(gdf_stops.iloc[0])

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

    def data2shift(self, grp=32, parallel=48):
        self.stops2shift = self.gdf_stops.loc[(self.gdf_stops.home == 0) & (~self.gdf_stops.Tag.isna()), :].copy()
        L = len(self.stops2shift)
        print(f'Number of stops to simulate: {L}')
        random.seed(1)
        self.stops2shift.loc[:, 'pr'] = np.random.randint(1, parallel + 1, L)

        # Group users
        uids = self.stops2shift.uid.unique()
        gps = np.random.randint(1, grp + 1, len(uids))
        gp_dict = dict(zip(uids, gps))
        self.stops2shift.loc[:, 'gp'] = self.stops2shift['uid'].apply(lambda x: gp_dict[x])

    def poi2nearby(self, row):
        shift_radius = 1000  # m
        shift_radius_lower = 30  # m
        # Distance-constrained POI shifting
        X = self.gdf_pois.loc[self.gdf_pois.osm_id == row['osm_id'], 'x'].values[0]
        Y = self.gdf_pois.loc[self.gdf_pois.osm_id == row['osm_id'], 'y'].values[0]
        ind, dist = self.tree.query_radius([(Y, X)], r=shift_radius,
                                      return_distance=True, count_only=False, sort_results=True)
        ind = ind[0]
        dist = dist[0]

        def tag_categorization(x):
            if x == row['Tag']:
                return 1
            if ('(' in row['Tag']) & ('(' in x):
                if row['Tag'].split(' (')[0] == x.split(' (')[0]:
                    return 2
            if (row['Tag'] in ('Office', 'Craft')) & (x in ('Office', 'Craft')):
                return 3
            if ('(s)' in row['Tag']) | (row['Tag'] == 'Shop'):
                if ('(s)' in x) | (x == 'Shop'):
                    return 4
            return 0

        if len(ind) > 0:
            df = pd.DataFrame()
            df.loc[:, "id"] = range(0, len(ind))
            df.loc[:, "tag"] = [self.gdf_pois.loc[x, 'Tag'] for x in ind]
            df.loc[:, "dist"] = dist
            df.loc[:, "hex_s"] = [self.gdf_pois.loc[x, 'hex_s'] for x in ind]
            # Exclude POIs too close
            df = df.loc[df.dist > shift_radius_lower, :]
            if len(df) > 0:
                df.loc[:, "tag_cat"] = df.loc[:, "tag"].apply(lambda x: tag_categorization(x))
                if df.loc[:, "tag_cat"].sum() > 0:
                    # sample 1 POI following the conditions 1, 2, 3, and 4
                    for cat in (1, 2, 3, 4):
                        df2sample = df.loc[df.tag_cat == cat, :]
                        if len(df2sample) > 0:
                            hex_pool = random.choices(df2sample['hex_s'].values, k=100)
                            # hex_st = df2sample['hex_s'].values[0]
                            break
                else:
                    hex_pool = []
                    # hex_st = ''
            else:
                hex_pool = []
                # hex_st = ''

            if len(hex_pool) > 0:
                hx_str = str(dict(Counter(hex_pool)))
            else:
                hx_str = ''

            return pd.Series(dict(hex_s=hx_str))

    def simulation(self, data):
        shifted = data.apply(self.poi2nearby, axis=1)
        return pd.concat([data.drop(columns=['gp', 'pr']), shifted], axis=1)

    def data_merge_and_save(self, data_sim=None):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        print('Merging simulated data...')
        stops2keep = self.gdf_stops.loc[~((self.gdf_stops.home == 0) & (~self.gdf_stops.Tag.isna())), :]
        data2save = pd.concat([data_sim, stops2keep])
        print('Saving...')
        data2save.drop(columns=['x', 'y', 'geometry']). \
            to_sql('mobi_seg_hex_raw_sim1_w1h0', engine, schema='segregation', index=False,
                   method='multi', if_exists='append', chunksize=10000)


if __name__ == '__main__':
    hhs = HomophilyHexSim()
    hhs.poi_data_loader()
    hhs.stop_data_loader(test=False)
    hhs.data2shift(grp=3, parallel=48)
    sp_list = []
    for n, df in hhs.stops2shift.groupby('gp'):
        print(f'Processing group {n}...')
        rstl = p_map(hhs.simulation, [g for _, g in df.groupby('pr')])
        sp_list.append(pd.concat(rstl))
    sp = pd.concat(sp_list)
    print(sp.iloc[0])
    hhs.data_merge_and_save(data_sim=sp)
