import sys
from pathlib import Path
import os
import pandas as pd
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
import sqlalchemy
import ast
import numpy as np
from tqdm import tqdm
from sklearn.neighbors import KDTree


ROOT_dir = Path(__file__).parent.parent.parent
sys.path.append(ROOT_dir)
sys.path.insert(0, os.path.join(ROOT_dir, 'lib'))

import preprocess as preprocess


class BipartiteGraphCreation:
    def __init__(self):
        self.spatial_units = None
        self.gdf_pois = None
        self.tree = None
        self.geolocations = None
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

    def load_zones_geolocations(self, test=False, weekday=None, holiday=None):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        # Load spatial units (hexagons and deso zones)
        print('Load spatial units.')
        self.spatial_units = gpd.GeoDataFrame.from_postgis(sql="""SELECT deso, hex_id, geom FROM spatial_units;""",
                                                        con=engine)
        print('Load geolocations.')
        if test:
            self.geolocations = pd.read_sql(sql=f"""SELECT uid, lat, lng, wt_total, time_span, deso 
                                                    FROM segregation.mobi_seg_deso_raw
                                                    WHERE weekday={weekday} AND holiday={holiday}
                                                    LIMIT 100000;""",
                                            con=engine)
        else:
            self.geolocations = pd.read_sql(sql=f"""SELECT uid, lat, lng, wt_total, time_span, deso 
                                                    FROM segregation.mobi_seg_deso_raw
                                                    WHERE weekday={weekday} AND holiday={holiday};""",
                                            con=engine)
        print(f'{len(self.geolocations)} from {self.geolocations.uid.nunique()} individual devices are loaded.')

        # Get span length (stay duration by count)
        print('Process geolocations to get stay duration in half-hour interval count.')
        self.geolocations.loc[:, 'time_span'] = self.geolocations.loc[:, 'time_span'].\
            apply(lambda x: ast.literal_eval(
            x.replace("{", "(").replace("}", ")")
        ))

        def span2length(time_seq_list):
            L = time_seq_list[1] - time_seq_list[0] + 1
            if len(time_seq_list) > 2:
                L2 = time_seq_list[3] - time_seq_list[2] + 1
                L = L2 + L
            return L

        self.geolocations.loc[:, 'dur'] = self.geolocations.loc[:, 'time_span'].apply(span2length)

        # Add socioeconomic attributes to individuals
        uid_zone = pd.read_sql(sql='''SELECT uid, zone FROM mobility.indi_mobi_metrics_p;''', con=engine)
        socio_metrics = pd.read_sql(sql='''SELECT zone, birth_se, birth_other, pop FROM grids;''', con=engine)
        socio_metrics = socio_metrics.loc[socio_metrics.zone.isin(uid_zone.zone), :]
        socio_metrics = socio_metrics.loc[socio_metrics['pop'] > 0, :]
        uid_zone = pd.merge(uid_zone, socio_metrics, on='zone', how='left')
        # uid_zone.loc[:, 'eth_wt'] = uid_zone['birth_se'] - uid_zone['birth_other']
        print('Add ethnicity information to individual.')
        self.geolocations = pd.merge(self.geolocations,
                                     uid_zone[['uid', 'birth_se', 'birth_other', 'pop']],
                                     on='uid', how='left')

    def stops2poi(self, visit_num_threshold=5):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        gdf_stops = preprocess.df2gdf_point(self.geolocations, 'lng', 'lat', crs=4326, drop=False)
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
        self.geolocations = pd.merge(gdf_stops, self.gdf_pois[['osm_id', 'Tag']], on='osm_id', how='left')

        # Filter stops for weekday=1 and holiday=0 with more than x visits
        df_seg_poi = pd.read_sql(sql=f"""SELECT osm_id, num_visits FROM segregation.mobi_seg_poi
                                         WHERE weekday=1 AND holiday=0;""", con=engine)
        df_seg_poi = df_seg_poi.groupby('osm_id')['num_visits'].sum().reset_index()
        osm2keep = df_seg_poi.loc[df_seg_poi.num_visits > visit_num_threshold, 'osm_id'].unique()
        self.geolocations = self.geolocations.loc[self.geolocations.osm_id.isin(osm2keep), :]

        # Preview the data
        self.geolocations.drop(columns=['geometry', 'home', 'y', 'x'], inplace=True)
        print(f"Number of stops: {len(self.geolocations)} with {self.geolocations.osm_id.nunique()} unique POIs.")
        print(self.geolocations.iloc[0])

    def bipartite_graph_poi(self):
        def link_strength(data):
            return pd.Series({'count': sum(data['dur'] * data['wt_total']),
                              'birth_se': data['birth_se'].values[0],
                              'birth_other': data['birth_other'].values[0],
                              'pop': data['pop'].values[0]})

        print("Count visitor-deso link strength.")
        tqdm.pandas()
        g = self.geolocations.groupby(['uid', 'osm_id']).progress_apply(link_strength).reset_index().\
            rename(columns={'osm_id': 'poi'})
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')

        print("Save POI bipartite graph.")
        g.to_sql('poi', engine, schema='bipartite_graph', index=False,
                 method='multi', if_exists='append', chunksize=10000)

    def bipartite_graph_deso(self):
        def link_strength(data):
            return pd.Series({'count': sum(data['dur'] * data['wt_total'])})

        print("Count visitor-deso link strength.")
        tqdm.pandas()
        g = self.geolocations.groupby(['uid', 'deso']).progress_apply(link_strength).reset_index().\
            rename(columns={'deso': 'zone'})
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')

        print("Save DeSO bipartite graph.")
        g.to_sql('deso', engine, schema='bipartite_graph', index=False,
                 method='multi', if_exists='append', chunksize=10000)

    def bipartite_graph_hex(self):
        deso_list = self.spatial_units.loc[self.spatial_units['hex_id'] == '0', 'deso'].values
        hex_deso_list = self.spatial_units.loc[self.spatial_units['hex_id'] != '0', 'deso'].unique()
        geo_deso = self.geolocations.loc[self.geolocations['deso'].isin(deso_list), :]
        geo_hex = self.geolocations.loc[self.geolocations['deso'].isin(hex_deso_list), :]

        def link_strength(data):
            return pd.Series({'count': sum(data['dur'] * data['wt_total'])})

        def find_hex(data):
            # uid, lat, lng, wt_total, dur, hex_id*
            deso = data.deso.values[0]
            d = data.loc[:, ['uid', 'lat', 'lng', 'wt_total', 'dur']]
            gdf_d = preprocess.df2gdf_point(d, x_field='lng', y_field='lat', crs=4326, drop=True)
            gdf_d = gpd.sjoin(gdf_d,
                              self.spatial_units.loc[self.spatial_units['deso'] == deso, :].drop(columns=['deso']),
                              how='inner')
            return gdf_d[['uid', 'hex_id', 'wt_total', 'dur']]

        print("Count visitor-deso link strength (small DeSO zones w/o hexagons).")
        tqdm.pandas()
        g1 = geo_deso.groupby(['uid', 'deso']).progress_apply(link_strength).reset_index().\
            rename(columns={'deso': 'zone'})

        print("Find hexagons for geolocations by DeSO zone.")
        tqdm.pandas()
        geo4graph = geo_hex.groupby('deso').progress_apply(find_hex).reset_index()

        print("Count visitor-hexagon link strength (larger DeSO zones w/ hexagons).")
        tqdm.pandas()
        g2 = geo4graph.groupby(['uid', 'hex_id']).progress_apply(link_strength).reset_index().\
            rename(columns={'hex_id': 'zone'})
        g = pd.concat([g1, g2])
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')

        print("Save hexagon bipartite graph.")
        g.to_sql('hex', engine, schema='bipartite_graph', index=False,
                 method='multi', if_exists='append', chunksize=10000)


if __name__ == '__main__':
    bgc = BipartiteGraphCreation()
    bgc.poi_data_loader()
    bgc.load_zones_geolocations(test=False, weekday=1, holiday=0)
    bgc.stops2poi(visit_num_threshold=5)
    bgc.bipartite_graph_poi()
#    bgc.bipartite_graph_deso()
#    bgc.bipartite_graph_hex()
