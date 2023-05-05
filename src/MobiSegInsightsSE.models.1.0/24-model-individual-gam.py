import os, sys
import subprocess
from interpret.glassbox import ExplainableBoostingRegressor
from interpret.perf import RegressionPerf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import pandas as pd
import shap
import numpy as np
import pickle


def get_repo_root():
    """Get the root directory of the repo."""
    dir_in_repo = os.path.dirname(os.path.abspath('__file__'))
    return subprocess.check_output('git rev-parse --show-toplevel'.split(),
                                   cwd=dir_in_repo,
                                   universal_newlines=True).rstrip()


ROOT_dir = get_repo_root()
sys.path.append(ROOT_dir)
sys.path.insert(0, ROOT_dir + '/lib')


class GAMModel:
    def __init__(self):
        self.data = None
        self.predictors = ['weekend', 'weekday', 'non_holiday', 'holiday',
                           'number_of_locations', 'number_of_visits', 'average_displacement', 'radius_of_gyration',
                           'median_distance_from_home',
                           'Not Sweden', 'Lowest income group', 'car_ownership',
                           'cum_jobs', 'cum_stops', 'evenness_income_resi',
                           'num_jobs', 'num_stops', 'length_density']   # 'gsi',
        self.target_column = 'evenness_income'
        self.X_train = None

    def load_data(self):
        # Load data for modelling
        print('Load data.')
        df = pd.read_parquet("results/data4model_individual.parquet")
        print('One Hot Encoder')
        df = pd.get_dummies(df, columns=['weekday'], prefix='weekday_', prefix_sep='')
        self.data = pd.get_dummies(df, columns=['holiday'], prefix='holiday_', prefix_sep='')
        self.data = self.data.rename(columns={'weekday_0': 'weekend',
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

        self.data.loc[:, 'Income group'] = self.data.loc[:, 'Lowest income group'].apply(label_income_group)
        print(self.data.iloc[0])

    def ebm_model(self, df):
        print('Preprocess features...')
        X = df[self.predictors]
        y = df[self.target_column]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=40)

        print('Normalization...')
        scaler = StandardScaler().fit(X_train)
        X_train = scaler.transform(X_train)
        X_test = scaler.transform(X_test)
        self.X_train = X_train

        print('Training...')
        seed = 1
        ebm = ExplainableBoostingRegressor(interactions=3, random_state=seed,
                                           feature_names=self.predictors, outer_bags=2)
        ebm.fit(X_train, y_train)  # Works on dataframes and numpy arrays
        # Performance
        ebm_perf_test = RegressionPerf(ebm.predict).explain_perf(X_test, y_test, name='EBM')
        ebm_perf_train = RegressionPerf(ebm.predict).explain_perf(X_train, y_train, name='EBM')

        ebm_global = ebm.explain_global(name='EBM')

        # Log data
        overall = ebm_global.data()
        f_score = {}
        for i, f in zip(range(0, len(ebm_global.feature_names)), ebm_global.feature_names):
            f_score[f] = ebm_global.data(i)
        return ebm, ebm_perf_train.data(), ebm_perf_test.data(), overall, f_score

    def explain_ebm(self, ebm_model=None):
        # explain the GAM model with SHAP
        np.random.seed(1)
        background = shap.maskers.Independent(self.X_train, max_samples=1000)
        explainer_ebm = shap.Explainer(ebm_model.predict, background)
        shap_values_ebm = explainer_ebm(self.X_train[np.random.randint(self.X_train.shape[0], size=10000), :])
        shap_values_ebm.feature_names = self.predictors
        return shap_values_ebm

    def ebm_model_train(self, df=None, file_name='model', explain=False):
        ebm, perf_train, perf_test, overall, f_score = self.ebm_model(df=df)
        ebm_learned = {"perf_train": perf_train, "perf_test": perf_test,
                       "overall": overall, "f_score": f_score}
        pickle.dump(ebm_learned, open(os.path.join(ROOT_dir, 'results', 'ebm', f"{file_name}.p"), "wb"))
        print("Results pickled.")
        if explain:
            shap_values_ebm = self.explain_ebm(ebm_model=ebm)
            pickle.dump(shap_values_ebm,
                        open(os.path.join(ROOT_dir, 'results', 'ebm', f"{file_name}_explained.p"), "wb"))
            print("Shap values pickled.")


if __name__ == '__main__':
    gam = GAMModel()
    gam.load_data()
    # Modelling all data
    print("Model all the individuals.")
    gam.ebm_model_train(df=gam.data,
                        file_name='model_all',
                        explain=False)

    # Modelling low income
    print("Model low income.")
    gam.ebm_model_train(df=gam.data[gam.data['Income group'] == 'Low income'],
                        file_name='model_low_income',
                        explain=True)

    # Modelling high income
    print("Model low income.")
    gam.ebm_model_train(df=gam.data[gam.data['Income group'] == 'High income'],
                        file_name='model_high_income',
                        explain=True)
