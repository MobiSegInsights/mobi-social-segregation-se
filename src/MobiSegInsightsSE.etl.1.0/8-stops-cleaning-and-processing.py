import sys
import subprocess
import os
import pandas as pd
from tqdm import tqdm
from datetime import datetime
import time
from p_tqdm import p_map
import numpy as np
import sqlalchemy
import multiprocessing


def get_repo_root():
    """Get the root directory of the repo."""
    dir_in_repo = os.path.dirname(os.path.abspath('__file__'))
    return subprocess.check_output('git rev-parse --show-toplevel'.split(),
                                   cwd=dir_in_repo,
                                   universal_newlines=True).rstrip()


ROOT_dir = get_repo_root()
sys.path.append(ROOT_dir)
sys.path.insert(0, ROOT_dir + '/lib')
import preprocess

se_box = (11.0273686052, 55.3617373725, 23.9033785336, 69.1062472602)

def within_sweden_time(latitude, longitude):
    if (latitude >= se_box[1]) & (latitude <= se_box[3]):
        if (longitude >= se_box[0]) & (longitude <= se_box[2]):
            return 1
    return 0


class DataCleaning:
    def __init__(self):
        self.data = None
        self.abnormal_stays = [(62.0, 15.0), (59.3333, 18.05), (59.3247, 18.056)]
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']

    def load_and_remove_abnormal(self, test=False):
        print("Load data...")
        engine = sqlalchemy.create_engine(f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
        if test:
            self.data = pd.read_sql(sql="""SELECT device_aid, loc, "start", "end", 
                                           latitude, longitude FROM stops_r LIMIT 100000""",
                                    con=engine)
        else:
            self.data = pd.read_sql(sql="""SELECT device_aid, loc, "start", "end", 
                                           latitude, longitude FROM stops_r""",
                                    con=engine)
        L_before = len(self.data)
        print("Remove abnormal stays...")
        tuples_in_df = pd.MultiIndex.from_frame(self.data[['latitude', 'longitude']])
        self.data = self.data[~tuples_in_df.isin(self.abnormal_stays)]
        L_after = len(self.data)
        print("Share of data remained after removing abnormal stays: %.2f %%" % (L_after / L_before * 100))

    def rename_columns(self):
        self.data = self.data.rename(columns={'device_aid': 'uid',
                                              'latitude': 'lat',
                                              'longitude': 'lng',
                                              'start': 'datetime',
                                              'end': 'leaving_datetime'})

    def time_processing(self):
        self.data.loc[:, 'timestamp'] = self.data['datetime']
        self.data.loc[:, 'dur'] = (self.data['leaving_datetime'] - self.data['datetime']) / 60  # minute
        tqdm.pandas()
        self.data.loc[:, 'datetime'] = self.data['datetime'].progress_apply(lambda x: datetime.fromtimestamp(x))
        self.data.loc[:, 'leaving_datetime'] = self.data['leaving_datetime'].progress_apply(lambda x: datetime.fromtimestamp(x))
        self.data.loc[:, 'se_time'] = self.data.progress_apply(lambda row: within_sweden_time(row['lat'], row['lng']), axis=1)
        print("Share of data in SE time: %.2f %%" % (self.data.loc[:, 'se_time'].sum() / len(self.data) * 100))

    def time_zone_parallel(self):
        df_sub = self.data.loc[self.data.se_time == 0, :].copy()
        df_se = self.data.loc[self.data.se_time == 1, :].copy()
        df_se.loc[:, 'tzname'] = 'Europe/Stockholm'

        def find_time_zone(data):
            data.loc[:, 'tzname'] = data.apply(lambda row: preprocess.get_timezone(row['lng'], row['lat']), axis=1)
            return data

        df_sub.loc[:, 'batch'] = np.random.randint(1, 101, df_sub.shape[0])
        rstl = p_map(find_time_zone, [g for _, g in df_sub.groupby('batch', group_keys=True)])
        df_sub = pd.concat(rstl)
        L_before = len(df_sub)
        df_sub = df_sub[df_sub.tzname.notna()]
        L_after = len(df_sub)
        print("Share of data remained after removing unknown timezone: %.2f %%" % (L_after / L_before * 100))
        self.data = pd.concat([df_se, df_sub.drop(columns=['batch'])])
        self.data = self.data.drop(columns=['se_time'])

    def convert_to_local_time(self):
        def zone_grp(k, data):
            data.loc[:, "localtime"] = data['datetime'].dt.tz_localize('UTC').dt.tz_convert(k)
            data.loc[:, "leaving_localtime"] = data['leaving_datetime'].dt.tz_localize('UTC').dt.tz_convert(k)
            return data
        mk = int(len(self.data)/2)
        part1 = self.data.iloc[:mk, :]
        part2 = self.data.iloc[mk:, :]
        print('Convert to local time: part 1.')
        rstl1 = p_map(zone_grp,
                     [k for k, _ in part1.groupby('tzname', group_keys=True)],
                     [g for _, g in part1.groupby('tzname', group_keys=True)])
        print('Convert to local time: part 2.')
        rstl2 = p_map(zone_grp,
                     [k for k, _ in part2.groupby('tzname', group_keys=True)],
                     [g for _, g in part2.groupby('tzname', group_keys=True)])
        self.data = pd.concat(rstl1 + rstl2)
        print(self.data.iloc[0])

    def mobi_data_time_enrich(self):
        """
        This function add a few useful columns based on dataframe's local time.
        :type data: dataframe
        :return: A dataframe with hour of the time, holiday label
        """
        # Add start time hour and duration in minute
        self.data.loc[:, 'h_s'] = self.data.loc[:, 'localtime'].apply(lambda x: x.hour + x.minute / 60)
        # Mark holiday season boundaries
        summer_start = datetime.strptime("2019-06-23 00:00:00+04:00", "%Y-%m-%d %H:%M:%S%z")
        summer_end = datetime.strptime("2019-08-11 00:00:00+04:00", "%Y-%m-%d %H:%M:%S%z")
        christmas_start = datetime.strptime("2019-12-22 00:00:00+04:00", "%Y-%m-%d %H:%M:%S%z")

        def holiday(x, s1, s2, s3):
            if (s1 < x < s2) | (x > s3):
                return 1
            else:
                return 0

        self.data.loc[:, 'gp'] = np.random.randint(multiprocessing.cpu_count(), size=len(self.data))

        def time_enrichment_parallel(df):
            # Add holiday season label
            df.loc[:, 'holiday_s'] = df.loc[:, 'localtime'].apply(
                lambda x: holiday(x, summer_start, summer_end, christmas_start))
            df.loc[:, 'holiday_e'] = df.loc[:, 'leaving_localtime'].apply(
                lambda x: holiday(x, summer_start, summer_end, christmas_start))
            # Add weekend/weekday label
            df.loc[:, 'weekday_s'] = df.loc[:, 'localtime'].apply(lambda x: 0 if x.weekday() in [5, 6] else 1)
            df.loc[:, 'weekday_e'] = df.loc[:, 'leaving_localtime'].apply(lambda x: 0 if x.weekday() in [5, 6] else 1)
            return df

        reslt = p_map(time_enrichment_parallel, [g for _, g in self.data.groupby('gp', group_keys=True)])
        self.data = pd.concat(reslt)
        self.data = self.data.drop(columns=['gp'])

        # Add individual sequence index
        self.data = self.data.sort_values(by=['uid', 'timestamp'], ascending=True)

        def indi_seq(df):
            df.loc[:, 'seq'] = range(1, len(df) + 1)
            return df

        reslt = p_map(indi_seq, [g for _, g in self.data.groupby('uid', group_keys=True)])
        self.data = pd.concat(reslt)


if __name__ == '__main__':
    start = time.time()
    dc = DataCleaning()
    dc.load_and_remove_abnormal(test=False)
    dc.rename_columns()
    dc.time_processing()
    dc.time_zone_parallel()
    dc.convert_to_local_time()
    dc.mobi_data_time_enrich()
    print('Writing data to database...')
    engine = sqlalchemy.create_engine(f'postgresql://{dc.user}:{dc.password}@localhost:{dc.port}/{dc.db_name}')
    dc.data.to_sql('stops_p', engine, schema='public', index=False, if_exists='append',
                   method='multi', chunksize=10000)
    time_elapsed = (time.time() - start) / 60
    print('Time cost: %.2f minutes.'%time_elapsed)
