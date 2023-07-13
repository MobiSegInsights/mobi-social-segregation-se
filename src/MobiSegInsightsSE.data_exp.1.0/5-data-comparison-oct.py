import sys
from pathlib import Path
import os
import pandas as pd
import utm
import time
from p_tqdm import p_map
import numpy as np


ROOT_dir = Path(__file__).parent.parent
sys.path.append(ROOT_dir)
sys.path.insert(0, os.path.join(ROOT_dir, 'lib'))


def one_day_processing(path=None, target_file=None):
    selectedcols = ['timestamp', 'device_aid', 'latitude', 'longitude', 'location_method']
    start = time.time()
    print("Data loading...")
    file_list = os.listdir(path)
    df_list = []
    for file in file_list:
        file_path = os.path.join(path, file)
        print(f'Loading {file_path}')
        df_list.append(pd.read_csv(file_path, sep='\t', compression='gzip', usecols=selectedcols))
    data = pd.concat(df_list)
    np.random.seed(68)
    data.loc[:, 'batch'] = np.random.randint(0, 16, size=len(data))

    def by_batch(data):
        data.loc[:, "utm_x"] = data.apply(lambda row: utm.from_latlon(row['latitude'], row['longitude'])[0],
                                          axis=1)
        data.loc[:, "utm_y"] = data.apply(lambda row: utm.from_latlon(row['latitude'], row['longitude'])[1],
                                          axis=1)

        return data
    # Process coordinates
    print('Process coordinates...')
    rstl = p_map(by_batch, [g for _, g in data.groupby('batch', group_keys=True)])
    data = pd.concat(rstl)
    end = time.time()
    print(f"Data processed in {(end - start)/60} minutes.")
    data.drop(columns=['batch']).\
        to_parquet(target_file)


if __name__ == '__main__':
    one_day_processing(path='D:\\MAD_dbs\\data_comparison\\pickwell',
                       target_file='D:\\MAD_dbs\\data_comparison\\pickwell.parquet')
    one_day_processing(path='D:\\MAD_dbs\\data_comparison\\predicio',
                       target_file='D:\\MAD_dbs\\data_comparison\\predicio.parquet')