import os
import subprocess
import yaml
import sqlalchemy
import pandas as pd
import numpy as np
import geopandas as gpd
import weighted
import skmob
from skmob.measures.individual import radius_of_gyration, distance_straight_line, number_of_locations, number_of_visits
from tqdm import tqdm
from p_tqdm import p_map
import multiprocessing


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

    def load_mobi_data(self, test=False):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
        print("Loading mobility data.")
        self.mobi_data = pd.read_sql_query(sql="""SELECT uid, date, month, "TimeLocal", dur,
        lat, lng, cluster FROM stops_subset;""", con=engine)
        if test:
            self.mobi_data = self.mobi_data.head(10000)
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


class MobilitySegregationPlace(MobilityMeasuresIndividual):
    def __init__(self):
        super().__init__()
        self.hexagons = None
        self.mobi_metrics = None

    def load_hexagons_mobi_metrics(self):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
        print('Loading hexagons...')
        self.hexagons = gpd.GeoDataFrame.from_postgis(sql="""SELECT hex_id, geom FROM hexagons;""", con=engine)
        print(f"Number of hexagons: {len(self.hexagons)}")
        print('Loading individual mobility metrics and segregation measuring by housing...')
        self.mobi_metrics = pd.read_sql(sql='''SELECT * FROM segregation.indi_mobi_resi_seg_metrics;''', con=engine)

    def mobi_data_processing(self):
        # Add time-related columns (h_s, dur, holiday). weekday
        print('Mobility data processing: add time-related columns (h_s, dur, holiday).')
        self.mobi_data = preprocess.mobi_data_time_enrich(self.mobi_data)

        # Add temporal weight column to visits (wt)
        print('Mobility data processing: add temporal weight column to visits (wt).')
        self.mobi_data = preprocess.record_weights(self.mobi_data)

        # Add individual weight (wt_p)
        print('Mobility data processing: add individual weight (wt_p).')
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
        df_wt = pd.read_sql(sql="""SELECT uid, wt FROM segregation.indi_mobi_resi_seg_metrics;""", con=engine)
        df_wt = df_wt.rename(columns={'wt': 'wt_p'})
        self.mobi_data = pd.merge(self.mobi_data, df_wt, on=['uid'], how='left')

        # Add total weight
        print('Mobility data processing: add total weight (wt_total).')
        self.mobi_data.loc[:, 'wt_total'] = self.mobi_data.loc[:, 'wt'] * self.mobi_data.loc[:, 'wt_p']

    def add_spatio_unit(self):
        print('Converting mobility data into Points...')
        gdf = preprocess.df2gdf_point(self.mobi_data.loc[:, ['lng', 'lat']].drop_duplicates(subset=['lng', 'lat']),
                                      'lng', 'lat', crs=4326, drop=False)
        # Hexagonal level
        print('Finding hexagons...')
        gdf_hex = gpd.sjoin(gdf, self.hexagons)
        self.mobi_data = pd.merge(self.mobi_data, gdf_hex.loc[:, ['lng', 'lat', 'hex_id']],
                                  on=['lng', 'lat'], how='left')

    def add_temporal_unit(self, num_groups=48):
        # Temporal unit
        # Create bins and add sequence to bins
        print('Create bins and add sequence to bins.')
        df = pd.DataFrame({'time': [x / (num_groups/24) for x in range(0, num_groups + 1)]})
        bins = [x / (num_groups/24) for x in range(0, num_groups + 1)]
        df['time_bin'] = pd.cut(df['time'], bins, right=True, include_lowest=True)
        df = df.iloc[1:]
        df.loc[:, 'time_seq'] = range(1, len(df) + 1)
        df = df.drop(columns=['time'])
        time_bins = dict(zip(df.time_bin, df.time_seq))

        # Binning time in hours into groups
        print('Binning time in hours into groups (time_bin)...')
        def time_span(row):
            span = pd.cut([row['h_s'], min(row['h_s'] + row['dur'] / 60, 24)], bins, right=True, include_lowest=True)
            time_seq_list = [time_bins[ele] for ele in span]
            return list(range(time_seq_list[0], time_seq_list[1] + 1))

        self.mobi_data.loc[:, 'gp'] = np.random.randint(multiprocessing.cpu_count(),
                                                        size=len(self.mobi_data))

        def parallel_func(df):
            df.loc[:, 'time_seq'] = df.apply(lambda row: time_span(row), axis=1)
            df = df.explode('time_seq')
            return df

        restl = p_map(parallel_func, [g for _, g in self.mobi_data.groupby('gp', group_keys=True)])
        self.mobi_data = pd.concat(restl)
        self.mobi_data = self.mobi_data.drop(columns=['gp'])

    def aggregating_metrics(self, test=False):
        def unit_weighted_median(data):
            hex_id_ = data.hex_id.values[0]
            #weekday_ = data['weekday'].values[0]
            #holiday_ = data.holiday.values[0]
            #time_seq_ = data.time_seq.values[0]
            # Visiting strength measure
            num_visits, num_visits_wt = len(data), data.wt_total.sum()
            num_unique_uid, num_pop = data.uid.nunique(), data.wt_p.sum()
            metrics_dict = dict(hex_id=hex_id_,
                                num_visits=num_visits,
                                num_visits_wt=num_visits_wt,
                                num_unique_uid=num_unique_uid,
                                num_pop=num_pop)
            # Mobility patterns and segregation measures
            df_indi_metrics = self.mobi_metrics.loc[self.mobi_metrics.uid.isin(data.uid.unique()), :]
            data_ = pd.merge(data, df_indi_metrics, on='uid', how='left')
            cols = ['number_of_locations', 'number_of_visits',
                    'average_displacement', 'radius_of_gyration',
                    'median_distance_from_home', 'S_income', 'iso_income',
                    'S_birth_region', 'iso_birth_region', 'S_background', 'iso_background',
                    'Foreign background', 'Not Sweden', 'Lowest income group']
            for v in cols:
                metrics_dict[v] = weighted.median(data_[v], data_['wt_total'])
            return pd.Series(metrics_dict)
        print('Calculate metrics of each spatiotemporal unit')

        def by_hexagon(data):
            df = data.groupby(['weekday', 'holiday', 'time_seq']).apply(unit_weighted_median).reset_index()
            return df
        if not test:
            restl = p_map(by_hexagon, [g for _, g in self.mobi_data.groupby('hex_id', group_keys=True)])
        else:
            restl = p_map(by_hexagon, [g for _, g in self.mobi_data.sample(100).groupby('hex_id', group_keys=True)])
        df_agg = pd.DataFrame(restl)
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
        print("Saving mobility-aware data...")
        df_agg.to_sql('mobi_seg_hexagons', engine, schema='segregation', index=False,
                      method='multi', if_exists='replace', chunksize=10000)
