import os
import subprocess
import yaml


def get_repo_root():
    """Get the root directory of the repo."""
    dir_in_repo = os.path.dirname(os.path.abspath('__file__'))
    return subprocess.check_output('git rev-parse --show-toplevel'.split(),
                                   cwd=dir_in_repo,
                                   universal_newlines=True).rstrip()


ROOT_dir = get_repo_root()
with open(os.path.join(ROOT_dir, 'dbs', 'keys.yaml')) as f:
    keys_manager = yaml.load(f, Loader=yaml.FullLoader)


def odm_ssi(df, x_field=None, y_field=None, norm=True):
    if norm:
        df.loc[:, x_field] = df.loc[:, x_field] / df.loc[:, x_field].sum()
        df.loc[:, y_field] = df.loc[:, y_field] / df.loc[:, y_field].sum()
    df.loc[:, 'flow_min'] = df.apply(lambda row: min(row[x_field], row[y_field]), axis=1)
    SSI = 2 * df.loc[:, 'flow_min'].sum() / \
          (df.loc[:, y_field].sum() + df.loc[:, x_field].sum())
    return SSI


def list2chunks(target_list=None, chunk_num=None):
    chunks = []
    chunk_size = int(len(target_list) / chunk_num) + (len(target_list) // chunk_num > 0)
    for i in range(chunk_num):
        chunk = target_list[i * chunk_size:(i + 1) * chunk_size]
        if len(chunk) > 0:
            chunks.append(chunk)
    return chunks