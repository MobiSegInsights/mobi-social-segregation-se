import sys
from pathlib import Path
import os
import patchworklib as pw
import pandas as pd
from statsmodels.stats.weightstats import DescrStatsW
import seaborn as sns
import matplotlib as mpl
mpl.rcParams.update(mpl.rcParamsDefault)
sns.set_palette(sns.color_palette("colorblind"))
font = {'size': 14}
mpl.rc('font', **font)


ROOT_dir = Path(__file__).parent.parent.parent
sys.path.append(ROOT_dir)
sys.path.insert(0, os.path.join(ROOT_dir, 'lib'))


if __name__ == '__main__':
    print(ROOT_dir)
    df_exp = pd.read_parquet(os.path.join(ROOT_dir, 'results/data4model_individual.parquet'))
    df_exp = df_exp.loc[(df_exp['weekday'] == 1) & (df_exp['holiday'] == 0), :]
    cols = ['uid', 'region', 'wt_p',
            'Lowest income group', 'car_ownership', 'radius_of_gyration',
            'cum_jobs', 'cum_stops',
            'ice_birth_resi', 'ice_birth']
    df_exp = df_exp[cols]
    df_exp.loc[:, 'wt_p'] /= 1000

    ylb = 'Weighted individual count ($\\times$10$^3$)'
    alpha = 0.4
    sz = (3.5, 3.5)
    ax1 = pw.Brick("ax1", figsize=sz)
    sns.histplot(data=df_exp.loc[(df_exp['Lowest income group'] > 0) & (df_exp['Lowest income group'] < 1), :],
                 x='Lowest income group', weights='wt_p',
                 bins=35, kde=False, fill=True, alpha=alpha, element='step', ax=ax1)
    wdf = DescrStatsW(df_exp['Lowest income group'], weights=df_exp['wt_p'], ddof=1)
    sts = wdf.quantile([0.50])
    q50 = sts.values[0]
    ax1.axvline(q50, label="median = %.2f" % q50)
    ax1.set(xlabel='Share of lowest income$^1$', ylabel=ylb)
    ax1.legend(loc='upper right', bbox_to_anchor=(1, 1.1), frameon=False)
    ax1.set_title('(a)', loc="left")
    ax1.savefig()

    ax2 = pw.Brick("ax2", figsize=sz)
    sns.histplot(data=df_exp, x='car_ownership', weights='wt_p',
                 bins=35, kde=False, fill=True, alpha=alpha, element='step', ax=ax2)
    wdf = DescrStatsW(df_exp['car_ownership'], weights=df_exp['wt_p'], ddof=1)
    sts = wdf.quantile([0.50])
    q50 = sts.values[0]
    ax2.axvline(q50, label="median = %.2f" % q50)
    ax2.legend(loc='upper right', bbox_to_anchor=(1, 1.1), frameon=False)
    ax2.set(xlabel='Car ownership (/capita)', ylabel=ylb)
    ax2.set_title('(b)', loc="left")
    ax2.savefig()

    ax3 = pw.Brick("ax3", figsize=sz)
    sns.histplot(data=df_exp, x='radius_of_gyration', weights='wt_p',
                 bins=[10 ** (x / 5) for x in range(-4, 40)], kde=False, fill=True, alpha=alpha, element='step', ax=ax3)
    wdf = DescrStatsW(df_exp['radius_of_gyration'], weights=df_exp['wt_p'], ddof=1)
    sts = wdf.quantile([0.50])
    q50 = sts.values[0]
    ax3.axvline(q50, label="median = %.0f" % q50)
    ax3.legend(loc='upper right', bbox_to_anchor=(1, 1.1), frameon=False)
    ax3.set(xlabel='Mobility range (km)', ylabel=ylb)
    ax3.set_xscale('log')
    ax3.set_title('(c)', loc="left")
    ax3.set_xlim(0.1, 10 ** 4)
    ax3.savefig()

    ax4 = pw.Brick("ax4", figsize=sz)
    sns.histplot(data=df_exp, x='cum_jobs', weights='wt_p',
                 bins=[10 ** (x / 5) for x in range(0, 50)], kde=False, fill=True, alpha=alpha, element='step', ax=ax4)
    wdf = DescrStatsW(df_exp['cum_jobs'], weights=df_exp['wt_p'], ddof=1)
    sts = wdf.quantile([0.50])
    q50 = sts.values[0]
    ax4.axvline(q50, label="median = %.0f" % q50)
    ax4.legend(loc='upper right', bbox_to_anchor=(1, 1.1), frameon=False)
    ax4.set(xlabel='Job accessibility by car$^2$', ylabel=ylb)
    ax4.set_xscale('log')
    ax4.set_title('(d)', loc="left")
    ax4.set_xlim(1, 10 ** 6)
    ax4.savefig()

    ax5 = pw.Brick("ax5", figsize=sz)
    sns.histplot(data=df_exp, x='cum_stops', weights='wt_p',
                 bins=[10 ** (x / 5) for x in range(0, 31)], kde=False, fill=True, alpha=alpha, element='step', ax=ax5)
    wdf = DescrStatsW(df_exp['cum_stops'], weights=df_exp['wt_p'], ddof=1)
    sts = wdf.quantile([0.50])
    q50 = sts.values[0]
    ax5.axvline(q50, label="median = %.0f" % q50)
    ax5.legend(loc='upper right', bbox_to_anchor=(1, 1.1), frameon=False)
    ax5.set(xlabel='Transit accessibility by walk$^3$', ylabel=ylb)
    ax5.set_xscale('log')
    ax5.set_title('(e)', loc="left")
    ax5.set_xlim(1, 10**3.1)
    ax5.savefig()

    df2plot = pd.melt(df_exp, id_vars=['wt_p'], value_vars=['ice_birth_resi', 'ice_birth'])
    ax6 = pw.Brick("ax6", figsize=sz)
    colors = sns.color_palette("colorblind", 2)
    h = sns.histplot(data=df2plot, x='value', weights='wt_p', hue='variable',
                     hue_order=['ice_birth_resi', 'ice_birth'],
                     bins=35, kde=False, fill=True, alpha=alpha, element='step', ax=ax6)
    wdf = DescrStatsW(df_exp['ice_birth'], weights=df_exp['wt_p'], ddof=1)
    sts = wdf.quantile([0.50])
    q501 = sts.values[0]
    wdf = DescrStatsW(df_exp['ice_birth_resi'], weights=df_exp['wt_p'], ddof=1)
    sts = wdf.quantile([0.50])
    q502 = sts.values[0]
    ax6.axvline(q501, color=colors[1])
    ax6.axvline(q502, color=colors[0])
    ax6.legend(labels=["Experienced (%.2f)" % q501,
                       "Residential (%.2f)" % q502],
               loc='upper right', bbox_to_anchor=(1, 1.2), frameon=False)
    ax6.set_xlim(-1, 1)
    ax6.set(xlabel='Nativity segregation', ylabel=ylb)
    ax6.set_title('(f)', loc="left")
    ax6.savefig()

    ax12 = ax1 | ax2
    ax34 = ax3 | ax4
    ax56 = ax5 | ax6
    ax123456 = ax12 / (ax34 / ax56)
    ax123456.savefig(os.path.join(ROOT_dir, 'figures/seg_trans_desc.png'), dpi=300)

