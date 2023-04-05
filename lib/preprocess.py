import pandas as pd
import geopandas as gpd
from geoalchemy2 import Geometry, WKTElement
import os
import subprocess
import numpy as np
import osmnx as ox
import yaml
import sqlalchemy
import time
from tqdm import tqdm
from geopandas import GeoDataFrame
from shapely.geometry import Point
from math import radians, cos, sin, asin, sqrt
from timezonefinder import TimezoneFinder
from datetime import datetime
from p_tqdm import p_map
import multiprocessing
from infostop import Infostop
# Set up infostop parameters
R1, R2, MIN_STAY, MAX_TIME_BETWEEN = 30, 30, 15, 12  # meters, meters, minutes, hours

def get_repo_root():
    """Get the root directory of the repo."""
    dir_in_repo = os.path.dirname(os.path.abspath('__file__'))
    return subprocess.check_output('git rev-parse --show-toplevel'.split(),
                                   cwd=dir_in_repo,
                                   universal_newlines=True).rstrip()


ROOT_dir = get_repo_root()
with open(os.path.join(ROOT_dir, 'dbs', 'keys.yaml')) as f:
    keys_manager = yaml.load(f, Loader=yaml.FullLoader)


def infostop_per_user(key, data):
    model = Infostop(
        r1=R1,
        r2=R2,
        label_singleton=True,
        min_staying_time=MIN_STAY * 60,
        max_time_between=MAX_TIME_BETWEEN * 60 * 60,
        min_size=2,
        min_spacial_resolution=0,
        distance_metric='haversine',
        weighted=False,
        weight_exponent=1,
        verbose=False, )
    x = data.loc[~(((data['latitude'] > 84) | (data['latitude'] < -80)) | (
                (data['longitude'] > 180) | (data['longitude'] < -180))), :]
    x = x.sort_values(by='timestamp').drop_duplicates(subset=['latitude', 'longitude', 'timestamp']).reset_index(
        drop=True)
    x = x.dropna()
    ##THE THING RECORDS A POINT EVERYTIME THE ACCELEROMETER REGISTER A CHANGE, SO ASSUME NO MOVE UP TO 12 hours
    x['t_seg'] = x['timestamp'].shift(-1)
    x.loc[x.index[-1], 't_seg'] = x.loc[x.index[-1], 'timestamp'] + 1
    x['n'] = x.apply(lambda x: range(int(x['timestamp']),
                                     min(int(x['t_seg']), x['timestamp'] + (MAX_TIME_BETWEEN * 60 * 60)),
                                     (MAX_TIME_BETWEEN * 60 * 60 - 1)), axis=1)
    x = x.explode('n')
    x['timestamp'] = x['n'].astype(float)
    x = x[['latitude', 'longitude', 'timestamp']].dropna()  # ,'timezone'

    try:
        labels = model.fit_predict(x[['latitude', 'longitude', 'timestamp']].values)
    except:
        return pd.DataFrame([], columns=['device_aid', 'timestamp', 'latitude', 'longitude', 'loc', 'stop_latitude',
                                         'stop_longitude', 'interval'])  # ,'timezone'

    label_medians = model.compute_label_medians()
    x['loc'] = labels
    x['same_loc'] = x['loc'] == x['loc'].shift()
    # x['same_timezone'] = x['timezone']==x['timezone'].shift()
    x['little_time'] = (x['timestamp'] - x['timestamp'].shift() < MAX_TIME_BETWEEN * 60 * 60)

    x['interval'] = (~(x['same_loc'] &
                       x['little_time'])).cumsum()  # & x['same_timezone']

    latitudes = {k: v[0] for k, v in label_medians.items()}
    longitudes = {k: v[1] for k, v in label_medians.items()}
    x['stop_latitude'] = x['loc'].map(latitudes)
    x['stop_longitude'] = x['loc'].map(longitudes)
    x['device_aid'] = key[0]

    # keep only stop locations
    x = x[x['loc'] > 0].copy()

    return x[['device_aid', 'timestamp', 'latitude', 'longitude', 'loc', 'stop_latitude', 'stop_longitude',
              'interval']]  # ,'timezone'


