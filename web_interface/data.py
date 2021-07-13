import pandas as pd
import time
import os

data_path = "../data"
try: 
    os.mkdir(data_path)
except OSError as error: 
    print(error)  
    
def save_data(data):
    '''
    Estructura mínima
    ------------------
    command     : comando enviado (en 4 bytes, coincide con el nombre del csv)
    timestamp   : timestamp al que el comando fue enviado
    type        : SEND o RECEIVE
    response    : la respuesta al comando, si type==RECEIVE

    Salida
    ------------------
    Archivo .csv con el nombre del comando enviado
    '''
    command = get_file_name(data['command'])
    timestamp = time.time()
    type = data['type']
    response = data['response'][5:] if "response" in data.keys() else ""
    new_data = pd.Series(index = ["command", "timestamp", "type", "response"],
                        data = [command, timestamp, type, response])
    try:
        df_data = pd.read_csv(f'{data_path}/{command}', index_col=0)
    except FileNotFoundError: 
        df_data = pd.DataFrame([])
    df_data = df_data.append(new_data, ignore_index=True)
    df_data.to_csv(f'{data_path}/{command}')

def get_file_name(command):
    if command.startswith("A"): return "Attt"
    if command.startswith("R"): return "Rttt"
    if command.startswith("GH"): return "GHxx"
    if command.startswith("GA"): return "GAxx"
    return command