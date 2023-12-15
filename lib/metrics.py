import os
from pathlib import Path
import yaml
import sqlalchemy
import pandas as pd
import numpy as np
import geopandas as gpd
import skmob
from skmob.measures.individual import radius_of_gyration, distance_straight_line, number_of_locations, number_of_visits
from tqdm import tqdm
from p_tqdm import p_map
import scipy.stats as stats
import multiprocessing
from statsmodels.stats.weightstats import DescrStatsW
from lib import preprocess as preprocess


ROOT_dir = Path(__file__).parent.parent
with open(os.path.join(ROOT_dir, 'dbs', 'keys.yaml')) as f:
    keys_manager = yaml.load(f, Loader=yaml.FullLoader)


def delta_ice(ice_r, ice_e):
    if ice_r < 0:
        return -(ice_e - ice_r)
    return ice_e - ice_r


def ice_group(ice, threshold=0):
    statistic, p_value = stats.shapiro(ice)
    if p_value > 0.05:
        t_statistic, t_p_value = stats.ttest_1samp(ice, threshold, alternative='greater')
        if t_p_value < 0.05:
            return 'D'
        else:
            t_statistic, t_p_value = stats.ttest_1samp(ice, -threshold, alternative='less')
            if t_p_value < 0.05:
                return 'F'
            else:
                return 'N'
    else:
        t_statistic, t_p_value = stats.wilcoxon(ice-threshold, alternative='greater')
        if t_p_value < 0.05:
            return 'D'
        else:
            t_statistic, t_p_value = stats.wilcoxon(ice+threshold, alternative='less')
            if t_p_value < 0.05:
                return 'F'
            else:
                return 'N'