def convert_to_location_tz(row, _tf=TimezoneFinder()):
    # if lat/lon aren't specified, we just want the existing name (e.g. UTC)
    if (row.lat == 0) & (row.lng == 0):
        return row.datetime.tz_localize('UTC').tzname(), row.datetime, row.leaving_datetime
    # otherwise, try to find tz name
    tzname = _tf.timezone_at(lng=row.lng, lat=row.lat)
    if tzname: # return the name if it is not None
        return tzname, row.datetime.tz_localize('UTC').tz_convert(tzname),\
               row.leaving_datetime.tz_localize('UTC').tz_convert(tzname)
    return row.datetime.tz_localize('UTC').tzname(), row.datetime, row.leaving_datetime  # else return existing name


def get_timezone(longitude, latitude):
    if longitude is None or latitude is None:
        return None
    tzf = TimezoneFinder()
    try:
        timeZone = tzf.timezone_at(lng=longitude, lat=latitude)
    except:
        timeZone = None
    return timeZone


def raw2df2db(file, user, password, port, db_name, table_name, schema_name):
    """
    Read the compressed files and get the dataframe for further processing.
    :param file: a string that points to raw records, e.g., "VGR_raw_mobile_2019_10.csv.gz"
    :return:
    A dataframe with each row a request record.
    """
    raw_folder = os.path.join(ROOT_dir, "dbs")
    chunk_container = pd.read_csv(os.path.join(raw_folder, file + ".gz"), sep=',',
                                  header=0,
                                  compression='gzip',
                                  chunksize=2000000,
                                  error_bad_lines=False)
    chunk_list = []
    for chunk in chunk_container:
        chunk_list.append(chunk)
    df = pd.concat(chunk_list)
    print('Rows number', len(df))
    dump2db_df(df, user, password, port, db_name, table_name, schema_name)
    return df


def raw2chunk2db(file, user, password, port, db_name, table_name, schema_name, folder_under_db="original_input_data"):
    """
    Read the compressed files and get the chunk for dumping.
    :param file: a string that points to raw records, e.g., "VGR_raw_mobile_2019_10.csv.gz"
    :return:
    A dataframe with each row a request record.
    """
    engine = sqlalchemy.create_engine(f'postgresql://{user}:{password}@localhost:{port}/{db_name}')
    raw_folder = os.path.join(ROOT_dir, "dbs", folder_under_db)
    chunk_container = pd.read_csv(os.path.join(raw_folder, file + ".gz"), sep=',',
                                  header=0, iterator=True,
                                  compression='gzip',
                                  chunksize=2000000,
                                  error_bad_lines=False)
    start = time.time()
    for chunk in tqdm(chunk_container, desc='Dumping data to database by chunk'):
        df = chunk.rename(columns={c: c.replace(' ', '') for c in chunk.columns})
        df.to_sql(table_name, engine, schema=schema_name, index=False, if_exists='append', method='multi', chunksize=5000)
    end = time.time()
    print(end - start)
    return df


def osm_net_retrieve(bbox, network_type, folder='dbs\\geo', region=None):
    """
    Save two formats of network downloaded from OpenStreetMap (.graphml & .shp)
    :param folder: where to save the downloaded data
    :param bbox: bounding box for retrieving the network
    :param network_type: "walk" or "drive"
    :param osm_folder: where to save the network
    :return: None
    """
    north, south, east, west = bbox
    G = ox.graph_from_bbox(north, south, east, west, network_type=network_type)
    ox.save_graphml(G, filepath=os.path.join(ROOT_dir, folder, network_type + f'_network_{region}.graphml'))
    gdf = ox.graph_to_gdfs(G)
    edge = gdf[1]
    edge = edge.loc[:, ['geometry', 'highway', 'junction', 'length', 'maxspeed', 'name', 'oneway',
                        'osmid', 'u', 'v', 'width']]

    fields = ['highway', 'junction', 'length', 'maxspeed', 'name', 'oneway',
              'osmid', 'u', 'v', 'width']
    df_inter = pd.DataFrame()
    for f in fields:
        df_inter[f] = edge[f].astype(str)
    gdf_edge = gpd.GeoDataFrame(df_inter, geometry=edge["geometry"])
    gdf_edge.to_file(os.path.join(ROOT_dir, folder, network_type + f'_network_{region}.shp'))


