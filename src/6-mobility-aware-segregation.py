import sys
import subprocess
import os


def get_repo_root():
    """Get the root directory of the repo."""
    dir_in_repo = os.path.dirname(os.path.abspath('__file__'))
    return subprocess.check_output('git rev-parse --show-toplevel'.split(),
                                   cwd=dir_in_repo,
                                   universal_newlines=True).rstrip()


ROOT_dir = get_repo_root()
sys.path.append(ROOT_dir)
sys.path.insert(0, ROOT_dir + '/lib')

from lib import metrics as mt
from lib import preprocess as preprocess


if __name__ == '__main__':
    mobi_seg = mt.MobilitySegregationPlace()
    mobi_seg.load_home_seg_uid()
    mobi_seg.load_mobi_data(test=False)
    mobi_seg.load_hexagons_mobi_metrics()
    mobi_seg.mobi_data_processing()
    mobi_seg.add_spatio_unit()
    mobi_seg.add_temporal_unit(num_groups=48)
    print(mobi_seg.mobi_data.iloc[0])
    mobi_seg.aggregating_metrics()