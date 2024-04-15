import pandas as pd
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split


def preprocess_data(data):
    train_val = data.copy(deep=True)

    #1. Fixing the money and percents#
    train_val['x12'] = train_val['x12'].str.replace('$','')
    train_val['x12'] = train_val['x12'].str.replace(',','')
    train_val['x12'] = train_val['x12'].str.replace(')','')
    train_val['x12'] = train_val['x12'].str.replace('(','-')
    train_val['x12'] = train_val['x12'].astype(float)
    train_val['x63'] = train_val['x63'].str.replace('%','')
    train_val['x63'] = train_val['x63'].astype(float)

    # 2. Creating the train/val/test set
    x_train, x_val, y_train, y_val = train_test_split(train_val.drop(columns=['y']), train_val['y'], test_size=0.1, random_state=13)
    x_train, x_test, y_train, y_test = train_test_split(x_train, y_train, test_size=4000, random_state=13)

    # 3. smashing sets back together
    train = pd.concat([x_train, y_train], axis=1, sort=False).reset_index(drop=True)
    val = pd.concat([x_val, y_val], axis=1, sort=False).reset_index(drop=True)
    test = pd.concat([x_test, y_test], axis=1, sort=False).reset_index(drop=True)

    # 3. With mean imputation from Train set

    imputer = SimpleImputer(missing_values = np.nan, strategy = 'mean')
    train_imputed = pd.DataFrame(imputer.fit_transform(train.drop(columns=['y', 'x5', 'x31',  'x81' ,'x82'])), columns=train.drop(columns=['y', 'x5', 'x31', 'x81', 'x82']).columns)
    std_scaler = StandardScaler()
    train_imputed_std = pd.DataFrame(std_scaler.fit_transform(train_imputed), columns=train_imputed.columns)

    # 3 create dummies

    dumb5 = pd.get_dummies(train['x5'], drop_first=True, prefix='x5', prefix_sep='_', dummy_na=True)
    train_imputed_std = pd.concat([train_imputed_std, dumb5], axis=1, sort=False)

    dumb31 = pd.get_dummies(train['x31'], drop_first=True, prefix='x31', prefix_sep='_', dummy_na=True)
    train_imputed_std = pd.concat([train_imputed_std, dumb31], axis=1, sort=False)

    dumb81 = pd.get_dummies(train['x81'], drop_first=True, prefix='x81', prefix_sep='_', dummy_na=True)
    train_imputed_std = pd.concat([train_imputed_std, dumb81], axis=1, sort=False)

    dumb82 = pd.get_dummies(train['x82'], drop_first=True, prefix='x82', prefix_sep='_', dummy_na=True)
    train_imputed_std = pd.concat([train_imputed_std, dumb82], axis=1, sort=False)
    train_imputed_std = pd.concat([train_imputed_std, train['y']], axis=1, sort=False)

    del dumb5, dumb31, dumb81, dumb82

    test_imputed = pd.DataFrame(imputer.transform(test.drop(columns=['y', 'x5', 'x31', 'x81' ,'x82'])), columns=train.drop(columns=['y','x5', 'x31', 'x81', 'x82']).columns)
    test_imputed_std = pd.DataFrame(std_scaler.transform(test_imputed), columns=train_imputed.columns)

    # 3 create dummies

    dumb5 = pd.get_dummies(test['x5'], drop_first=True, prefix='x5', prefix_sep='_', dummy_na=True)
    test_imputed_std = pd.concat([test_imputed_std, dumb5], axis=1, sort=False)

    dumb31 = pd.get_dummies(test['x31'], drop_first=True, prefix='x31', prefix_sep='_', dummy_na=True)
    test_imputed_std = pd.concat([test_imputed_std, dumb31], axis=1, sort=False)

    dumb81 = pd.get_dummies(test['x81'], drop_first=True, prefix='x81', prefix_sep='_', dummy_na=True)
    test_imputed_std = pd.concat([test_imputed_std, dumb81], axis=1, sort=False)

    dumb82 = pd.get_dummies(test['x82'], drop_first=True, prefix='x82', prefix_sep='_', dummy_na=True)
    test_imputed_std = pd.concat([test_imputed_std, dumb82], axis=1, sort=False)
    test_imputed_std = pd.concat([test_imputed_std, test['y']], axis=1, sort=False)

    test_imputed_std[variables] = test_imputed_std[variables].astype(float)

    return train_imputed_std