def dump2db_df(df, user, password, port, db_name, table_name, schema_name):
    """
    Dump a pandas dataframe to a database: a fast solution.
    :param df: string, data to dump as a table
    :param user: string, user name of the target database
    :param password: string, user password of the target database
    :param port: string, port number of the target database
    :param db_name: string, database name
    :param table_name: string, table name to be created in database
    :param schema_name: string, existing schema to create the dataframe as a table
    :return: None
    """
    engine = sqlalchemy.create_engine(f'postgresql://{user}:{password}@localhost:{port}/{db_name}')
    # df.head(0).to_sql(table_name, engine, schema=schema_name, if_exists='replace', index=False)
    # conn = engine.raw_connection()
    # cur = conn.cursor()
    # output = io.StringIO()
    # df.to_csv(output, sep='\t', header=False, index=False)
    # output.seek(0)
    # cur.copy_from(output, "\"" + "\".\"".join([schema_name, table_name]) + "\"", null="")  # null values become ''
    # conn.commit()
    df.to_sql(table_name, engine, schema=schema_name, index=False,
              method='multi', if_exists='replace', chunksize=10000)


def dump2db_gdf(gdf, sdtype, crs, user, password, port, db_name, table_name, schema_name):
    """
    Dump a pandas dataframe to a database: a fast solution.
    :param gdf: string, data to dump as a table
    :param sdtype: string, 'POINT', 'POLYGON' etc
    :param crs: integer, crs number e.g., 4326
    :param crs: string, data to dump as a table
    :param user: string, user name of the target database
    :param password: string, user password of the target database
    :param port: string, port number of the target database
    :param db_name: string, database name
    :param table_name: string, table name to be created in database
    :param schema_name: string, existing schema to create the dataframe as a table
    :return: None
    """
    engine = sqlalchemy.create_engine(f'postgresql://{user}:{password}@localhost:{port}/{db_name}')
    stt = time.time()
    gdf['geom'] = gdf['geometry'].apply(lambda x: WKTElement(x.wkt, srid=crs))

    # drop the geometry column as it is now duplicative
    gdf.drop('geometry', 1, inplace=True)
    gdf.to_sql(
        schema=schema_name,
        name=table_name,
        con=engine,
        if_exists='replace',
        index=False,
        dtype={
            'geom': Geometry(geometry_type=sdtype, srid=crs),
        }
    )
    print('Data dumped: %g' % (time.time() - stt))


def df2gdf_point(df, x_field, y_field, crs=4326, drop=True):
    """
    Convert two columns of GPS coordinates into POINT geo dataframe
    :param drop: boolean, if true, x and y columns will be dropped
    :param df: dataframe, containing X and Y
    :param x_field: string, col name of X
    :param y_field: string, col name of Y
    :param crs: int, epsg code
    :return: a geo dataframe with geometry of POINT
    """
    geometry = [Point(xy) for xy in zip(df[x_field], df[y_field])]
    if drop:
        gdf = GeoDataFrame(df.drop(columns=[x_field, y_field]), geometry=geometry)
    else:
        gdf = GeoDataFrame(df, crs=crs, geometry=geometry)
    gdf.set_crs(epsg=crs, inplace=True)
    return gdf


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees) in km
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r


def haversine_vec(data):
    """
    Take array of zones' centroids to return the Haversine distance matrix
    :param data: 2d array e.g., list(zones.loc[:, ["Y", "X"]].values)
    :return: a matrix of distance
    """
    # Convert to radians
    data = np.deg2rad(data)

    # Extract col-1 and 2 as latitudes and longitudes
    lat = data[:, 0]
    lng = data[:, 1]

    # Elementwise differentiations for latitudes & longitudes
    diff_lat = lat[:, None] - lat
    diff_lng = lng[:, None] - lng

    # Finally Calculate haversine
    d = np.sin(diff_lat / 2) ** 2 + np.cos(lat[:, None]) * np.cos(lat) * np.sin(diff_lng / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(d))


def df_col2batches(df, column_name, chunk_size=30000):
    id_list = []
    num_chunks = len(df) // chunk_size + 1
    for i in range(num_chunks):
        id_batch = tuple(df.loc[i * chunk_size:(i + 1) * chunk_size, column_name])
        id_list.append(id_batch)
    return id_list


def df2batches(df, chunk_size=30000):
    df_list = []
    num_chunks = len(df) // chunk_size + 1
    for i in range(num_chunks):
        df_batch = df.loc[i * chunk_size:(i + 1) * chunk_size, :]
        df_list.append(df_batch)
    return df_list


