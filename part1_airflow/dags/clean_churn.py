# dags/clean_churn.py

import pendulum
from airflow.decorators import dag, task

@dag(
    schedule='@once',
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    catchup=False,
    tags=["ETL"]
)
def clean_flats_dataset():
    import pandas as pd
    import numpy as np
    from airflow.providers.postgres.hooks.postgres import PostgresHook
    @task()
    def create_table():
        from sqlalchemy import Table, Column, DateTime, Float, Integer, Index, MetaData, String, UniqueConstraint, inspect
        hook = PostgresHook('destination_db')
        db_engine = hook.get_sqlalchemy_engine()
        conn = db_engine.connect()  # Получаем объект соединения для выполнения запросов

        # Исполнение SQL-команды для удаления таблицы, если она существует
        conn.execute("DROP TABLE IF EXISTS clean_flats_churn")

        metadata = MetaData()

        churn_table = Table(
            'clean_flats_churn',
            metadata,
            Column('id_key', Integer, primary_key=True, autoincrement=True),
            Column('id', String),
            Column('building_id', String),
            Column('floor', Integer),
            Column('kitchen_area', Float),
            Column('living_area', Float),
            Column('rooms', Integer),
            Column('is_apartment', String),
            Column('studio', String),
            Column('total_area', Float),
            Column('price', Float),
            Column('build_year', Integer),
            Column('building_type_int', String),
            Column('latitude', Float),
            Column('longitude', Float),
            Column('ceiling_height', Float),
            Column('flats_count', Integer),
            Column('floors_total', Integer),
            Column('has_elevator', String),
            Column('price_metr', Float),
            UniqueConstraint('id', name='unique_clean_flat_constraint')
        )

        metadata.create_all(db_engine)
        conn.close()
    
    @task()
    def extract(**kwargs):
        hook = PostgresHook('destination_db')
        conn = hook.get_conn()
        sql = 'select * from flats_churn'
        data = pd.read_sql(sql, conn)
        conn.close()
        return data

    @task()
    def transform(data: pd.DataFrame):
        # удаление дубликатов
        feature_cols = ['building_id', 'floor', 'kitchen_area', 'living_area', 'rooms', 'is_apartment', 'studio', 'total_area', 'price', 'build_year',
                'building_type_int', 'latitude', 'longitude', 'ceiling_height', 'flats_count', 'floors_total', 'has_elevator']
        is_duplicated_features = data.duplicated(subset=feature_cols, keep=False)
        data = data[~is_duplicated_features].reset_index(drop=True)

        # устранение аномальных выбросов по высоте потолка
        data.loc[data['ceiling_height'] >= 20, 'ceiling_height'] /= 10
        # устранение аномальных выбросов по этажности дома
        data['floors_total'] = np.ceil(data.groupby(['latitude', 'longitude'])['floors_total'].transform("median"))
        # удаление несоответствий суммарной площади объекта 
        condition = data['kitchen_area']+data['living_area'] > data['total_area']
        data = data[~condition]
        # удаление объектов с нулевыми значениями по жилой и кухонной зоне
        condition = (data['living_area'] == 0) & (data['kitchen_area'] == 0)
        data = data[~condition]
        # удаление аномальных выбросов по стоимости объекта
        condition = (data['price_metr'] <= 80000) | (data['price_metr'] >= 1200000)
        data = data[~condition]
        # удаление аномальных выбросов по количеству квартир
        condition = (data['flats_count'] > 1700)
        data = data[~condition]

        return data

    @task()
    def load(data: pd.DataFrame):
        hook = PostgresHook('destination_db')
        hook.insert_rows(
            table="clean_flats_churn",
            replace=True,
            target_fields=data.columns.tolist(),
            replace_index=['id'],
            rows=data.values.tolist()
        )

    
    create_table()
    data = extract()
    transformed_data = transform(data)
    load(transformed_data)
    

clean_flats_dataset()