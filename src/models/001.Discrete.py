# -*- coding: utf-8 -*-
"""
Created on Thu Mar 12 14:02:38 2020

@author: M44427


Just some additional preprocessing
"""

import numpy as np
import pandas as pd

import sys
import csv
import math
from operator import itemgetter
import time

from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.externals import joblib
from sklearn.feature_selection import RFE, VarianceThreshold, SelectFromModel
from sklearn.feature_selection import SelectKBest, mutual_info_regression, mutual_info_classif, chi2
from sklearn import metrics
from sklearn.model_selection import cross_validate, train_test_split
from sklearn.preprocessing import KBinsDiscretizer, scale

import xgboost as xgb
from catboost import CatBoostClassifier, cv, Pool



plays = pd.read_csv("../../data/clean/plays.csv", low_memory = False)
drives = pd.read_csv("../../data/drives/drives.csv", low_memory = False)
drives.drop(['posteam_type', 'year', 'month', 'qtr', 'cd_start_yds_to_go', 'cd_start_time_left', 'cd_start_time_left', 'cd_start_score_diff',
             'cd_plays', 'points_scored', 'cd_run_percentage', 'cd_drive_length', 'cd_avg_yds_to_go_3rd', 'cd_avg_first_yds_gain', 'cd_net_penatly_yd_play',
             'cd_net_penalties_play', 'cd_pass_yard_att', 'cd_rush_yard_att', 'cd_sacks_play', 'cd_tfl_play', 'cd_expl_runs_play', 'cd_expl_pass_play',
             'cd_pass_completion_pct', 'cd_third_conversions'], axis = 1, inplace = True)

del drives['ld_outcome']
del drives['ld_opp_outcome']

# Get current drives outcome to remove any drives that end in turnovers or qb_kneels
current_drive_outcome = pd.read_csv("../../data/clean/DriveOutcome.csv", low_memory = False)
del current_drive_outcome['Unnamed: 0']
plays = pd.merge(plays, current_drive_outcome, how='inner', on=['game_id', 'drive', 'posteam'])
plays = plays[~((plays['drive_outcome'] == 'turnover') | (plays['drive_outcome'] == "turnover_on_downs") | (plays['drive_outcome'] == "qb_kneel") | (plays['drive_outcome'] == "qb_spike"))]
del plays['drive_outcome']

plays = pd.merge(plays, drives, how='inner', on=['game_id', 'drive', 'posteam'])

# Merge prior drive information
# Change certain columns to categorical variables
#drives['month'] = drives['month'].astype('category')
#drives['qtr'] = drives['qtr'].astype('category')


# Create Game-Drive ID
plays['game-drive'] = plays['game_id'].astype(str) + '-' + plays['drive'].astype(str)
del plays['game_id']
del plays['drive']
del plays['play_id']



# Set up for target variable
plays['next_play'] = plays['play_type'].shift(-1)
plays['next_id'] = plays['game-drive'].shift(-1)
plays['target'] = np.where(plays['next_id'] == plays['game-drive'], plays['next_play'], np.nan)

del plays['next_id']
del plays['next_play']
del plays['sp']
#del plays['play_type']



### remove unecessary columns
del plays['extra_point_result']
del plays['two_point_conv_result']
del plays['timeout']
del plays['penalty_team']
del plays['penalty_type']
del plays['penalty_yards']
del plays['defensive_two_point_attempt']
del plays['defensive_two_point_conv']
del plays['game_half']

plays.drop(['punt_blocked', 'fumble_forced', 'fumble_not_forced', 'fumble_out_of_bounds', 'safety', 'penalty', 'fumble_lost', 'extra_point_attempt',
            'two_point_attempt', 'field_goal_attempt', 'points_earned', 'yrdln', 'RunOver10', 'PassOver20', 'complete_pass', 'touchdown', 'rush_touchdown', 'pass_touchdown', 
            'rush_attempt', 'pass_attempt', 'qb_hit', 'tackled_for_loss', 'incomplete_pass', 'qb_kneel'], axis =1, inplace = True)


# Remove in the interim
del plays['posteam']
del plays['defteam']
del plays['pass_length']
del plays['pass_location']
del plays['run_gap']
del plays['run_location']
del plays['Time']

# Create Dummy Data
plays['home'] = pd.get_dummies(plays['posteam_type'], drop_first=True)
del plays['posteam_type']
plays = pd.get_dummies(plays, columns=['play_type'])

# Remove last plays of drives
plays.dropna(inplace = True)

# Check if any columns have null values
drives.columns[drives.isna().any()].tolist()

del plays['game-drive']

# Double Check Output
plays.to_csv('../../data/clean/model_plays.csv', index = False)


# Separate Class from Data

# Test for run and pass predictors. Comment out if we don't want this
plays = plays[((plays['target'] == 'run') |  (plays['target'] == 'pass'))]


plays['target'] = plays['target'].astype('category').cat.codes
target_np = plays['target']
del plays['target']

data_np = plays.copy()

# Create Dummy Variables


# Split samples before normalizing data

data_train, data_test, target_train, target_test = train_test_split(data_np, target_np, test_size=0.35)

from sklearn.metrics import accuracy_score
from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report

####Classifiers####
clf = DecisionTreeClassifier(criterion='entropy', splitter='best', max_depth=None, min_samples_split=3, min_samples_leaf=1, max_features=None, random_state=None)
clf.fit(data_train, target_train)
print('Decision Tree Acc:', clf.score(data_test, target_test))


rf = RandomForestClassifier(n_estimators = 1000, max_depth = 10, min_samples_split = 25)
rf.fit(data_train, target_train)
rfpredictions = rf.predict(data_test)
print("Train Accuracy :: ", accuracy_score(target_train, rf.predict(data_train)))
print("Test Accuracy  :: ", accuracy_score(target_test, rfpredictions))
print("\n")
print("Confusion matrix: \n", confusion_matrix(target_test, rfpredictions))

rfconfusionMatrix = confusion_matrix(target_test, rfpredictions)

print(classification_report(target_test, rfpredictions))
print(rf.feature_importances_)



# Catboost
clf=CatBoostClassifier(task_type = 'GPU', silent = True)
clf.fit(data_np, target_np)
test_predictions = clf.predict(data_test)
scores_ACC = clf.score(data_test, target_test)
print("CatBoost Train Accuracy:",clf.score(data_np, target_np))
print('CatBoost Test Acc:', scores_ACC)
print(classification_report(target_test, test_predictions))       

# XGBoost
clf=xgb.XGBClassifier()
clf.fit(data_np, target_np)
test_predictions = clf.predict(data_test)
scores_ACC = clf.score(data_test, target_test)
print("XGBoost Train Accuracy:",clf.score(data_np, target_np))
print('XGBoost Test Acc:', scores_ACC)
print(classification_report(target_test, test_predictions))
