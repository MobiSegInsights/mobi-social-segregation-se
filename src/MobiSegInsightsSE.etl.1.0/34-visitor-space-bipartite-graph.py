import sys
from pathlib import Path
import os
import pandas as pd
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
import sqlalchemy
import ast
from tqdm import tqdm


ROOT_dir = Path(__file__).parent.parent.parent
sys.path.append(ROOT_dir)
sys.path.insert(0, os.path.join(ROOT_dir, 'lib'))

import preprocess as preprocess


class BipartiteGraphCreation:
    def __init__(self):
        self.spatial_units = None
        self.geolocations = None
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']

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
    bgc.load_zones_geolocations(test=False, weekday=1, holiday=0)
    bgc.bipartite_graph_deso()
    bgc.bipartite_graph_hex()