def cluster_tempo(pur=None, temps=None, interval=30, maximum_days=2, norm=True):
    """
    :param maximum_days: number of days a stay spans, usually 2 days
    holder_size = maximum_days x 24 x (60 / interval)
    holder_day = 24 x (60 / interval)
    :type maximum_days: int
    :param interval: resolution of temporal counting in minute, e.g., 30 min
    :type interval: int
    :param pur: Purpose to add to the activity
    :type pur: str
    :param temps: List of tuples containing start (hour) and duration (minute)
    :type temps: list
    :return: A dataframe of half-hour frequency of a certain activity.
    :rtype:
    """
    holder_size = int(maximum_days * 24 * (60 / interval))
    holder = np.zeros((holder_size, 1))
    for tm in temps:
        start_ = int(np.floor(tm[0] * 60 / interval))
        end_ = int(np.floor((tm[0] * 60 + int(tm[1])) / interval))
        holder[start_:end_ + 1, 0] += 1
    if maximum_days != 1:
        mk = int(24 * (60 / interval))
        holder_day = holder[:mk] + holder[mk:]  # This fold it back to 24 hour temporal profile
    else:
        holder_day = holder
    df = pd.DataFrame()
    df.loc[:, 'half_hour'] = range(0, len(holder_day))
    df.loc[:, 'freq'] = holder_day
    if norm:
        df.loc[:, 'freq'] /= max(holder_day)
    if pur is not None:
        df.loc[:, 'activity'] = pur
    return df


def cluster_tempo_weighted(pur=None, temps=None, interval=30, maximum_days=2):
    """
    :param maximum_days: number of days a stay spans, usually 2 days
    holder_size = maximum_days x 24 x (60 / interval)
    holder_day = 24 x (60 / interval)
    :type maximum_days: int
    :param interval: resolution of temporal counting in minute, e.g., 30 min
    :type interval: int
    :param pur: Purpose to add to the activity
    :type pur: str
    :param temps: List of tuples containing start half_hour, duration, and weight
    :type temps: list
    :return: A dataframe of half-hour frequency of a certain activity.
    :rtype:
    """
    holder_size = int(maximum_days * 24 * (60 / interval))
    holder = np.zeros((holder_size, 1))
    holder_wt = np.zeros((holder_size, 1))
    for tm in temps:
        start_ = int(np.floor(tm[0] / interval))
        end_ = int(np.floor((tm[0] + int(tm[1])) / interval))
        holder[start_:end_ + 1, 0] += 1
        holder_wt[start_:end_ + 1, 0] += tm[2]
    if maximum_days != 1:
        mk = int(24 * (60 / interval))
        holder_day = holder[:mk] + holder[mk:]  # This fold it back to 24 hour temporal profile
        holder_day_wt = holder_wt[:mk] + holder_wt[mk:]  # This fold it back to 24 hour temporal profile
    else:
        holder_day = holder
        holder_day_wt = holder_wt
    df = pd.DataFrame()
    df.loc[:, 'half_hour'] = range(0, 48)
    df.loc[:, 'freq'] = holder_day / max(holder_day)
    df.loc[:, 'freq_wt'] = holder_day_wt / max(holder_day_wt)
    if pur is not None:
        df.loc[:, 'activity'] = pur
    return df


def record_weights(data):
    """
    This function produces weight column based the temporal distribution of records.
    The weight is for approximating evenly sampling.
    This function assumes the default parameters adopted in cluster_tempo.
    :type data: dataframe with h_s, dur columns
    :return: a dataframe with wt
    """
    # Get weights
    recs = list(data[['h_s', 'dur']].to_records(index=False))
    df_tp = cluster_tempo(temps=recs)
    df_tp.loc[:, 'wt'] = df_tp.loc[:, 'freq'].apply(lambda x: 1 / x if x != 0 else 0)
    wt = df_tp.loc[:, 'wt'].values.reshape((48, 1))

    # Assign weights to each location
    def row_weight_assign(row):
        start_ = int(np.floor(row['h_s'] / 30))
        end_ = int(np.floor((row['h_s'] + int(row['dur'])) / 30))
        return np.sum(wt[start_:end_ + 1, 0])

    data.loc[:, 'wt'] = data.apply(lambda row: row_weight_assign(row), axis=1)
    return data
