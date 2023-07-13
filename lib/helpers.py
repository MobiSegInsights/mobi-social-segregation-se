import os
from pathlib import Path
import yaml
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import pickle
import numpy as np


ROOT_dir = Path(__file__).parent.parent
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


class EBMResultsOrganizer:
    def __init__(self, file_loc=None):
        self.model = pickle.load(open(file_loc, "rb"))
        self.all_fscore = {}
        self.X_train = None
        self.df = None
        # Define mapping rules for naming the features
        self.feature_dict = {"weekend": 'Weekend', 'weekday': 'Weekday',
                        'non_holiday': 'Non-holiday', 'holiday': 'Holiday',
                        'number_of_locations': 'No. of unique locations visited',
                        'number_of_visits': 'No. of visits',
                        'average_displacement': 'Average displacement',
                        'radius_of_gyration': 'Radius of gyration',
                        'median_distance_from_home': 'Median distance from home',
                        "Not Sweden": 'Prob. born outside Sweden',
                        'Lowest income group': 'Prob. in lowest income group',
                        'car_ownership': 'Prob. of owning a car',
                        'cum_jobs': 'Job accessibility by car',
                        'cum_stops': 'Transit accessibility by walking',
                        'evenness_income_resi': 'Residential income segregation',
                        'num_jobs': 'Job density at residence',
                        'num_stops': 'Transit stop density at residence',
                        'gsi': 'GSI at residence',
                        'length_density': 'Pedestrian network density at residence'}
        self.color_dict = {"weekend": 'purple', 'weekday': 'purple',
                      'non_holiday': 'purple', 'holiday': 'purple',
                      'number_of_locations': 'coral',
                      'number_of_visits': 'coral',
                      'average_displacement': 'coral',
                      'radius_of_gyration': 'coral',
                      'median_distance_from_home': 'coral',
                      "Not Sweden": 'steelblue',
                      'Lowest income group': 'steelblue',
                      'car_ownership': 'steelblue',
                      'cum_jobs': 'darkgreen',
                      'cum_stops': 'darkgreen',
                      'evenness_income_resi': 'steelblue',
                      'num_jobs': 'darkgreen',
                      'num_stops': 'darkgreen',
                      'gsi': 'darkgreen',
                      'length_density': 'darkgreen'}

    def load_raw_data(self, select=None):
        df = pd.read_parquet(ROOT_dir + "/results/data4model_individual.parquet")
        df = pd.get_dummies(df, columns=['weekday'], prefix='weekday_', prefix_sep='')
        df = pd.get_dummies(df, columns=['holiday'], prefix='holiday_', prefix_sep='')
        df = df.rename(columns={'weekday_0': 'weekend',
                                'weekday_1': 'weekday',
                                'holiday_0': 'non_holiday',
                                'holiday_1': 'holiday'})
        print('Label low, middle, and high income.')

        def label_income_group(x):
            if x <= 0.1:
                return 'High income'
            if x > 0.4:
                return 'Low income'
            return 'Middle income'

        df.loc[:, 'Income group'] = df.loc[:, 'Lowest income group'].apply(label_income_group)
        if select != 'all':
            df = df.loc[df['Income group'] == select, :]

        predictors = ['weekend', 'weekday', 'non_holiday', 'holiday',
                      'number_of_locations', 'number_of_visits', 'average_displacement', 'radius_of_gyration',
                      'median_distance_from_home',
                      'Not Sweden', 'Lowest income group', 'car_ownership',
                      'cum_jobs', 'cum_stops', 'evenness_income_resi',
                      'num_jobs', 'num_stops', 'gsi', 'length_density']
        target_column = 'evenness_income'
        X = df[predictors]
        y = df[target_column]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=40)
        self.X_train = X_train
        self.df = df

    def performance(self):
        perf_train = self.model["perf_train"]
        perf_test = self.model["perf_test"]
        return dict(rmse_train=perf_train['rmse'],
                    r2_train=perf_train['r2'],
                    rmse_test=perf_test['rmse'],
                    r2_test=perf_test['r2'])

    def feature_importance(self):
        all_features = {}
        for var, score in zip(self.model["overall"]["names"], self.model["overall"]["scores"]):
            if var not in all_features:
                all_features[var] = score
        # Feature score data prep.
        df_f = pd.DataFrame([(k, v) for k, v in all_features.items()],
                            columns=('Feature/Interaction', 'Score')).sort_values(by='Score', ascending=False)
        df_f.loc[:, 'Name'] = df_f.loc[:, 'Feature/Interaction'].apply(
            lambda x: self.feature_dict[x] if ' & ' not in x else ' & '.join([self.feature_dict[v] for v in x.split(' & ')]))
        df_f.loc[:, 'Color'] = df_f.loc[:, 'Feature/Interaction'].apply(
            lambda x: self.color_dict[x] if ' & ' not in x else 'black')
        df_f = df_f.loc[:, ['Name', 'Color', 'Score']].sort_values(by='Score', ascending=False)
        return df_f

    def feature_scores(self):
        ## f_score
        self.all_fscore["feature"] = {}
        self.all_fscore["interaction"] = {}
        for var, score in self.model["f_score"].items():
            if var not in self.all_fscore:
                if len(score) == 7:
                    self.all_fscore["feature"][var] = [score["names"],
                                                       score["scores"],
                                                       score["lower_bounds"],
                                                       score["upper_bounds"]]
                else:
                    self.all_fscore["interaction"][var] = [score["left_names"],
                                                           score["right_names"],
                                                           score["scores"]]

    def single_feature_effect(self):
        fscore_f = []
        for k, v in self.all_fscore['feature'].items():
            tp = pd.DataFrame()
            tp['var'] = [k] * len(v[1])
            scaler = StandardScaler().fit(self.X_train[k].values.reshape(-1, 1))
            if k in ('weekend', 'weekday', 'non_holiday', 'holiday'):
                tp['x'] = scaler.inverse_transform([v[0][0], v[0][2]])
            else:
                tp['x'] = scaler.inverse_transform(v[0][:-1])
            tp['y'] = v[1]
            tp['y_lower'] = v[2]
            tp['y_upper'] = v[3]
            fscore_f.append(tp)
        df_fscore_f = pd.concat(fscore_f)
        return df_fscore_f

    def interection_effect(self, path2save=None):
        labels_cat = ['weekend', 'weekday', 'non_holiday', 'holiday']
        labels_cat_names = {"weekend": 'Weekend', 'weekday': 'Weekday',
                            'non_holiday': 'Non-holiday', 'holiday': 'Holiday'}
        for k, v in self.all_fscore['interaction'].items():
            tp = pd.DataFrame(v[2])
            tp = tp.unstack().reset_index()
            var1 = k.split(' & ')[0]
            var2 = k.split(' & ')[1]

            scaler_x = StandardScaler().fit(self.X_train[var1].values.reshape(-1, 1))
            scaler_y = StandardScaler().fit(self.X_train[var2].values.reshape(-1, 1))
            v1_values = scaler_x.inverse_transform(v[0])
            v2_values = scaler_y.inverse_transform(v[1])

            tp.columns = [var1, var2, 'f']
            tp.loc[:, var1] = tp.loc[:, var1].apply(lambda x: v1_values[x])
            tp.loc[:, var2] = tp.loc[:, var2].apply(lambda x: v2_values[x])

            # Get the frequency of the interaction cells
            if var1 not in labels_cat:
                edges_x = np.insert(v1_values, 0, self.X_train.loc[:, var1].min() - 1, axis=0)
            else:
                edges_x = np.array(v1_values + [v1_values[-1] + 1])

            if var2 not in labels_cat:
                edges_y = np.insert(v2_values, 0, self.X_train.loc[:, var2].min() - 1, axis=0)
            else:
                edges_y = np.array(v2_values + [v2_values[-1] + 1])

            h, _, _ = np.histogram2d(self.df.loc[:, var1], self.df.loc[:, var2], bins=(edges_x, edges_y))
            df_h = pd.DataFrame(h, index=v1_values, columns=v2_values)
            df_h = df_h.stack().reset_index()
            df_h.columns = [var1, var2, 'freq']
            tp = pd.merge(tp, df_h, on=[var1, var2])
            if var1 in labels_cat:
                tp.loc[:, var1] = tp.loc[:, var1].map(labels_cat_names[var1])
            if var2 in labels_cat:
                tp.loc[:, var2] = tp.loc[:, var2].map(labels_cat_names[var2])
            tp.to_csv(path2save + f'{k}.csv', index=False)
