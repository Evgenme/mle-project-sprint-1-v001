from airflow.providers.telegram.hooks.telegram import TelegramHook # импортируем хук телеграма

def send_telegram_success_message(context): # на вход принимаем словарь со контекстными переменными
    hook = TelegramHook(telegram_conn_id='test',
                        token='{вставьте ваш token_id}',
                        chat_id='{вставьте ваш chat_id}')
    dag = context['dag']
    run_id = context['run_id']
    
    message = f'Исполнение DAG {dag} с id={run_id} прошло успешно!'
    hook.send_message({
        'chat_id': '{вставьте ваш chat_id}',
        'text': message
    })

def send_telegram_failure_message(context):
    
    hook = TelegramHook(telegram_conn_id='test',
                        token='{вставьте ваш token_id}',
                        chat_id='{вставьте ваш chat_id}')
    
    run_id = context['run_id']
    task_instance_key_str = context['task_instance_key_str']
    
    message = f'Исполнение DAG  с id={run_id} прошло неудачно! ключь ошибки {task_instance_key_str}'
    hook.send_message({
        'chat_id': '{вставьте ваш chat_id}',
        'text': message
    }) 