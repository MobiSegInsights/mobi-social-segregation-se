import sys
from pathlib import Path
import os
import pandas as pd
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
from h3 import h3
import sqlalchemy
from shapely.geometry import Polygon
from shapely.geometry import box
from tqdm import tqdm

ROOT_dir = Path(__file__).parent.parent.parent
sys.path.append(ROOT_dir)
sys.path.insert(0, os.path.join(ROOT_dir, 'lib'))

import preprocess as preprocess


class HexagonsCreation:
    def __init__(self):
        self.deso_zones = None
        self.geolocations = None
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']

    def load_zones_geolocations(self, test=False):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        self.deso_zones = gpd.GeoDataFrame.from_postgis(sql="""SELECT deso, befolkning, geom FROM zones;""",
                                                        con=engine)
        self.deso_zones.loc[:, 'area'] = self.deso_zones.loc[:, 'geom'].area / 10 ** 6  # m^2 -> km^2

        def reso_assign(x):
            if x < 0.5:
                return 999
            elif (x >= 0.5) & (x < 3.5):
                return 9
            elif (x >= 3.5) & (x < 15):
                return 8
            elif (x >= 15) & (x < 100):
                return 7
            elif (x >= 100) & (x < 720):
                return 6
            else:
                return 5

        self.deso_zones.loc[:, 'reso'] = self.deso_zones.loc[:, 'area'].apply(lambda x: reso_assign(x))
        if test:
            self.geolocations = pd.read_sql(sql="""SELECT uid, lat, lng, deso FROM segregation.mobi_seg_deso_raw
                                                   LIMIT 100000;""",
                                            con=engine)
        else:
            self.geolocations = pd.read_sql(sql="""SELECT uid, lat, lng, deso FROM segregation.mobi_seg_deso_raw;""",
                                            con=engine)

    def h3_by_deso(self, data):
        deso = data['deso'].values[0]
        reso = data['reso'].values[0]
        bd_file = os.path.join(ROOT_dir, f'dbs/{deso}.geojson')
        # Boundary creation
        geom = box(*data.to_crs(4326).total_bounds)
        gdf_box = gpd.GeoDataFrame([1], geometry=[geom])
        gdf_box = gdf_box.rename(columns={0: 'box'})
        gdf_box.to_file(bd_file, driver='GeoJSON')

        # Create hexagons
        sd = gpd.read_file(bd_file)
        hexs = h3.polyfill(sd.geometry[0].__geo_interface__, reso, geo_json_conformant=True)
        polygonise = lambda hex_id: Polygon(h3.h3_to_geo_boundary(
            hex_id, geo_json=True))

        all_polys = gpd.GeoSeries(list(map(polygonise, hexs)),
                                  index=hexs,
                                  crs="EPSG:4326")
        h3_all = gpd.GeoDataFrame({"geometry": all_polys, "hex_id": all_polys.index}, crs=all_polys.crs)
        h3_land = gpd.overlay(h3_all, data.to_crs(h3_all.crs), how="intersection")

        # Load geolocations
        df_points_s = self.geolocations.loc[self.geolocations['deso'] == deso, :]
        gdf_points = preprocess.df2gdf_point(df_points_s, x_field='lng', y_field='lat', crs=4326, drop=True)
        gdf_points = gpd.sjoin(gdf_points, h3_land, how='inner')

        # Filter hexagons based on geolocations
        cols = ['hex_id', 'deso', 'geometry']
        h32keep = h3_land.loc[h3_land.hex_id.isin(gdf_points.hex_id.unique()), cols]

        # Clean up deso boundary file
        os.remove(bd_file)
        return h32keep


if __name__ == '__main__':
    test = False
    hc = HexagonsCreation()
    hc.load_zones_geolocations(test=test)
    gdf_deso = hc.deso_zones.loc[hc.deso_zones.reso == 999, ['deso', 'geom']].\
        to_crs(4326).rename(columns={'geom': 'geometry'})
    if test:
        hc.deso_zones = hc.deso_zones.loc[hc.deso_zones.reso != 999, :].sample(20, random_state=7)
    else:
        hc.deso_zones = hc.deso_zones.loc[hc.deso_zones.reso != 999, :]
    list_gdf = []

    for r, g in tqdm(hc.deso_zones.groupby('deso', group_keys=True), desc='Process deso zones'):
        hx = hc.h3_by_deso(g)
        list_gdf.append(hx)
    gdf = pd.concat([gdf_deso, pd.concat(list_gdf)]).fillna(0)
    engine = sqlalchemy.create_engine(
        f'postgresql://{hc.user}:{hc.password}@localhost:{hc.port}/{hc.db_name}?gssencmode=disable')
    gdf.rename(columns={'geometry': 'geom'}).to_postgis("spatial_units", con=engine)

