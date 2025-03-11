# -*- coding: utf-8 -*-
"""Untitled37.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1rfIty2xr04StxKdItR0hVVAWnVhsUf7g
"""

from flask import Flask, request, send_file, jsonify
from obspy import read
import requests
import io
import datetime
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Para evitar problemas de GUI en entornos sin pantalla
from flask_cors import CORS  # Habilitar CORS para todas las rutas

app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas las rutas

# Directorio de Estaciones de REDNE y sus canales
station_channels = {
    'UIS01': ['HNE', 'HNN', 'HNZ'],
    'UIS03': ['HNE', 'HNN', 'HNZ'],
    'UIS04': ['HNE', 'HNN', 'HNZ'], 
    'UIS05': ['EHZ', 'ENE', 'ENN', 'ENZ'], 
    'UIS06': ['EHE', 'EHN', 'EHZ'],
    'UIS09': ['EHE', 'EHN', 'EHZ'], 
    'UIS10': ['EHE', 'EHN', 'EHZ'],
    'UIS11': ['EHE', 'EHN', 'EHZ'], 
}

# Función auxiliar para calcular la diferencia de tiempo
def calculate_time_difference(start, end):
    start_time = datetime.datetime.fromisoformat(start)
    end_time = datetime.datetime.fromisoformat(end)
    return (end_time - start_time).total_seconds() / 60  # Diferencia en minutos

# Función para generar el helicorder
def generate_helicorder_logic(net, sta, loc, cha, start, end):
    try:
        print(f"Generando helicorder para: {sta}, Canal: {cha}, {start} - {end}")

        # URL de la solicitud para obtener los datos del helicorder
        url = f"http://osso.univalle.edu.co/fdsnws/dataselect/1/query?starttime={start}&endtime={end}&network={net}&station={sta}&location={loc}&channel={cha}&nodata=404"
        print(f"URL de solicitud para el helicorder: {url}")
        
        # Calcular el intervalo de tiempo entre el inicio y el fin
        interval_minutes = calculate_time_difference(start, end)
        
        # Ajustar el tiempo de espera en función del intervalo
        if interval_minutes >= 420:  # Si el intervalo es mayor a 7 horas (420 minutos)
            timeout = 60  # Tiempo de espera de 60 segundos para intervalos largos (7 horas)
        else:
            timeout = 10  # Tiempo de espera de 10 segundos para intervalos cortos (menores de 7 horas)

        print(f"Tiempo de espera para la solicitud: {timeout} segundos")

        # Realizar la solicitud HTTP con el timeout ajustado
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            raise Exception(f"Error al descargar datos del helicorder: {response.status_code}")
        print(f"Datos descargados correctamente para el helicorder, tamaño de los datos: {len(response.content)} bytes")
        
        # Procesar los datos MiniSEED para el helicorder
        mini_seed_data = io.BytesIO(response.content)
        st = read(mini_seed_data)
        print(f"Datos MiniSEED procesados correctamente para el helicorder")
        
        # Crear el helicorder utilizando ObsPy
        fig = st.plot(
            type="dayplot",
            interval=15,
            right_vertical_labels=True,
            vertical_scaling_range=2000,
            color=['k', 'r', 'b'],
            show_y_UTC_label=True,
            one_tick_per_line=True
        )
        
        # Ajustar el tamaño del helicorder
        fig.set_size_inches(12, 4)  # Configura el tamaño del gráfico (ancho x alto)
        
        # Guardar el gráfico del helicorder en memoria
        output_image = io.BytesIO()
        fig.savefig(output_image, format='png', dpi=120, bbox_inches="tight")
        output_image.seek(0)
        plt.close(fig)

        print(f"Helicorder generado para la estación {sta}")
        
        return send_file(output_image, mimetype='image/png')
    
    except Exception as e:
        print(f"Error al generar el helicorder: {str(e)}")
        return jsonify({"error": f"Ocurrió un error: {str(e)}"}), 500

