# dags/churn.py

import pendulum
from airflow.decorators import dag, task
from steps.messages import send_telegram_success_message, send_telegram_failure_message


@dag(
    schedule='@once',
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    catchup=False,
    tags=["ETL"],
    on_success_callback=send_telegram_success_message,
    on_failure_callback=send_telegram_failure_message
)
def prepare_flats_dataset():
    import pandas as pd
    import numpy as np
    from airflow.providers.postgres.hooks.postgres import PostgresHook
	
    @task()
    def create_table():
        import sqlalchemy
        from sqlalchemy import Table, MetaData, Column, Integer, String, UniqueConstraint, Float, inspect
        hook = PostgresHook('destination_db')
        db_conn = hook.get_sqlalchemy_engine()
        # Подключаемся к БД и удаляем таблицу flats_churn если такая существует
        conn = db_conn.connect()
        conn.execute("DROP TABLE IF EXISTS flats_churn")
        
        # Инициализируем таблицу flats_churn
        metadata = MetaData()
        flats_churn = Table(
            'flats_churn',
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
            UniqueConstraint('id', name='unique_flat_constraint')
            )
        
        # Создаем таблицу flats_churn
        metadata.create_all(db_conn)
        conn.close()
        
    @task()
    def extract(**kwargs):

        hook = PostgresHook('destination_db')
        conn = hook.get_conn()
        sql = f"""
        select
            f.id, f.building_id, f.floor, f.kitchen_area, f.living_area, f.rooms, f.is_apartment, f.studio, f.total_area, f.price,
            b.build_year, b.building_type_int, b.latitude, b.longitude, b.ceiling_height, b.flats_count, b.floors_total, b.has_elevator
        from flats as f
        left join buildings as b on b.id = f.building_id
        """
        data = pd.read_sql(sql, conn)
        conn.close()
        #assert len(data) != 0
        return data

    @task()
    def transform(data: pd.DataFrame) -> pd.DataFrame:
        data['price_metr'] = data['price']/data['total_area']

        return data


    @task()
    def load(data: pd.DataFrame):
        hook = PostgresHook('destination_db')
        hook.insert_rows(
            table="flats_churn",
            replace=True,
            target_fields=data.columns.tolist(),
            replace_index=['id'],
            rows=data.values.tolist()
        )
        #assert len(data) != 0

    create_table()
    data = extract()
    transformed_data = transform(data)
    load(transformed_data) 
    
prepare_flats_dataset()