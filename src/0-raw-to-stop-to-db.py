import sys
import subprocess
import os
import pandas as pd
import geopandas as gpd
import skmob
from skmob.preprocessing import filtering
from skmob.preprocessing import detection
import sqlalchemy
import time
import multiprocessing as mp
from tqdm import tqdm


def get_repo_root():
    """Get the root directory of the repo."""
    dir_in_repo = os.path.dirname(os.path.abspath('__file__'))
    return subprocess.check_output('git rev-parse --show-toplevel'.split(),
                                   cwd=dir_in_repo,
                                   universal_newlines=True).rstrip()


ROOT_dir = get_repo_root()
sys.path.append(ROOT_dir)
sys.path.insert(0, ROOT_dir + '/lib')

from lib import preprocess as preprocess


class DataPrep:
    def __init__(self, month=None):
        """
        :param month: 06, 07, 08, 12
        :type month: str
        :return: None
        :rtype: None
        """
        self.raw_data_folder = 'D:\\MAD_dbs\\raw_data_se_2019'  # under the local drive D
        self.month = month
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']
        self.data = None

    def stop_detection(self, df, id_tuple):
        try:
            tdf = skmob.TrajDataFrame(df.loc[df.device_aid.isin(id_tuple), :], user_id='device_aid', datetime='TimeUTC',
                                      latitude='latitude', longitude='longitude')
            stdf = detection.stops(filtering.filter(tdf, max_speed_kmh=500.),
                                   stop_radius_factor=0.5, no_data_for_minutes=60,
                                   minutes_for_a_stop=10.0, min_speed_kmh=3,
                                   spatial_radius_km=0.1, leaving_time=True)
            return stdf
        except:
            return None

    def stop_detection_batch(self, chunk):
        stop_list = []
        for id_tuple in tqdm(chunk):
            stop_list.append(self.stop_detection(self.data, id_tuple))
        stops = pd.concat(stop_list)
        return stops

    def load_data(self, selectedcols=None, day=None):
        """
        :param selectedcols: a list of column names
        :type selectedcols: list
        :return: None
        :rtype: None
        """
        start = time.time()
        print("Data loading...")
        path = os.path.join(self.raw_data_folder, self.month, day)
        file_list = os.listdir(path)
        df_list = []
        for file in file_list:
            file_path = os.path.join(path, file)
            print(f'Processing {file_path}')
            df_list.append(preprocess.raw_time_processing(filepath=file_path, selectedcols=selectedcols))
        self.data = pd.concat(df_list)
        end = time.time()
        print(f"Number of rows for {self.month}.{day}: {len(self.data)} loaded in {end - start} seconds.")

    def stops_day(self):
        # Define batches of jobs
        df_id = pd.DataFrame(self.data.device_aid.unique(), columns=['device_aid'])
        id_batches = preprocess.df_col2batches(df_id, column_name='device_aid', chunk_size=100)
        id_batches_chunks = []
        num_thread = 10
        num_chunks = num_thread  # number of CPUs to use : mp.cpu_count() - 1
        chunk_size = int(len(id_batches) / num_chunks) + (len(id_batches) // num_chunks > 0)
        for i in range(num_chunks):
            id_batches_chunk = id_batches[i * chunk_size:(i + 1) * chunk_size]
            if len(id_batches_chunk) > 0:
                id_batches_chunks.append(id_batches_chunk)

        # Start parallel processing
        print('Start parallel processing...')
        pool = mp.Pool(num_thread)  # mp.cpu_count() - 1
        df_list = pool.starmap(self.stop_detection_batch,
                               [(element,) for element in id_batches_chunks])
        pool.close()
        stdf = pd.concat(df_list)
        return pd.DataFrame(stdf)

    def dump_monthly_stops(self, selectedcols=None):
        tb_name = 'stops'
        engine = sqlalchemy.create_engine(f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
        days_num = {'06': 30, '07': 31, '08': 31, '09': 30, '10': 31, '11': 30, '12': 31}
        if self.month != '10':
            days = ["%02d" % (number,) for number in range(1, days_num[self.month] + 1)]
        else:
            days = ["%02d" % (number,) for number in range(1, days_num[self.month] + 1) if number > 8]
        for day in days:
            self.load_data(selectedcols=selectedcols, day=day)
            # Stop detection for one day
            print("Stop detection started...")
            start = time.time()
            stdf = self.stops_day()
            end = time.time()
            print(stdf.head())
            print(f"Stop detection (# {len(stdf)}) finished in {end - start} seconds.")

            # Get local time
            start = time.time()
            print("Local time computation started...")
            stdf[['tzname', 'TimeLocal', 'leaving_TimeLocal']] = stdf.apply(lambda row: preprocess.convert_to_location_tz(row), axis=1,
                                                                            result_type='expand')
            end = time.time()
            print(f"Local time computation finished in {end - start} seconds.")

            # Save data to database
            start = time.time()
            print("Saving data...")
            stdf.to_sql(tb_name, engine, schema='public', index=False, if_exists='append',
                        method='multi', chunksize=5000)
            end = time.time()
            print(f"Data saved in {end - start} seconds.")


if __name__ == '__main__':
    flag = 1
    # 1. Load data from raw files, detect stops, and store in dbs/
    if flag == 1:
        cols = ['timestamp', 'device_aid', 'latitude', 'longitude', 'location_method']
        for m in ('06', '07', '08', '09', '10', '11', '12'):
            print(f'Processing month {m}:')
            start = time.time()
            data_prep = DataPrep(month=m)
            data_prep.dump_monthly_stops(selectedcols=cols)
            end = time.time()
            time_elapsed = (end - start)//60 #  in minutes
            print(f"Month {m} processed in {time_elapsed} minutes.")
    if flag == 2:
        user = preprocess.keys_manager['database']['user']
        password = preprocess.keys_manager['database']['password']
        port = preprocess.keys_manager['database']['port']
        db_name = preprocess.keys_manager['database']['name']
        # 2. Inject zones
        print("Loading zones...")
        gdf_zones = gpd.GeoDataFrame.from_file(os.path.join(ROOT_dir, 'dbs', 'DeSO', 'DeSO_2018_v2.shp'))
        preprocess.dump2db_gdf(gdf_zones, 'POLYGON', 3006,
                               user, password, port, db_name, table_name='zones', schema_name='public')
        print("...done.")
