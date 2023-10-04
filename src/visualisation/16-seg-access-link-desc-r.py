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


def delta_ice(ice_r, ice_e):
    if ice_r < 0:
        return -(ice_e - ice_r)
    return ice_e - ice_r


if __name__ == '__main__':
    print(ROOT_dir)
    df_exp = pd.read_parquet(os.path.join(ROOT_dir, 'results/data4model_individual.parquet'))
    df_sim = pd.read_parquet(os.path.join(ROOT_dir, 'results/seg_pref_reduced.parquet'))
    df_exp = df_exp.loc[(df_exp['weekday'] == 1) & (df_exp['holiday'] == 0), :]
    cols = ['uid', 'region', 'wt_p', 'cum_jobs_pt', 'cum_jobs_car']
    df_exp = pd.merge(df_exp[cols], df_sim[['uid', 'ice_r', 'ice_e', 'ice_ep']], on='uid')
    df_exp.loc[:, 'wt_p'] /= 1000
    df_exp = pd.merge(df_exp[cols], df_sim[['uid', 'ice_r', 'ice_e', 'ice_ep']], on='uid')
    df_exp.loc[:, 'delta_ice'] = df_exp.apply(lambda row: delta_ice(row['ice_r'], row['ice_e']), axis=1)
    df_exp.loc[:, 'delta_ice_p'] = df_exp.apply(lambda row: delta_ice(row['ice_r'], row['ice_ep']), axis=1)

    ylb = 'Weighted individual count ($\\times$10$^3$)'
    alpha = 0.4
    sz = (4, 4)

    ax1 = pw.Brick("ax1", figsize=sz)
    sns.histplot(data=df_exp, x='cum_jobs_car', weights='wt_p',
                 bins=[10 ** (x / 5) for x in range(0, 30)], kde=False, fill=True, alpha=alpha, element='step', ax=ax1)
    wdf = DescrStatsW(df_exp['cum_jobs_car'], weights=df_exp['wt_p'], ddof=1)
    sts = wdf.quantile([0.50])
    q50 = sts.values[0]
    ax1.axvline(q50, label="median = %.0f" % q50)
    ax1.legend(loc='upper right', bbox_to_anchor=(1, 1.1), frameon=False)
    ax1.set(xlabel='Job accessibility by car', ylabel=ylb)
    ax1.set_xscale('log')
    ax1.set_title('(a)', loc="left")
    ax1.set_xlim(1, 10 ** 6)
    ax1.savefig()

    ax2 = pw.Brick("ax2", figsize=sz)
    sns.histplot(data=df_exp, x='cum_jobs_pt', weights='wt_p',
                 bins=[10 ** (x / 5) for x in range(0, 31)], kde=False, fill=True, alpha=alpha, element='step', ax=ax2)
    wdf = DescrStatsW(df_exp['cum_jobs_pt'], weights=df_exp['wt_p'], ddof=1)
    sts = wdf.quantile([0.50])
    q50 = sts.values[0]
    ax2.axvline(q50, label="median = %.0f" % q50)
    ax2.legend(loc='upper right', bbox_to_anchor=(1, 1.1), frameon=False)
    ax2.set(xlabel='Job accessibility by transit', ylabel=ylb)
    ax2.set_xscale('log')
    ax2.set_title('(b)', loc="left")
    ax2.set_xlim(1, 550000)
    ax2.savefig()

    df2plot = pd.melt(df_exp, id_vars=['wt_p'], value_vars=['ice_r', 'ice_e', 'ice_ep'])
    ax3 = pw.Brick("ax3", figsize=sz)
    colors = sns.color_palette("colorblind", 3)
    h = sns.histplot(data=df2plot, x='value', weights='wt_p', hue='variable',
                     hue_order=['ice_r', 'ice_e', 'ice_ep'],
                     bins=35, kde=False, fill=True, alpha=alpha, element='step', ax=ax3)
    wdf = DescrStatsW(df_exp['ice_e'], weights=df_exp['wt_p'], ddof=1)
    sts = wdf.quantile([0.50])
    q501 = sts.values[0]
    wdf = DescrStatsW(df_exp['ice_r'], weights=df_exp['wt_p'], ddof=1)
    sts = wdf.quantile([0.50])
    q502 = sts.values[0]
    wdf = DescrStatsW(df_exp['ice_ep'], weights=df_exp['wt_p'], ddof=1)
    sts = wdf.quantile([0.50])
    q503 = sts.values[0]
    ax3.axvline(q501, color=colors[1])
    ax3.axvline(q502, color=colors[0])
    ax3.axvline(q503, color=colors[2])
    ax3.legend(labels=["Preference-reduced (%.2f)" % q503,
                       "Experienced (%.2f)" % q501,
                       "Residential (%.2f)" % q502],
               loc='upper right', bbox_to_anchor=(1, 1.3), frameon=False)
    ax3.set_xlim(-1, 1)
    ax3.set(xlabel='Nativity segregation', ylabel=ylb)
    ax3.set_title('(c)', loc="left")
    ax3.savefig()

    df2plot = pd.melt(df_exp, id_vars=['wt_p'], value_vars=['delta_ice', 'delta_ice_p'])
    ax4 = pw.Brick("ax4", figsize=sz)
    colors = sns.color_palette("colorblind", 2)
    h = sns.histplot(data=df2plot, x='value', weights='wt_p', hue='variable',
                     hue_order=['delta_ice', 'delta_ice_p'],
                     bins=35, kde=False, fill=True, alpha=alpha, element='step', ax=ax4)
    wdf = DescrStatsW(df_exp['delta_ice'], weights=df_exp['wt_p'], ddof=1)
    sts = wdf.quantile([0.50])
    q501 = sts.values[0]
    wdf = DescrStatsW(df_exp['delta_ice_p'], weights=df_exp['wt_p'], ddof=1)
    sts = wdf.quantile([0.50])
    q502 = sts.values[0]
    ax4.axvline(q501, color=colors[0])
    ax4.axvline(q502, color=colors[1])
    ax4.legend(labels=["Preference-reduced disparity (%.2f)" % q502,
                       "Experienced disparity (%.2f)" % q501],
               loc='upper right', bbox_to_anchor=(1, 1.3), frameon=False)
    ax4.set_xlim(-1.5, 1.5)
    ax4.set(xlabel='Nativity segregation disparity', ylabel=ylb)
    ax4.set_title('(d)', loc="left")
    ax4.savefig()

    ax12 = ax1 | ax2
    ax34 = ax3 | ax4
    ax1234 = ax12 / ax34
    ax1234.savefig(os.path.join(ROOT_dir, 'figures/seg_trans_desc_r.png'), dpi=300)

