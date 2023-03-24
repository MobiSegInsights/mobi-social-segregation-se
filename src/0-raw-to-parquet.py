import sys
import subprocess
import os
import pandas as pd
import utm
import sqlalchemy
import time
from p_tqdm import p_map
from tqdm import tqdm
import numpy as np


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
        self.converted_data_folder = 'D:\\MAD_dbs\\raw_data_se_2019\\format_parquet'
        self.month = month
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']
        self.data = None
        self.devices = None

    def device_grouping(self, num_groups=100):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}')
        devices = pd.read_sql('''SELECT uid FROM description.stops;''', con=engine)
        np.random.seed(68)
        devices.loc[:, 'batch'] = np.random.randint(0, num_groups, size=len(devices))
        self.devices = {x: devices.loc[devices.batch == x, 'uid'].to_list() for x in range(0, num_groups)}

    def process_data(self, selectedcols=None, day=None):
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
            print(f'Loading {file_path}')
            df_list.append(pd.read_csv(file_path, sep='\t', compression='gzip', usecols=selectedcols))
        self.data = pd.concat(df_list)
        np.random.seed(68)
        self.data.loc[:, 'batch'] = np.random.randint(0, 16, size=len(self.data))

        def by_batch(data):
            data.loc[:, "utm_x"] = data.apply(lambda row: utm.from_latlon(row['latitude'], row['longitude'])[0],
                                              axis=1)
            data.loc[:, "utm_y"] = data.apply(lambda row: utm.from_latlon(row['latitude'], row['longitude'])[1],
                                              axis=1)

            return data
        # Process coordinates
        print('Process coordinates...')
        rstl = p_map(by_batch, [g for _, g in self.data.groupby('batch', group_keys=True)])
        self.data = pd.concat(rstl)
        end = time.time()
        print(f"Data processed in {(end - start)/60} minutes.")

    def write_out(self, grp=None, day=None):
        dirs = [x[0] for x in os.walk(self.converted_data_folder)]
        target_dir = os.path.join(self.converted_data_folder, 'grp_' + str(grp))
        if target_dir not in dirs:
            os.makedirs(target_dir)
            print("created folder : ", target_dir)

        self.data.drop(columns=['batch']).loc[self.data.device_aid.isin(self.devices[grp]), :]. \
            to_parquet(os.path.join(target_dir, self.month + '_' + day + '.parquet'))

    def dump_to_parquet(self, day=None):
        # Save data to database
        start = time.time()
        for grp in tqdm(range(0, len(self.devices)), desc='Saving data'):
            self.write_out(grp=grp, day=day)
        end = time.time()
        print(f"Data saved in {(end - start)/60} minutes.")


def get_day_list(month=None):
    days_num = {'06': 30, '07': 31, '08': 31, '09': 30, '10': 31, '11': 30, '12': 31}
    days = ["%02d" % (number,) for number in range(1, days_num[month] + 1)]
    return days


if __name__ == '__main__':
    print('Processing .csv.gz into database by day:')
    days_num = {'06': 30, '07': 31, '08': 31, '09': 30, '10': 31, '11': 30, '12': 31}
    cols = ['timestamp', 'device_aid', 'latitude', 'longitude', 'location_method']
    for m in ('06', '07', '08', '09', '10', '11', '12'):
        print(f'Processing month {m}:')
        start = time.time()
        days_list = get_day_list(month=m)
        data_prep = DataPrep(month=m)
        data_prep.device_grouping(num_groups=100)
        for day in days_list:
            data_prep.process_data(selectedcols=cols, day=day)
            data_prep.dump_to_parquet(day=day)
        end = time.time()
        time_elapsed = (end - start)//60 #  in minutes
        print(f"Month {m} processed in {time_elapsed} minutes.")
