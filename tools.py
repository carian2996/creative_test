#coding=utf-8

from __future__ import division

import numpy as np # data manipulation
import pandas as pd # data manipulation

from sklearn.tree import DecisionTreeClassifier # data transformation

from sklearn.model_selection import cross_val_score # data modeling
from sklearn.model_selection import train_test_split # data modeling
from sklearn.linear_model import LogisticRegression # data modeling

from sklearn.metrics import roc_auc_score # model performance
from sklearn.metrics import roc_curve # model performance
from sklearn.metrics import confusion_matrix # model performance
from sklearn.metrics import accuracy_score # model performance
from sklearn.metrics import average_precision_score # model performance

import matplotlib.pyplot as plt # data visualization


def what_first(bgc, vehicle):
    if (pd.isnull(bgc)) and (pd.isnull(vehicle)):
        return 'Null'
    elif (~pd.isnull(bgc)) and (pd.isnull(vehicle)):
        return 'bgc_first'
    elif (pd.isnull(bgc)) and (~pd.isnull(vehicle)):
        return 'vehicle_first'
    elif (~pd.isnull(bgc)) and (~pd.isnull(vehicle)):
        if bgc < vehicle:
            return 'vehicle_first'
        elif bgc > vehicle:
            return 'bgc_first'
        else:
            return 'same_day'

def web_mobile(channel):
    if pd.isnull(channel):
        return 'Null'
    elif 'web' in channel:
        return 'web'
    else:
        return 'mobile'

def iv(X, target):
    
    binary = target.name
    feat = X.name
    df = X.to_frame().reset_index(drop=True)
    target = target.to_frame().reset_index(drop=True)
    df = df.merge(target, left_index=True, right_index=True, how='inner')
    iv_df = df.copy()
    iv_df['NS'] = (iv_df[binary] == 0).astype(int)
    iv_df['S'] = (iv_df[binary] == 1).astype(int)
    iv_df = iv_df[['NS', 'S', feat]]
    iv_df = iv_df.groupby(feat).sum()
    iv_df['NS'] = iv_df['NS'] / iv_df['NS'].sum()
    iv_df['S'] = iv_df['S'] / iv_df['S'].sum()
    iv_df['W'] = np.log(iv_df['NS'] / iv_df['S'])
    iv_df['I'] = iv_df['W'] * (iv_df['NS'] - iv_df['S'])
    
    return iv_df['I'].sum()

def woe_transformation(df, features, target):
    
    df = df.copy()

    if type(features) is not list:
        features = [features]

    for feat in features:
        iv_df = df[[feat, target]].copy()
        iv_df['NS'] = (iv_df[target] == 0).astype(int)
        iv_df['S'] = (iv_df[target] == 1).astype(int)
        iv_df = iv_df[['NS', 'S', feat]]
        iv_df = iv_df.groupby(feat).sum()
        iv_df['NS'] = iv_df['NS'] / iv_df['NS'].sum()
        iv_df['S'] = iv_df['S'] / iv_df['S'].sum()
        iv_df['W'] = np.log(iv_df['S'] / iv_df['NS'])
        iv_df[feat] = iv_df.index
        df = df.merge(iv_df[[feat, 'W']], on=feat, how='left')
        df.rename(columns={'W': 'W_' + feat}, inplace=True)
    
    return df

def binning_opt(X, y, depth):
    
    var_name = X.name
    df = X.to_frame()
    target_df = y.to_frame()
    missing_df = df[df[var_name].isnull()]

    df = df.merge(missing_df, left_index=True, right_index=True, how='outer', indicator=True)
    df = df[df['_merge'] == 'left_only']
    df.drop([var_name + '_y', '_merge'], axis=1, inplace=True)
    df.rename(columns={var_name + '_x': var_name}, inplace=True)

    target_df = target_df.merge(missing_df, left_index=True, right_index=True, how='outer',
                                                indicator=True)
    target_df = target_df[target_df['_merge'] == 'left_only']
    target_df.drop([var_name, '_merge'], axis=1, inplace=True)
    dt = DecisionTreeClassifier(max_features=1, max_depth=depth, min_samples_leaf=0.1)
    dt.fit(df, target_df)
    df['nodo'] = dt.apply(df)
    df['nodo'] = df['nodo'].astype(str)
    bins = df.groupby('nodo').agg(['min', 'max'])[var_name]
    bins.sort_values('min', inplace=True)
    bins['min2'] = bins['max'].shift(1)
    bins['min'] = np.where(bins['min2'].isnull(), bins['min'], bins['min2'])
    bins.reset_index(inplace=True)
    bins['id'] = (bins.index + 1).map(lambda x: '0' + str(x) if x < 10 else str(x))
    bins['C_' + var_name] = bins['id'] + '. (' + bins['min'].astype(str) + ", " + bins['max'].astype(str) + "]"
    bins = bins[['nodo', 'C_' + var_name]]
    df['in'] = df.index
    df = df.merge(bins, how='inner', on='nodo')
    df.index = df['in']
    df.sort_index(inplace=True)
    df.drop(['in', 'nodo'], axis=1, inplace=True)

    missing_df['C_' + var_name] = 'Null'
    missing_df['in'] = missing_df.index
    missing_df.index = missing_df['in']
    missing_df.drop('in', axis=1, inplace=True)
    df = pd.concat([df, missing_df]).sort_index()
    df.index.name = None
    return df['C_' + var_name]

def discretize_opt(df, features, target, iv_threshold=0.6, verbose=True):
   
    df_final = df.copy()
    if type(features) is not list:
        features = [features]
    for feature in features:
        if verbose:
            print "fitting best number of bins for feature %s ..." % feature
        best_iv_k = 1
        best_iv = 0.1
        aux = df[[feature, target]].copy()
        for k in range(2, 11):
            iv_st = iv(binning_opt(aux[feature], aux[target], k), aux[target])
            if (iv_st > best_iv) and (iv_st != np.inf) and (iv_st <= iv_threshold):
                best_iv = iv_st
                best_iv_k = k
        if verbose:
            print "best number of bins encountered: %d with iv %4.2f " % (best_iv_k, best_iv)
        df_final['C_' + feature] = binning_opt(aux[feature], aux[target], best_iv_k)
    return df_final

def plot_roc_curve(df, features, target, logreg, train_size=0.7):
    
    X = df[features]
    y = df[target]
    Xt, Xv, yt, yv = train_test_split(X, y, train_size=train_size)
    plt.figure()
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.0])
    ax = plt.subplot('111')
    ax.set_title("ROC Curve")

    y_pred = logreg.predict_proba(Xt)[:, 1]
    fpr, tpr, thresholds = roc_curve(yt, y_pred)
    plt.plot(fpr, tpr, label='%s %4.3f' % ('training', roc_auc_score(yt, y_pred)))

    y_pred = logreg.predict_proba(Xv)[:, 1]
    fpr, tpr, thresholds = roc_curve(yv, y_pred)
    plt.plot(fpr, tpr, label='%s %4.3f' % ('validation', roc_auc_score(yv, y_pred)))

    plt.plot([0, 1], [0, 1], color='red', label='Reference Line')
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