class MobilityMeasuresIndividual:
    def __init__(self):
        self.home = None
        self.mobi_data = None
        # self.resi_seg = None
        # self.zone_stats = None
        self.mobi_data_traj = None
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']

    def load_home_seg_uid(self):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        print("Loading home and segregation data.")
        self.home = pd.read_sql_query(sql="""SELECT uid, zone, deso, wt_p, lng, lat FROM home_p;""", con=engine)
        # self.resi_seg = pd.read_sql_query(sql="""SELECT region, var, evenness, iso FROM resi_seg_deso;""", con=engine)
        # self.zone_stats = pd.read_sql_query(sql="""SELECT * FROM zone_stats;""", con=engine)

    def load_mobi_data(self, test=False, traj_format=True):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        print("Loading mobility data.")
        if test:
            self.mobi_data = pd.read_sql_query(sql="""SELECT uid, "localtime", dur, lat, lng, 
                                                      loc, h_s, holiday_s, weekday_s FROM stops_p
                                                      WHERE dur < 720
                                                      LIMIT 10000;""",
                                               con=engine)
        else:
            self.mobi_data = pd.read_sql_query(sql="""SELECT uid, "localtime", dur, lat, lng, 
                                                      loc, h_s, holiday_s, weekday_s FROM stops_p 
                                                      WHERE dur < 720;""",
                                               con=engine)
        self.mobi_data = self.mobi_data.rename(columns={'holiday_s': 'holiday',
                                                        'weekday_s': 'weekday'})
        df_uids = pd.read_sql_query(
            sql="""SELECT uid, num_loc FROM description.stops_p WHERE num_days > 7;""", con=engine)
        df_uids = df_uids.loc[df_uids.num_loc > 2, :]
        self.mobi_data = self.mobi_data.loc[self.mobi_data.uid.isin(df_uids.uid), :]
        self.mobi_data = self.mobi_data.loc[self.mobi_data.uid.isin(self.home.uid), :]
        num_uids, num_stays = self.mobi_data['uid'].nunique(), len(self.mobi_data)
        print(f"Apply {num_stays} stays from {num_uids} devices.")

        if traj_format:
            print("Converting it to scikit-learn format.")
            self.mobi_data_traj = skmob.TrajDataFrame(self.mobi_data,
                                                      latitude='lat', longitude='lng',
                                                      datetime='localtime',
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
        self.zones = None
        self.mobi_metrics = None

    def load_deso_zones(self):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        print('Loading DeSO zones...')
        self.zones = gpd.GeoDataFrame.from_postgis(sql="""SELECT deso, geom FROM zones;""", con=engine)
        self.zones = self.zones.to_crs(4326)
        print(f"Number of DeSO zones: {len(self.zones)}")

    def mobi_data_weight_processing(self):
        # Add temporal weight column to visits (wt)
        print('Mobility data processing: add temporal weight column to visits (wt).')
        self.mobi_data = preprocess.record_weights(self.mobi_data)

        # Add individual weight (wt_p)
        print('Mobility data processing: add individual weight (wt_p).')
        self.mobi_data = pd.merge(self.mobi_data, self.home[['uid', 'wt_p']], on=['uid'], how='left')

        # Add total weight
        print('Mobility data processing: add total weight (wt_total).')
        self.mobi_data.loc[:, 'wt_total'] = self.mobi_data.loc[:, 'wt'] * self.mobi_data.loc[:, 'wt_p']

    def add_spatio_unit(self):
        print('Converting mobility data into Points...')
        gdf = preprocess.df2gdf_point(self.mobi_data.loc[:, ['lng', 'lat']].drop_duplicates(subset=['lng', 'lat']),
                                      'lng', 'lat', crs=4326, drop=False)
        # DeSO level
        print('Finding DeSO zones...')
        gdf_zones = gpd.sjoin(gdf, self.zones)
        self.mobi_data = pd.merge(self.mobi_data, gdf_zones.loc[:, ['lng', 'lat', 'deso']],
                                  on=['lng', 'lat'], how='left')

    def add_temporal_unit(self, num_groups=48, save=False):
        # Temporal unit
        # This function requires the covered stays that last less than 12 hours
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
            seq = list(range(time_seq_list[0], time_seq_list[1] + 1))
            if row['h_s'] + row['dur'] / 60 > 24:
                span2 = pd.cut([0, row['h_s'] + row['dur'] / 60 - 24], bins, right=True, include_lowest=True)
                time_seq_list2 = [time_bins[ele] for ele in span2]
                seq2 = list(range(time_seq_list2[0], time_seq_list2[1] + 1))
                seq = seq2 + seq
            return seq

        def parallel_func(df):
            df.loc[:, 'time_seq'] = df.apply(lambda row: time_span(row), axis=1)
            df = df.explode('time_seq')
            return df

        def time_span_compact(row):
            span = pd.cut([row['h_s'], min(row['h_s'] + row['dur'] / 60, 24)], bins, right=True, include_lowest=True)
            time_seq_list = [time_bins[ele] for ele in span]
            if row['h_s'] + row['dur'] / 60 > 24:
                span2 = pd.cut([0, row['h_s'] + row['dur'] / 60 - 24], bins, right=True, include_lowest=True)
                time_seq_list2 = [time_bins[ele] for ele in span2]
                time_seq_list = time_seq_list2 + time_seq_list
            return time_seq_list

        def parallel_func_compact(df):
            df.loc[:, 'time_span'] = df.apply(lambda row: time_span_compact(row), axis=1)
            return df

        self.mobi_data.loc[:, 'gp'] = np.random.randint(multiprocessing.cpu_count(),
                                                        size=len(self.mobi_data))
        restl = p_map(parallel_func_compact, [g for _, g in self.mobi_data.groupby('gp', group_keys=True)])
        self.mobi_data = pd.concat(restl)
        self.mobi_data = self.mobi_data.drop(columns=['gp'])

        if save:
            self.mobi_data = self.mobi_data.loc[:, ['uid', 'lat', 'lng', 'holiday', 'weekday', 'wt_total',
                                                    'deso', 'time_span']]
            print('Save the data...')
            engine = sqlalchemy.create_engine(
                f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
            self.mobi_data.to_sql('mobi_seg_deso_raw', engine, schema='segregation', index=False,
                      method='multi', if_exists='append', chunksize=10000)


class AccessVSSegregation:
    def __init__(self):
        self.data = None
        self.pop = None
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']

    def load_data_and_process(self):
        self.data = pd.read_parquet(os.path.join(ROOT_dir, 'results/data4model_individual.parquet'))
        self.data = self.data.loc[(self.data['weekday'] == 1) & (self.data['holiday'] == 0), :]
        self.pop = self.data.wt_p.sum()
        # Keep relevant columns for analysis
        cols = ['uid', 'region', 'wt_p',
                'car_ownership', 'radius_of_gyration', 'median_distance_from_home',
                'cum_jobs_pt', 'cum_jobs_car',
                'ice_birth_resi', 'ice_birth']
        self.data = self.data[cols].rename(columns={'ice_birth_resi': 'ice_r',
                                                    'ice_birth': 'ice_e'})

        # Add region county code and land-use type
        self.data.loc[:, 'deso_2'] = self.data['region'].apply(lambda x: x[0:2])
        self.data.loc[:, 'region_cat'] = self.data['region']. \
            apply(lambda x: 'Rural/Suburban' if x[4] in ('A', 'B') else 'Urban')

        # Delta ice - segregation disparity
        self.data.loc[:, 'delta_ice'] = self.data.apply(lambda row: delta_ice(row['ice_r'], row['ice_e']), axis=1)
        self.data.loc[:, 'seg_change'] = self.data['delta_ice'].apply(lambda x: 'inc' if x > 0 else 'dec')

        # Control for groups
        self.data.loc[:, 'car_op_cat'] = pd.cut(self.data['car_ownership'],
                                                bins=[0.01, 0.35, 0.53, 1.72],
                                                labels=['L', 'M', 'H'])
        self.data.loc[:, 'ice_r_grp'] = pd.cut(self.data.ice_r,
                                               bins=[-1, -0.2, 0.2, 1],
                                               labels=['F', 'N', 'D'])

    def add_access_groups(self, num_grps=None):
        self.data.loc[:, 'access_grp_car'] = pd.qcut(self.data['cum_jobs_car'], num_grps)
        self.data.loc[:, 'access_grp_pt'] = pd.qcut(self.data['cum_jobs_pt'], num_grps)

        def car_grp_wm(data):
            return pd.Series({'access_car': np.average(data['cum_jobs_car'], weights=data['wt_p'])})

        def pt_grp_wm(data):
            return pd.Series({'access_pt': np.average(data['cum_jobs_pt'], weights=data['wt_p'])})

        df_car = self.data.groupby('access_grp_car').apply(car_grp_wm).reset_index()
        df_pt = self.data.groupby('access_grp_pt').apply(pt_grp_wm).reset_index()
        df2 = pd.merge(self.data, df_car, on='access_grp_car')
        df2 = pd.merge(df2, df_pt, on='access_grp_pt')
        self.data = df2.drop(columns=['access_grp_car', 'access_grp_pt']).copy()

    def grp_stats_com(self, data=None, var=None):
        stat_dict = {'share': data.wt_p.sum() / self.pop * 100}
        wdf = DescrStatsW(data[var], weights=data['wt_p'], ddof=1)
        sts = wdf.quantile([0.25, 0.50, 0.75])
        q25 = sts.values[0]
        q50 = sts.values[1]
        q75 = sts.values[2]
        stat_dict['mean'] = wdf.mean
        stat_dict['q25'] = q25
        stat_dict['q50'] = q50
        stat_dict['q75'] = q75
        stat_dict['var'] = var
        return pd.Series(stat_dict)

    def multi_var_mode_access(self,
                              df=None,
                              grp_by_set=['ice_r_grp', 'region_cat'],
                              var_set=None):
        list_df = []
        for var in var_set:
            res = df.groupby(grp_by_set + ['access_car']). \
                apply(lambda data: self.grp_stats_com(data, var=var)). \
                reset_index().rename(columns={'access_car': 'access'})
            res.loc[:, 'mode'] = 'Car'
            list_df.append(res)

            res = df.groupby(grp_by_set + ['access_pt']). \
                apply(lambda data: self.grp_stats_com(data, var=var)). \
                reset_index().rename(columns={'access_pt': 'access'})
            res.loc[:, 'mode'] = 'Transit'
            list_df.append(res)
        return pd.concat(list_df)
