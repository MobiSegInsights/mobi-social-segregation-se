import sys
import subprocess
import os
import pandas as pd
import sqlalchemy
import time


def get_repo_root():
    """Get the root directory of the repo."""
    dir_in_repo = os.path.dirname(os.path.abspath('__file__'))
    return subprocess.check_output('git rev-parse --show-toplevel'.split(),
                                   cwd=dir_in_repo,
                                   universal_newlines=True).rstrip()


ROOT_dir = get_repo_root()
sys.path.append(ROOT_dir)
sys.path.insert(0, ROOT_dir + '/lib')

from lib import activity_patterns as ap


if __name__ == '__main__':
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
    df_top = pd.read_sql_query(sql="""SELECT * FROM description.clusters_top%s_wt;"""%top_n,
                               con=engine)
    print(f'Keep those devices with more than one cluster.')
    df_top_size = df_top['uid'].value_counts().rename_axis('uid').reset_index(name='cluster_num')
    df_top = df_top.loc[df_top.uid.isin(df_top_size.loc[df_top_size.cluster_num > 1, 'uid']), :]
    activity_patterns.activities_temporal(df_top=df_top)
    end = time.time()
    time_elapsed = (end - start) // 60  # in minutes
    print(f"Cluster statistics computed in {time_elapsed} minutes.")