# Función auxiliar para generar el sismograma combinado
def generate_sismograma_engrupo(net, sta, loc, start, end):
    try:
        print(f"Generando sismograma combinado para: {sta}, {start} - {end}")
        # Obtener los canales asociados a la estación
        selected_channels = station_channels.get(sta, [])
        if not selected_channels:
            return jsonify({"error": "No se encontraron canales para la estación seleccionada"}), 400
        
        # Crear una figura para el gráfico conjunto
        fig, axs = plt.subplots(len(selected_channels), 1, figsize=(10, 6 * len(selected_channels)))
        if len(selected_channels) == 1:
            axs = [axs]  # Asegurar que axs sea iterable incluso si solo hay un canal
        
        # Iterar sobre los canales y generar el gráfico para cada uno
        for i, cha in enumerate(selected_channels):
            print(f"Generando gráfico para el canal: {cha}")
            url = f"http://osso.univalle.edu.co/fdsnws/dataselect/1/query?starttime={start}&endtime={end}&network={net}&station={sta}&location={loc}&channel={cha}&nodata=404"
            print(f"URL de solicitud para el canal {cha}: {url}")
            
            # Realizar la solicitud HTTP para obtener los datos
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                raise Exception(f"Error al descargar datos del canal {cha}: {response.status_code}")
            print(f"Datos descargados correctamente para el canal {cha}, tamaño de los datos: {len(response.content)} bytes")
            
            # Procesar los datos MiniSEED
            mini_seed_data = io.BytesIO(response.content)
            st = read(mini_seed_data)
            print(f"Datos MiniSEED procesados correctamente para el canal {cha}")
            
            # Crear el gráfico del sismograma para cada canal
            tr = st[0]
            start_time = tr.stats.starttime.datetime
            times = [start_time + datetime.timedelta(seconds=sec) for sec in tr.times()]
            data = tr.data
            
            # Generar gráfico en el eje correspondiente de la figura
            axs[i].plot(times, data, linewidth=0.8)
            axs[i].set_title(f"Universidad Industrial de Santander UIS \n Red Sísmica REDNE \n Sismograma {cha} ({sta}) \n {start} - {end}")
            axs[i].set_xlabel("Tiempo (UTC Colombia)")
            axs[i].set_ylabel("Amplitud (M/s)")
            axs[i].grid(True)
            axs[i].tick_params(axis='x', rotation=45)
        
        # Ajustar el espacio entre los subgráficos
        fig.tight_layout(pad=2.0)
        
        # Guardar el gráfico combinado en memoria
        output_image = io.BytesIO()
        plt.savefig(output_image, format='png', dpi=100, bbox_inches="tight")
        output_image.seek(0)
        plt.close(fig)
        
        print(f"Sismograma combinado generado para la estación {sta}")
        
        # Devolver la imagen generada
        return send_file(output_image, mimetype='image/png')
    
    except Exception as e:
        print(f"Error al generar el sismograma combinado: {str(e)}")
        return jsonify({"error": f"Ocurrió un error: {str(e)}"}), 500

# Ruta de Flask para manejar solicitudes de sismogramas y helicorders
@app.route('/generate_sismograma', methods=['GET'])
def generate_sismograma():
    try:
        # Obtener parámetros de la solicitud
        start = request.args.get('start')
        end = request.args.get('end')
        net = request.args.get('net')
        sta = request.args.get('sta')
        loc = request.args.get('loc')
        cha = request.args.get('cha')
        
        # Verificar que todos los parámetros estén presentes
        if not all([start, end, net, sta, loc, cha]):
            return jsonify({"error": "Faltan parámetros requeridos"}), 400
        
        # Verificar si la estación es válida
        if sta not in station_channels:
            return jsonify({"error": "Estación no válida"}), 400
        
        # Calcular la diferencia de tiempo para decidir el tipo de gráfico
        interval_minutes = calculate_time_difference(start, end)
        if interval_minutes <= 15:
            return generate_sismograma_engrupo(net, sta, loc, start, end)
        else:
            return generate_helicorder_logic(net, sta, loc, cha, start, end)
    
    except Exception as e:
        return jsonify({"error": f"Ocurrió un error: {str(e)}"}), 500

# Punto de entrada del servidor Flask
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)








