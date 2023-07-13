import sys
from pathlib import Path
import os
import pandas as pd
import sqlalchemy
import time


ROOT_dir = Path(__file__).parent.parent
sys.path.append(ROOT_dir)
sys.path.insert(0, os.path.join(ROOT_dir, 'lib'))

from lib import activity_patterns as ap
from lib import preprocess


if __name__ == '__main__':
    print('Aggregating survey temporal patterns.')
    df_act = pd.read_csv(os.path.join(ROOT_dir, 'dbs/survey/day_act.csv'))
    df_act.loc[:, 'h_s'] /= 60
    all = list(df_act.loc[:, ['h_s', 'dur']].to_records(index=False))
    list_df_tempo = [preprocess.cluster_tempo(pur='All', temps=all, interval=30, maximum_days=1, norm=False)]

    for p in df_act.Purpose.unique():
        temps = list(df_act.loc[df_act['Purpose'] == p, ['h_s', 'dur']].to_records(index=False))
        list_df_tempo.append(preprocess.cluster_tempo(pur=p, temps=temps, interval=30, maximum_days=1, norm=False))
    df_tempo = pd.concat(list_df_tempo)
    df_tempo.to_csv(os.path.join(ROOT_dir, 'results/activity_patterns_survey.csv'), index=False)

    print(f'Loading data:')
    start = time.time()
    activity_patterns = ap.ActivityPatterns()
    activity_patterns.load_process_data()
    end = time.time()
    time_elapsed = (end - start) // 60  # in minutes
    print(f"Data processed in {time_elapsed} minutes.")

    print(f'Describing data aggregate temporal patterns:')
    start = time.time()
    df = activity_patterns.aggregate_activity_temporal()
    df.to_csv(os.path.join(ROOT_dir, 'results/activity_patterns_mad.csv'), index=False)
    end = time.time()
    time_elapsed = (end - start) // 60  # in minutes
    print(f"Aggregate temporal profiles computed in {time_elapsed} minutes.")

    print(f'Calculating record weights:')
    start = time.time()
    activity_patterns.add_weight2records()
    end = time.time()
    time_elapsed = (end - start) // 60  # in minutes
    print(f"Weights computed in {time_elapsed} minutes.")

    print(f'Calculating cluster statistics:')
    start = time.time()
    activity_patterns.cluster_stats()
    end = time.time()
    time_elapsed = (end - start) // 60  # in minutes
    print(f"Cluster statistics computed in {time_elapsed} minutes.")

    top_n = 3
    print(f'Calculating temporal patterns of top {top_n} clusters (weighted):')
    start = time.time()
    engine = sqlalchemy.create_engine(
        f'postgresql://{activity_patterns.user}:{activity_patterns.password}'
        f'@localhost:{activity_patterns.port}/{activity_patterns.db_name}')
    df_top = pd.read_sql_query(sql="""SELECT * FROM description.clusters_top%s_wt_p;"""%top_n,
                               con=engine)
    activity_patterns.activities_temporal(df_top=df_top)
    end = time.time()
    time_elapsed = (end - start) // 60  # in minutes
    print(f"Cluster statistics computed in {time_elapsed} minutes.")
