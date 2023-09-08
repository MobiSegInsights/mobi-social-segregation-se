import sys
from pathlib import Path
import os
import shutil
os.environ['USE_PYGEOS'] = '0'
import pandas as pd
import geopandas as gpd
import sqlalchemy
from tqdm import tqdm


ROOT_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(ROOT_dir)
sys.path.insert(0, os.path.join(ROOT_dir, 'lib'))

import routing_helpers as rh
import preprocess as preprocess


class CountyDataPrep4PTAccess:
    def __init__(self):
        self.home = None
        self.gdf_g = None
        self.counties = None
        self.gdf_z = None
        self.user_grid = []
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']

    def load_geo(self):
        engine = sqlalchemy.create_engine(f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        self.gdf_z = gpd.GeoDataFrame.from_postgis(sql="""SELECT deso, geom FROM zones;""", con=engine)
        self.gdf_z.loc[:, 'deso_2'] = self.gdf_z.loc[:, 'deso'].apply(lambda x: x[:2])
        self.counties = self.gdf_z.loc[:, 'deso_2'].unique()
        self.home = pd.read_sql(sql="""SELECT uid, zone, deso FROM home_p;""", con=engine)
        self.home.loc[:, 'deso_2'] = self.home.loc[:, 'deso'].apply(lambda x: x[:2])
        self.gdf_g = gpd.read_postgis(sql="""SELECT zone, pop, job, geom FROM grids;""", con=engine)

    def osm_extent(self, county=None):
        gdf_c = self.gdf_z.loc[self.gdf_z.deso_2 == county, :]
        convex_hull = gdf_c.unary_union.convex_hull.buffer(40000)
        convex_hull = gpd.GeoDataFrame(geometry=[convex_hull], crs=gdf_c.crs)
        print(f"Area for {county}", convex_hull.area / 10 ** 6)

        # prepare .poly file
        print("Prepare .poly file of county boundary")
        tf = os.path.join(ROOT_dir, f'dbs/geo/sweden_bounding_{county}.poly')
        rh.gdf2poly(geodata=convex_hull, targetfile=tf, buffer=0)

        # Create directory for county
        print("Prepare county data folder")
        directory_path = os.path.join(ROOT_dir, f'dbs/accessibility/c_{county}')
        source_file = os.path.join(ROOT_dir, f'dbs/accessibility/sweden_fixed.zip')

        if os.path.exists(directory_path):
            print(f"The directory '{directory_path}' exists.")
        else:
            os.makedirs(directory_path)
            shutil.copy2(source_file, directory_path)
            print(f"The directory '{directory_path}' created. GTFS file copied.")

        # Process data
        osm_file = os.path.join(ROOT_dir, 'dbs/geo/sweden-latest.osm.pbf')
        terget_file = os.path.join(ROOT_dir, directory_path, f'sweden-{county}.osm.pbf')
        poly_file = os.path.join(ROOT_dir, f'dbs/geo/sweden_bounding_{county}.poly')
        osmosis_path = 'osmosis'
        if os.path.exists(terget_file) is not True:
            print('Cropping OSM data.')
            rh.osm_country2region(osm_file=osm_file,
                                  terget_file=terget_file,
                                  poly_file=poly_file,
                                  osmosis_path=osmosis_path)
        else:
            print("Skip cropping because the file exists.")
        return convex_hull

    def od_data_prep(self, county=None, geo_extent=None):
        # Refine destinations
        gdf_d = gpd.sjoin(self.gdf_g.loc[self.gdf_g.job > 0, :], geo_extent)
        gdf_d = gdf_d.drop(columns=['index_right']).rename(columns={'geom': 'geometry'}).set_geometry('geometry')

        # Refine origins
        df2p = self.home.loc[self.home.deso_2 == county, :].copy()
        if len(self.user_grid) > 0:
            df2p = df2p.loc[~df2p.zone.isin(self.user_grid), :]
        gdf_o = self.gdf_g.loc[self.gdf_g.zone.isin(df2p.zone), :].copy().\
            rename(columns={'geom': 'geometry'}).\
            set_geometry('geometry')

        print("Length of origins:", len(gdf_o))
        print("Length of destinations:", len(gdf_d))

        gdf_o["geometry"] = gdf_o.geometry.centroid
        gdf_d["geometry"] = gdf_d.geometry.centroid
        gdf_d = gdf_d.to_crs(4326)
        gdf_o = gdf_o.to_crs(4326)
        gdf_o.loc[:, 'lon'] = gdf_o.geometry.x
        gdf_d.loc[:, 'lon'] = gdf_d.geometry.x
        gdf_o.loc[:, 'lat'] = gdf_o.geometry.y
        gdf_d.loc[:, 'lat'] = gdf_d.geometry.y

        origins = gdf_o.loc[:, ['zone', 'lon', 'lat']].rename(columns={'zone': 'id'})
        destinations = gdf_d.loc[:, ['zone', 'lon', 'lat', 'job']].rename(columns={'zone': 'id'})
        o_file = os.path.join(ROOT_dir, f"dbs/accessibility/data/origins_{county}.csv")
        d_file = os.path.join(ROOT_dir, f"dbs/accessibility/data/destinations_{county}.csv")
        origins.to_csv(o_file, index=False)
        destinations.to_csv(d_file, index=False)
        # Keep track of covered origins (user home grids)
        self.user_grid += gdf_o.loc[:, 'zone'].values.tolist()


if __name__ == '__main__':
    dp = CountyDataPrep4PTAccess()
    dp.load_geo()
    for c in tqdm(dp.counties, desc='Processing by county'):
        convex_hull = dp.osm_extent(county=c)
        dp.od_data_prep(county=c, geo_extent=convex_hull)
