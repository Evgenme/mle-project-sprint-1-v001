# scripts/fit.py
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from category_encoders import CatBoostEncoder
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from catboost import CatBoostRegressor
from sklearn.model_selection import RandomizedSearchCV
import yaml
import os
import joblib
import numpy as np

def fit_model():
    with open('params.yaml', 'r') as fd:
        params = yaml.safe_load(fd)
        
    # Загрузка данных
    data = pd.read_csv('data/initial_data.csv')
    target = data[params['target_col']]
    data = data.drop(params['drop_col'] + [params['target_col']], axis=1)
    
    # Разделение данных на числовые и категориальные признаки
    cat_features = data.select_dtypes(include='object')
    potential_binary_features = cat_features.nunique() == 2
    binary_cat_features = cat_features[potential_binary_features[potential_binary_features].index]
    other_cat_features = cat_features[potential_binary_features[~potential_binary_features].index]
    num_features = data.select_dtypes(['float', 'int'])
    
    # Предобработка данных
    preprocessor = ColumnTransformer(
        [
            ('binary', OneHotEncoder(drop=params['one_hot_drop']), binary_cat_features.columns.tolist()),
            ('cat', CatBoostEncoder(), other_cat_features.columns.tolist()),
            ('num', StandardScaler(), num_features.columns.tolist())
        ],
        remainder='drop',
        verbose_feature_names_out=False
    )
    
    # Модель CatBoost
    model = CatBoostRegressor(
        loss_function='RMSE',
        verbose=0  # Отключение вывода информации о процессе обучения для Random Search
    )
    
    # Параметры для Random Search
    param_distributions = {
        'model__iterations': [500, 1000, 1500],
        'model__learning_rate': [0.01, 0.05, 0.1],
        'model__depth': [4, 6, 8, 10],
        'model__l2_leaf_reg': [1, 3, 5, 7, 9]
    }
    
    # Пайплайн
    pipeline = Pipeline(
        [
            ('preprocessor', preprocessor),
            ('model', model)
        ]
    )
    
    # Randomized Search CV
    random_search = RandomizedSearchCV(
        estimator=pipeline,
        param_distributions=param_distributions,
        n_iter=20,  # Количество итераций Random Search
        scoring='neg_mean_squared_error',  # Оценка на основе среднеквадратичной ошибки
        cv=5,  # Кросс-валидация с 5 фолдами
        n_jobs=-1,  # Использование всех процессоров
        verbose=2,  # Вывод информации о процессе поиска
        random_state=42  # Фиксация случайного состояния для воспроизводимости
    )
    
    # Обучение модели с Random Search
    random_search.fit(data, target)
    
    # Лучшая модель
    best_model = random_search.best_estimator_
    
    # Сохранение лучшей модели
    os.makedirs('models', exist_ok=True)
    with open('models/fitted_model.pkl', 'wb') as fd:
        joblib.dump(best_model, fd)

if __name__ == '__main__':
    fit_model()