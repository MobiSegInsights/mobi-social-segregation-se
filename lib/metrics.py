import os
import subprocess
import yaml
import sqlalchemy
import pandas as pd
import skmob
from skmob.measures.individual import radius_of_gyration, distance_straight_line, number_of_locations, number_of_visits
from tqdm import tqdm

def get_repo_root():
    """Get the root directory of the repo."""
    dir_in_repo = os.path.dirname(os.path.abspath('__file__'))
    return subprocess.check_output('git rev-parse --show-toplevel'.split(),
                                   cwd=dir_in_repo,
                                   universal_newlines=True).rstrip()


ROOT_dir = get_repo_root()
with open(os.path.join(ROOT_dir, 'dbs', 'keys.yaml')) as f:
    keys_manager = yaml.load(f, Loader=yaml.FullLoader)

from lib import preprocess as preprocess


class MobilityMeasuresIndividual:
    def __init__(self):
        self.home = None
        self.mobi_data = None
        self.resi_seg = None
        self.zone_stats = None
        self.mobi_data_traj = None
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']

    def load_home_seg_uid(self):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
        print("Loading home and segregation data.")
        self.home = pd.read_sql_query(sql="""SELECT uid, deso, lng, lat FROM home_sub;""", con=engine)
        self.resi_seg = pd.read_sql_query(sql="""SELECT region, var, "S", iso FROM resi_segregation;""", con=engine)
        self.zone_stats = pd.read_sql_query(sql="""SELECT * FROM zone_stats;""", con=engine)

    def load_mobi_data(self):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
        print("Loading mobility data.")
        self.mobi_data = pd.read_sql_query(sql="""SELECT uid, date, month, "TimeLocal", dur,
        lat, lng, cluster FROM stops_subset;""", con=engine)
        self.mobi_data = self.mobi_data.loc[self.mobi_data.uid.isin(self.home.uid), :]
        print("Converting it to scikit-learn format.")
        self.mobi_data_traj = skmob.TrajDataFrame(self.mobi_data,
                                                  latitude='lat', longitude='lng',
                                                  datetime='TimeLocal',
                                                  user_id='uid')

    def rg(self):
        return radius_of_gyration(self.mobi_data_traj)

    def displacement_average(self):
        d_strl = distance_straight_line(self.mobi_data_traj)
        num_visits = number_of_visits(self.mobi_data_traj)
        df_avd = pd.merge(d_strl, num_visits, on=['uid'])
        df_avd.loc[:, 'disp_ave'] = df_avd.loc[:, 'distance_straight_line'] / \
                                            (df_avd.loc[:, 'number_of_visits'] - 1)
        return df_avd

    def num_locations(self):
        return number_of_locations(self.mobi_data_traj)

    def dist_to_home_median(self):
        coords = self.mobi_data.loc[:, ['uid', 'lng', 'lat']].copy()
        coords = coords.rename(columns={'lng': 'lng_1', 'lat': 'lat_1'})
        print('Merge data.')
        coords = pd.merge(coords, self.home.loc[:, ['uid', 'lng', 'lat']], on=['uid'])
        tqdm.pandas()
        coords.loc[:, 'dist2home'] = coords.progress_apply(lambda row: preprocess.haversine(row['lng'], row['lat'],
                                                                                            row['lng_1'], row['lat_1']),
                                                           axis=1)
        df_dist2home = coords.groupby('uid')['dist2home'].median().reset_index()
        return df_dist2home