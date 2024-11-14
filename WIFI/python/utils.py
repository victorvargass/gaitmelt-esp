import pandas as pd
import matplotlib.pyplot as plt
import csv
import struct
import concurrent.futures
import time
import os
import socket
import queue
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import numpy as np
from datetime import datetime
import tkinter as tk

class VibracionContinua:
    def __init__(
        self,
        local_udp_ip,
        shared_port,
        esp_ips,
        struct_format,
        output_folder,
        output_filename,
        motor_power,
    ):
        self.local_udp_ip = local_udp_ip
        self.shared_port = shared_port
        self.num_esps = 4
        self.esp_indexes = [1, 2, 3, 4]
        self.esp_ips = esp_ips
        self.struct_format = struct_format
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.output_folder = output_folder
        self.output_filename = output_filename
        self.motor_power = motor_power
        self.max_time_sync_diff = 50  # Máxima diferencia de tiempo permitida (8 ms)
        self.vibration_duration = 3600000 # tiempo maximo de vibracion

        # Estado de grabación
        self.recording = False
        self.recorded_data = []
        self.start_time = None
        self.buffers = [[] for _ in range(self.num_esps)]
        self.sock = self.setup_socket(local_udp_ip, shared_port)

        self.data_queue = queue.Queue()
        self.esp_data = [None] * self.num_esps
        self.last_received = [None] * self.num_esps

    def setup_socket(self, local_ip, shared_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((local_ip, shared_port))
            return sock
        except Exception as e:
            print(e)

    def save_data_to_csv(self):
        with open(self.output_folder + "/" + self.output_filename + "/" + "recorded_data.csv", "w", newline="") as csvfile:
            csvwriter = csv.writer(csvfile)
            header = ["elapsed_time"]
            for i in self.esp_indexes:
                header.extend(
                    [
                        f"ts_{i}",
                        f"acc_x_{i}",
                        f"acc_y_{i}",
                        f"acc_z_{i}",
                        f"gyr_x_{i}",
                        f"gyr_y_{i}",
                        f"gyr_z_{i}",
                    ]
                )
            csvwriter.writerow(header)
            csvwriter.writerows(self.recorded_data)

    def clean_and_rename_csv(self):
        df = pd.read_csv(f"{self.output_folder}/{self.output_filename}/recorded_data.csv", delimiter=",")
        # Definir columnas de timestamp y número de filas iniciales a revisar
        timestamp_columns = ["ts_1", "ts_2", "ts_3", "ts_4"]
        initial_rows_count = 20
        timestamp_threshold = 500  # El umbral para detectar valores anómalos en las primeras filas
        
        for column in timestamp_columns:
            df = df.drop_duplicates(subset=[column])

        initial_df = df.head(initial_rows_count)

        anomaly_mask = (initial_df[timestamp_columns] > timestamp_threshold).any(axis=1)
        filtered_initial_df = initial_df[~anomaly_mask]

        remaining_df = df.iloc[initial_rows_count:]

        df = pd.concat([filtered_initial_df, remaining_df], ignore_index=True)

        umbral = 500
        df['diff_ts_1'] = df['ts_1'].diff()
        wrong_ts_idx = df[df['diff_ts_1'].abs() > umbral].index
        if not wrong_ts_idx.empty:
            idx_to_delete= wrong_ts_idx[0]
            df = df.iloc[:idx_to_delete]
        df = df.drop(columns=['diff_ts_1'])

        df.insert(0, "index", range(len(df)))

        output_filename = "Datos.csv"
        df.to_csv(f"{self.output_folder}/{self.output_filename}/{output_filename}", index=False)

        return output_filename

    def process_data(self, data):
        # Verificamos si la grabación ha comenzado, reiniciando los buffers y otros valores
        if self.start_time is None:
            # Reiniciar el tiempo de inicio y otros valores necesarios
            self.start_time = time.time()
            self.init_time = datetime.now().strftime("%H:%M:%S")
            self.data_queue = queue.Queue()
            self.buffers = [[] for _ in range(self.num_esps)]  # Reiniciar los buffers
        if self.recording:
            elapsed_time = time.time() - self.start_time

            for esp_id in self.esp_indexes:
                if data[esp_id - 1] is not None:
                    self.buffers[esp_id - 1].append(data[esp_id - 1])

            while all(self.buffers):
                record_entry = [elapsed_time]
                for esp_id in self.esp_indexes:
                    synchronized_data = self.buffers[esp_id - 1].pop(0)
                    record_entry.extend(
                        [
                            synchronized_data[7],
                            synchronized_data[1],
                            synchronized_data[2],
                            synchronized_data[3],
                            synchronized_data[4],
                            synchronized_data[5],
                            synchronized_data[6],
                        ]
                    )
                self.recorded_data.append(record_entry)

    def all_devices_active(self, current_time):
        for last_time in self.last_received:
            if last_time is None or (current_time - last_time) > 2:
                return False
        return True

    def display_data(self, data, label_texts, record_with_vibration_button, record_without_vibration_button):
        current_time = time.time()
        all_active = self.all_devices_active(current_time)
        
        record_state = "normal" if all_active else "disabled"
        record_with_vibration_button.config(state=record_state)
        record_without_vibration_button.config(state=record_state)

        for esp_id in self.esp_indexes:
            if data[esp_id - 1] is None or \
            self.last_received[esp_id - 1] is None or \
            (current_time - self.last_received[esp_id - 1]) > 2:
                label_texts[esp_id - 1].set(f"Board {esp_id} no conectada")
            else:
                board_id = data[esp_id - 1][0]
                label_texts[esp_id - 1].set(
                    f"Board ID: {board_id}\n"
                    f"  Acc      Gyr\n"
                    f"X  {round(data[esp_id - 1][1], 2):<7}   {round(data[esp_id - 1][4], 2):<7}\n"
                    f"Y  {round(data[esp_id - 1][2], 2):<7}   {round(data[esp_id - 1][5], 2):<7}\n"
                    f"Z  {round(data[esp_id - 1][3], 2):<7}   {round(data[esp_id - 1][6], 2):<7}\n"
                    f"Timestamp: {data[esp_id - 1][7]}"
                )

    def is_synchronized(self, data):
        timestamps = [reading[7] for reading in data if reading is not None]
        
        if len(timestamps) < len(self.esp_indexes):
            return False  # No todos los dispositivos han enviado datos aún

        min_ts = min(timestamps)
        max_ts = max(timestamps)
        
        # Definir un máximo de diferencia entre los timestamps para considerar que están sincronizados
        if max_ts - min_ts <= self.max_time_sync_diff:
            return True
        else:
            return False

    def receive_data(self):
        while True:
            try:
                data, _ = self.sock.recvfrom(1024)
                if len(data) == struct.calcsize(self.struct_format):
                    readings = struct.unpack(self.struct_format, data)
                    esp_id = readings[0]
                    self.esp_data[esp_id - 1] = readings
                    self.last_received[esp_id - 1] = time.time()  # Registrar la hora de recepción

                    if self.recording:
                        # Primero verificar si los dispositivos están sincronizados
                        if self.is_synchronized(self.esp_data):
                            # Si están sincronizados, enviamos los datos a la cola y los procesamos
                            self.data_queue.put(self.esp_data.copy())  # Agregar los datos a la cola
                            data = self.data_queue.get()  # Extraer los datos de la cola
                            self.process_data(data)  # Procesar los datos
                        else:
                            # Si no están sincronizados, esperamos un poco antes de intentar de nuevo
                            continue
            except:
                self.setup_socket(self.local_udp_ip, self.shared_port)

    def update_gui(self, label_texts, root, record_with_vibration_button, record_without_vibration_button):
        try:
            if root.winfo_exists():
                # Llama a display_data para actualizar la interfaz
                self.display_data(self.esp_data, label_texts, record_with_vibration_button, record_without_vibration_button)
                # Programa la próxima actualización sin necesidad de while True
                root.after(10, self.update_gui, label_texts, root, record_with_vibration_button, record_without_vibration_button)
            else:
                root.quit()  # Cierra la aplicación correctamente
        except Exception as e:
            print(f"Se produjo un error: {e}")
            root.quit()  # En caso de cualquier error, cerrar la aplicación

    def reinitialize_gaitmelt_variables(self):
        self.recorded_data = []
        self.start_time = None
        self.buffers = [[] for _ in range(self.num_esps)]

    def stop_recording(self, record_button, vibration):
        self.save_data_to_csv()
        final_csv_filename = self.clean_and_rename_csv()
        self.plot_acc_data(final_csv_filename)
        os.remove(self.output_folder + "/" + self.output_filename + "/" + "recorded_data.csv")
        if vibration:
            button_text = "Iniciar registro con vibración"
        else:
            button_text = "Iniciar registro sin vibración"
        record_button.config(text=button_text, bg="green", fg="white")

    def init_recording(self, record_button):
        record_button.config(text="Detener registro", bg="red", fg="white")

    def exit_app(self, root):
        root.quit()  # Cerrar la aplicación

    def show_result_dialog(self, root):
        root.withdraw()  # Ocultar la ventana principal

        # Crear una ventana principal
        window = tk.Tk()
        
        #window.overrideredirect(True)  # Elimina los bordes y botones estándar
        window.protocol("WM_DELETE_WINDOW", lambda: None)

        # Ajustar el tamaño de la ventana
        window.geometry("400x400")  # Aumenta el tamaño de la ventana
        
        # Establecer el título de la ventana
        window.title("Registro Finalizado")
        window.resizable(False, False)  # Permite redimensionar la ventana
        
        # Calcular la posición para centrar la ventana en la pantalla
        screen_width = window.winfo_screenwidth()  # Ancho de la pantalla
        screen_height = window.winfo_screenheight()  # Altura de la pantalla
        
        # Obtener las dimensiones de la ventana
        window_width = 600  # Ancho de la ventana
        window_height = 200  # Altura de la ventana
        
        # Calcular las coordenadas para centrar la ventana
        position_top = int(screen_height / 2 - window_height / 2)
        position_left = int(screen_width / 2 - window_width / 2)
        
        # Establecer la posición de la ventana
        window.geometry(f"{window_width}x{window_height}+{position_left}+{position_top}")
        
        # Crear un label (etiqueta) para el mensaje inicial
        message1 = "El registro ha finalizado con éxito.\nLos archivos han quedado guardados en:"
        label1 = tk.Label(window, text=message1, font=("Segoe UI", 20), padx=20, pady=20, justify="center")
        label1.pack(expand=True)

        # Crear un label (etiqueta) para la ruta en negrita
        message2 = f"{self.output_folder}{self.output_filename}/"
        label2 = tk.Label(window, text=message2, font=("Segoe UI", 20, "bold"), padx=20, pady=10, justify="center")
        label2.pack(expand=True)

        # Botón para cerrar la ventana
        continue_button = tk.Button(
            window, 
            text="Continuar", 
            command=lambda: self.close_dialog_and_reopen(window, root), 
            font=("Arial", 12),
            bg="green", 
            fg="white",
        )
        continue_button.pack(side="left", padx=20, pady=10)

        # Botón para cerrar la ventana
        close_button = tk.Button(
            window, 
            text="Salir", 
            command=lambda: self.exit_app(root), 
            font=("Arial", 12),
            bg="red", 
            fg="white",
        )
        close_button.pack(side="right", padx=20, pady=10)
        

    def close_dialog_and_reopen(self, window, root):
        window.destroy()
        root.deiconify()
    
    # Función que hace parpadear el círculo
    def blink_circle(self, canvas, circle, root):
        current_color = canvas.itemcget(circle, "fill")
        new_color = "white" if current_color == "red" else "red"
        canvas.itemconfig(circle, fill=new_color)
        root.after(1000, self.blink_circle, canvas, circle, root)


    def toggle_recording(self, record_button, another_record_button, vibration, back_button, exit_button, canvas, circle, root):
        self.sync_devices()
        if self.recording:
            if vibration:
                self.stop_selected_motors(self.esp_indexes)
            self.show_result_dialog(root)
            self.recording = False
            self.stop_recording(record_button, vibration)
            canvas.itemconfig(circle, state="hidden")  # Ocultar el círculo
            another_record_button.config(state="normal")
            back_button.config(state="normal")
            exit_button.config(state="normal")
        else:
            self.recording = True
            if not os.path.exists(self.output_folder + "/" + self.output_filename):
                os.makedirs(self.output_folder + "/" + self.output_filename)
            self.init_recording(record_button)
            if vibration:
                self.activate_selected_motors(self.esp_indexes)
            canvas.itemconfig(circle, state="normal")  # Ocultar el círculo
            another_record_button.config(state="disabled")
            back_button.config(state="disabled")
            exit_button.config(state="disabled")
            self.blink_circle(canvas, circle, root)  # Iniciar el parpadeo
        self.reinitialize_gaitmelt_variables()

    def send_esp_message(self, IP, message):
        try:
            self.sock.sendto(message.encode(), (IP, self.shared_port))
        except Exception as e:
            print(f"Error sending message {message} to {IP}: {e}")

    def sync_devices(self):
        self.set_selected_motors_motor_power()
        self.set_selected_motors_vibration_time()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.send_esp_message, self.esp_ips[esp], "reset")
                for esp in self.esp_indexes
            ]
            concurrent.futures.wait(futures)

    def set_selected_motors_vibration_time(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self.send_esp_message,
                    self.esp_ips[esp],
                    "duration" + str(self.vibration_duration),
                )
                for esp in self.esp_indexes
            ]
            concurrent.futures.wait(futures)

    def activate_selected_motors(self, selected_esp_indexes):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self.send_esp_message,
                    self.esp_ips[esp],
                    "motor0",
                )
                for esp in selected_esp_indexes
            ]
            concurrent.futures.wait(futures)

    def stop_selected_motors(self, selected_esp_indexes):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self.send_esp_message,
                    self.esp_ips[esp],
                    "stop",
                )
                for esp in selected_esp_indexes
            ]
            concurrent.futures.wait(futures)

    def set_selected_motors_motor_power(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self.send_esp_message,
                    self.esp_ips[esp],
                    "power" + str(int(self.motor_power)),
                )
                for esp in self.esp_indexes
            ]
            concurrent.futures.wait(futures)

    def update_output_filename(self, event):
        new_output_filename = event.widget.get()
        self.output_filename = new_output_filename


    def plot_acc_data(self, csv_filename):
        # Lee el archivo CSV
        accSetColors = ["red", "blue", "green"]

        acc_y_lims = (-25, 25)

        try:
            df = pd.read_csv(self.output_folder + "/" + self.output_filename + "/" +  csv_filename, sep=",")
        except FileNotFoundError:
            print("Error: Archivo no encontrado.")
            return

        fig, axs = plt.subplots(
            2, 2, figsize=(12, 8), sharex="col", sharey="row"
        )

        sensor_titles = [
            "Sensor 1 - Muslo Izquierdo",
            "Sensor 2 - Muslo Derecho",
            "Sensor 3 - Gemelo Izquierdo",
            "Sensor 4 - Gemelo Derecho",
        ]

        # Plot para acc_data
        axs[0, 0].plot(df["elapsed_time"], df["acc_x_1"], label="x", color=accSetColors[0])
        axs[0, 0].plot(df["elapsed_time"], df["acc_y_1"], label="y", color=accSetColors[1])
        axs[0, 0].plot(df["elapsed_time"], df["acc_z_1"], label="z", color=accSetColors[2])
        axs[0, 0].set_title(f"{sensor_titles[0]}")
        axs[0, 0].set_ylabel("Aceleración")
        axs[0, 0].legend(loc="lower left")
        axs[0, 0].set_ylim(acc_y_lims)

        axs[0, 1].plot(df["elapsed_time"], df["acc_x_2"], label="x", color=accSetColors[0])
        axs[0, 1].plot(df["elapsed_time"], df["acc_y_2"], label="y", color=accSetColors[1])
        axs[0, 1].plot(df["elapsed_time"], df["acc_z_2"], label="z", color=accSetColors[2])
        axs[0, 1].set_title(f"{sensor_titles[1]}")
        axs[0, 1].set_ylabel("Aceleración")
        axs[0, 1].legend(loc="lower left")
        axs[0, 1].set_ylim(acc_y_lims)

        axs[1, 0].plot(df["elapsed_time"], df["acc_x_3"], label="x", color=accSetColors[0])
        axs[1, 0].plot(df["elapsed_time"], df["acc_y_3"], label="y", color=accSetColors[1])
        axs[1, 0].plot(df["elapsed_time"], df["acc_z_3"], label="z", color=accSetColors[2])
        axs[1, 0].set_title(f"{sensor_titles[2]}")
        axs[1, 0].set_ylabel("Aceleración")
        axs[1, 0].legend(loc="lower left")
        axs[1, 0].set_ylim(acc_y_lims)

        axs[1, 1].plot(df["elapsed_time"], df["acc_x_4"], label="x", color=accSetColors[0])
        axs[1, 1].plot(df["elapsed_time"], df["acc_y_4"], label="y", color=accSetColors[1])
        axs[1, 1].plot(df["elapsed_time"], df["acc_z_4"], label="z", color=accSetColors[2])
        axs[1, 1].set_title(f"{sensor_titles[3]}")
        axs[1, 1].set_ylabel("Aceleración")
        axs[1, 1].legend(loc="lower left")
        axs[1, 1].set_ylim(acc_y_lims)

        fig.supxlabel("Tiempo [s]")

        # Ajustar el diseño
        suptitle = self.output_filename

        plt.suptitle(suptitle)
        plt.tight_layout()
        plt.savefig(
            self.output_folder + "/" + self.output_filename + "/" + "Gráficas.png"
        )  # Guardar el gráfico como una imagen PNG

    def plot_data(self, csv_filename):
        # Lee el archivo CSV
        accSetColors = ["red", "blue", "green"]
        gyrSetColors = ["purple", "orange", "pink"]

        acc_y_lims = (-25, 25)
        gyr_y_lims = (-10, 10)

        try:
            df = pd.read_csv(self.output_folder + "/" + self.output_filename + "/" +  csv_filename, sep=",")
        except FileNotFoundError:
            print("Error: Archivo no encontrado.")
            return

        fig, axs = plt.subplots(
            self.num_esps, 2, figsize=(12, 8), sharex="col", sharey="row"
        )

        sensor_titles = [
            "Sensor 1 - Muslo Izquierdo",
            "Sensor 2 - Muslo Derecho",
            "Sensor 3 - Gemelo Izquierdo",
            "Sensor 4 - Gemelo Derecho",
        ]

        # Plot para acc_data
        axs[0, 0].plot(df["ts_1"], df["acc_x_1"], label="x", color=accSetColors[0])
        axs[0, 0].plot(df["ts_1"], df["acc_y_1"], label="y", color=accSetColors[1])
        axs[0, 0].plot(df["ts_1"], df["acc_z_1"], label="z", color=accSetColors[2])
        axs[0, 0].set_title(f"{sensor_titles[0]}")
        axs[0, 0].set_ylabel("Aceleración")
        axs[0, 0].legend(loc="lower left")
        axs[0, 0].set_ylim(acc_y_lims)

        axs[0, 1].plot(df["ts_1"], df["acc_x_2"], label="x", color=accSetColors[0])
        axs[0, 1].plot(df["ts_1"], df["acc_y_2"], label="y", color=accSetColors[1])
        axs[0, 1].plot(df["ts_1"], df["acc_z_2"], label="z", color=accSetColors[2])
        axs[0, 1].set_title(f"{sensor_titles[1]}")
        axs[0, 1].set_ylabel("Aceleración")
        axs[0, 1].legend(loc="lower left")
        axs[0, 1].set_ylim(acc_y_lims)

        axs[1, 0].plot(df["ts_1"], df["acc_x_3"], label="x", color=accSetColors[0])
        axs[1, 0].plot(df["ts_1"], df["acc_y_3"], label="y", color=accSetColors[1])
        axs[1, 0].plot(df["ts_1"], df["acc_z_3"], label="z", color=accSetColors[2])
        axs[1, 0].set_title(f"{sensor_titles[2]}")
        axs[1, 0].set_ylabel("Aceleración")
        axs[1, 0].legend(loc="lower left")
        axs[1, 0].set_ylim(acc_y_lims)

        axs[1, 1].plot(df["ts_1"], df["acc_x_4"], label="x", color=accSetColors[0])
        axs[1, 1].plot(df["ts_1"], df["acc_y_4"], label="y", color=accSetColors[1])
        axs[1, 1].plot(df["ts_1"], df["acc_z_4"], label="z", color=accSetColors[2])
        axs[1, 1].set_title(f"{sensor_titles[3]}")
        axs[1, 1].set_ylabel("Aceleración")
        axs[1, 1].legend(loc="lower left")
        axs[1, 1].set_ylim(acc_y_lims)

        # Plot para gyr_data
        axs[2, 0].plot(df["ts_1"], df["gyr_x_1"], label="x", color=gyrSetColors[0])
        axs[2, 0].plot(df["ts_1"], df["gyr_y_1"], label="y", color=gyrSetColors[1])
        axs[2, 0].plot(df["ts_1"], df["gyr_z_1"], label="z", color=gyrSetColors[2])
        axs[2, 0].set_title(f"{sensor_titles[0]}")
        axs[2, 0].set_ylabel("Giroscopio")
        axs[2, 0].legend(loc="lower left")
        axs[2, 0].set_ylim(gyr_y_lims)

        axs[2, 1].plot(df["ts_1"], df["gyr_x_2"], label="x", color=gyrSetColors[0])
        axs[2, 1].plot(df["ts_1"], df["gyr_y_2"], label="y", color=gyrSetColors[1])
        axs[2, 1].plot(df["ts_1"], df["gyr_z_2"], label="z", color=gyrSetColors[2])
        axs[2, 1].set_title(f"{sensor_titles[1]}")
        axs[2, 1].set_ylabel("Giroscopio")
        axs[2, 1].legend(loc="lower left")
        axs[2, 1].set_ylim(gyr_y_lims)

        axs[3, 0].plot(df["ts_1"], df["gyr_x_3"], label="x", color=gyrSetColors[0])
        axs[3, 0].plot(df["ts_1"], df["gyr_y_3"], label="y", color=gyrSetColors[1])
        axs[3, 0].plot(df["ts_1"], df["gyr_z_3"], label="z", color=gyrSetColors[2])
        axs[3, 0].set_title(f"{sensor_titles[2]}")
        axs[3, 0].set_ylabel("Giroscopio")
        axs[3, 0].legend(loc="lower left")
        axs[3, 0].set_ylim(gyr_y_lims)

        axs[3, 1].plot(df["ts_1"], df["gyr_x_4"], label="x", color=gyrSetColors[0])
        axs[3, 1].plot(df["ts_1"], df["gyr_y_4"], label="y", color=gyrSetColors[1])
        axs[3, 1].plot(df["ts_1"], df["gyr_z_4"], label="z", color=gyrSetColors[2])
        axs[3, 1].set_title(f"{sensor_titles[3]}")
        axs[3, 1].set_ylabel("Giroscopio")
        axs[3, 1].legend(loc="lower left")
        axs[3, 1].set_ylim(gyr_y_lims)

        fig.supxlabel("Tiempo [s]")

        # Ajustar el diseño
        suptitle = self.output_filename

        plt.suptitle(suptitle)
        plt.tight_layout()
        plt.savefig(
            self.output_folder + "/" + self.output_filename + "/" + "Gráficas.png"
        )  # Guardar el gráfico como una imagen PNG



class FSR:
    def __init__(
        self,
        local_udp_ip,
        shared_port,
        esp_ips,
        struct_format,
        output_folder,
        output_filename,
        time_between_vibrations,
        time_between_heel_detection,
        thy,
        vd,
        motor_power,
        min_duration_between_heels,
        vibration_offset,
        reading_mode,
    ):
        self.local_udp_ip = local_udp_ip
        self.shared_port = shared_port
        self.num_esps = 4
        self.esp_indexes = [1, 2, 3, 4]
        self.esp_ips = esp_ips
        self.struct_format = struct_format
        self.output_folder = output_folder
        self.output_filename = output_filename
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.thy = thy
        self.vd = vd
        self.motor_power = motor_power
        self.max_time_sync_diff = 50 # Máxima diferencia de tiempo permitida (8 ms)
        self.time_between_vibrations = time_between_vibrations
        self.time_between_heel_detection = time_between_heel_detection
        self.reading_mode = reading_mode

        # Estado de grabación
        self.recording = False
        self.recorded_data = []
        self.start_time = None
        self.left_steps_ts = []
        self.right_steps_ts = []
        self.buffers = [[] for _ in range(self.num_esps)]
        self.sock = self.setup_socket(local_udp_ip, shared_port)

        # Variables caminata
        self.last_vibration_ts = [
            0 for _ in range(2)
        ]  # TS de la última vibración
        self.min_duration_between_heels = (
            min_duration_between_heels  # Duracion minima entre talones
        )
        self.vibrating = [False for _ in range(2)]
        self.fsr = [False for _ in range(2)]
        self.last_vibration_esp = -1
        self.vibration_offset = vibration_offset
        self.data_queue = queue.Queue()
        self.esp_data = [None] * self.num_esps

        self.total_time = 0
        self.init_time = 0

    def setup_socket(self, local_ip, shared_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((local_ip, shared_port))
            return sock
        except Exception as e:
            print(e)

    def analyze_event(self, esp_id, data, panels):
        fsr_frontal = data[7]
        fsr_trasero = data[8]
        current_ts = time.time()

        if not self.vibrating[0] and not self.vibrating[1]:
            if esp_id == 2:
                if (fsr_frontal > self.thy or fsr_trasero > self.thy):
                    self.fsr[0] = True
                else:
                    self.fsr[0] = False
            if esp_id == 4:
                if (fsr_frontal > self.thy or fsr_trasero > self.thy):
                    self.fsr[1] = True
                else:
                    self.fsr[1] = False
        
        if self.fsr[0] ^ self.fsr[1] and (not self.vibrating[0] and not self.vibrating[1]):
            if self.fsr[0] and not self.vibrating[0] and self.last_vibration_esp != 0:
                self.activate_selected_motors([2, 3])
                self.last_vibration_ts[0] = current_ts
                self.vibrating[0] = True
                self.last_vibration_esp = 0
                self.right_steps_ts.append(data[9])
                panels[1].configure(bg="green")
                panels[2].configure(bg="green")

            if self.fsr[1] and not self.vibrating[1] and self.last_vibration_esp != 1:
                self.activate_selected_motors([1, 4])
                self.last_vibration_ts[1] = current_ts
                self.vibrating[1] = True
                self.last_vibration_esp = 1
                self.left_steps_ts.append(data[9])
                panels[0].configure(bg="green")
                panels[3].configure(bg="green")

        if (
            esp_id == 2
            and (current_ts - self.last_vibration_ts[0]) * 1000 > self.vd
            and self.vibrating[0]
        ):
            self.vibrating[0] = False
            panels[1].configure(bg="white")
            panels[2].configure(bg="white")
        if (
            esp_id == 4
            and (current_ts - self.last_vibration_ts[1]) * 1000 > self.vd
            and self.vibrating[1]
        ):
            self.vibrating[1] = False
            panels[0].configure(bg="white")
            panels[3].configure(bg="white")
                
    def reinit_panels(self, panels):
        for esp_id in self.esp_indexes:
            panels[esp_id - 1].configure(bg="white")

    def update_output_filename(self, event):
        new_output_filename = event.widget.get()
        self.output_filename = new_output_filename

    def update_thy(self, new_thy):
        self.thy = float(new_thy)

    def update_vd(self, new_vd):
        self.vd = int(new_vd)
        self.set_selected_motors_vibration_time()

    def save_data_to_csv(self):
        with open(self.output_folder + "/" + self.output_filename + "/" + "recorded_data.csv", "w", newline="") as csvfile:
            csvwriter = csv.writer(csvfile)
            header = ["elapsed_time"]
            for i in self.esp_indexes:
                header.extend(
                    [
                        f"ts_{i}",
                        f"acc_x_{i}",
                        f"acc_y_{i}",
                        f"acc_z_{i}",
                        f"gyr_x_{i}",
                        f"gyr_y_{i}",
                        f"gyr_z_{i}",
                        f"fsr_frontal_{i}",
                        f"fsr_trasero_{i}",
                    ]
                )
            csvwriter.writerow(header)
            csvwriter.writerows(self.recorded_data)

    def clean_and_rename_csv(self):
        df = pd.read_csv(f"{self.output_folder}/{self.output_filename}/recorded_data.csv", delimiter=",")
        # Definir columnas de timestamp y número de filas iniciales a revisar
        timestamp_columns = ["ts_1", "ts_2", "ts_3", "ts_4"]
        initial_rows_count = 20
        timestamp_threshold = 500  # El umbral para detectar valores anómalos en las primeras filas

        for column in timestamp_columns:
            df = df.drop_duplicates(subset=[column])

        initial_df = df.head(initial_rows_count)

        anomaly_mask = (initial_df[timestamp_columns] > timestamp_threshold).any(axis=1)
        filtered_initial_df = initial_df[~anomaly_mask]

        remaining_df = df.iloc[initial_rows_count:]

        df = pd.concat([filtered_initial_df, remaining_df], ignore_index=True)

        umbral = 500
        df['diff_ts_1'] = df['ts_1'].diff()
        wrong_ts_idx = df[df['diff_ts_1'].abs() > umbral].index
        if not wrong_ts_idx.empty:
            idx_to_delete= wrong_ts_idx[0]
            df = df.iloc[:idx_to_delete]
        df = df.drop(columns=['diff_ts_1'])

        df.insert(0, "index", range(len(df)))

        output_filename = "Datos.csv"
        df.to_csv(f"{self.output_folder}/{self.output_filename}/{output_filename}", index=False)

        return output_filename

    def process_data(self, data, panels):
        # Verificamos si la grabación ha comenzado, reiniciando los buffers y otros valores
        if self.start_time is None and self.recording:
            # Reiniciar el tiempo de inicio y otros valores necesarios
            self.start_time = time.time()
            self.init_time = datetime.now().strftime("%H:%M:%S")
            self.data_queue = queue.Queue()
            self.buffers = [[] for _ in range(self.num_esps)]  # Reiniciar los buffers

        elapsed_time = time.time() - self.start_time

        for esp_id in self.esp_indexes:
            if data[esp_id - 1] is not None:
                self.buffers[esp_id - 1].append(data[esp_id - 1])

        while all(self.buffers):
            tss = [self.buffers[esp_id - 1][-1][9] for esp_id in self.esp_indexes]
            min_ts = min(tss)
            max_ts = max(tss)
            if max_ts - min_ts <= self.max_time_sync_diff:
                record_entry = [elapsed_time]
                for esp_id in self.esp_indexes:
                    try:
                        synchronized_data = self.buffers[esp_id - 1].pop(0)
                        record_entry.extend(
                            [
                                synchronized_data[9],
                                synchronized_data[1],
                                synchronized_data[2],
                                synchronized_data[3],
                                synchronized_data[4],
                                synchronized_data[5],
                                synchronized_data[6],
                                synchronized_data[7],
                                synchronized_data[8],
                            ]
                        )
                        self.analyze_event(esp_id, synchronized_data, panels)
                    except Exception as e:
                        continue
                self.recorded_data.append(record_entry)
            else:
                oldest_index = tss.index(min_ts)
                self.buffers[oldest_index].pop(0)

    def display_data(self, data, label_texts):
        for esp_id in self.esp_indexes:
            if data[esp_id - 1] is not None:
                board_id = data[esp_id - 1][0]
                if board_id == 1 or board_id == 3:
                    label_texts[esp_id - 1].set(
                        f"Board ID: {board_id}\n"
                        f"  Acc      Gyr\n"
                        f"X  {round(data[esp_id - 1][1], 2):<7}   {round(data[esp_id - 1][4], 2):<7}\n"
                        f"Y  {round(data[esp_id - 1][2], 2):<7}   {round(data[esp_id - 1][5], 2):<7}\n"
                        f"Z  {round(data[esp_id - 1][3], 2):<7}   {round(data[esp_id - 1][6], 2):<7}\n"
                        f"Timestamp: {data[esp_id - 1][9]}"
                    )
                else:
                    label_texts[esp_id - 1].set(
                        f"Board ID: {board_id}\n"
                        f"  Acc      Gyr\n"
                        f"X  {round(data[esp_id - 1][1], 2):<7}   {round(data[esp_id - 1][4], 2):<7}\n"
                        f"Y  {round(data[esp_id - 1][2], 2):<7}   {round(data[esp_id - 1][5], 2):<7}\n"
                        f"Z  {round(data[esp_id - 1][3], 2):<7}   {round(data[esp_id - 1][6], 2):<7}\n"
                        f"FSR Frontal  {round(data[esp_id - 1][7], 2):<7}\n"
                        f"FSR Trasero  {round(data[esp_id - 1][8], 2):<7}\n"
                        f"Timestamp: {data[esp_id - 1][9]}"
                    )
            else:
                label_texts[esp_id - 1].set(f"Board {esp_id} no conectada")

    def is_synchronized(self, data):
        timestamps = [reading[9] for reading in data if reading is not None]
        
        if len(timestamps) < len(self.esp_indexes):
            return False  # No todos los dispositivos han enviado datos aún

        min_ts = min(timestamps)
        max_ts = max(timestamps)
        
        # Definir un máximo de diferencia entre los timestamps para considerar que están sincronizados
        if max_ts - min_ts <= self.max_time_sync_diff:
            return True
        else:
            return False

    def receive_data(self, panels):
        while True:
            try:
                data, _ = self.sock.recvfrom(1024)
                if len(data) == struct.calcsize(self.struct_format):
                    readings = struct.unpack(self.struct_format, data)
                    esp_id = readings[0]
                    self.esp_data[esp_id - 1] = readings

                    if self.recording:
                        # Primero verificar si los dispositivos están sincronizados
                        if self.is_synchronized(self.esp_data):
                            # Si están sincronizados, enviamos los datos a la cola y los procesamos
                            self.data_queue.put(self.esp_data.copy())  # Agregar los datos a la cola
                            data = self.data_queue.get()  # Extraer los datos de la cola
                            self.process_data(data, panels)  # Procesar los datos
                        else:
                            # Si no están sincronizados, esperamos un poco antes de intentar de nuevo
                            continue
            except:
                self.setup_socket(self.local_udp_ip, self.shared_port)

    def update_gui(self, label_texts, root):
        try:
            if root.winfo_exists():
                # Llama a display_data para actualizar la interfaz
                self.display_data(self.esp_data, label_texts)
                # Programa la próxima actualización sin necesidad de while True
                #root.after(1, lambda: self.update_gui(label_texts, root))
                root.after(10, self.update_gui, label_texts, root)
            else:
                root.quit()  # Cierra la aplicación correctamente
        except Exception as e:
            print(f"Se produjo un error: {e}")
            root.quit()  # En caso de cualquier error, cerrar la aplicación
                
    def reinitialize_gaitmelt_variables(self):
        self.start_time = None
        self.recorded_data = []
        self.left_steps_ts = []
        self.right_steps_ts = []
        self.buffers = [[] for _ in range(self.num_esps)]
        self.last_vibration_ts = [0 for _ in range(self.num_esps)]

    def stop_recording(self, record_button):
        self.save_data_to_csv()
        final_csv_filename = self.clean_and_rename_csv()
        self.generate_pdf()
        self.plot_data(final_csv_filename)
        os.remove(self.output_folder + "/" + self.output_filename + "/" + "recorded_data.csv")
        button_text = "Iniciar registro"
        record_button.config(text=button_text, bg="green", fg="white")

    def init_recording(self, record_button):
        record_button.config(text="Detener registro", bg="red", fg="white")


    def exit_app(self, root):
        root.quit()  # Cerrar la aplicación

    def show_result_dialog(self, root):
        root.withdraw()  # Ocultar la ventana principal

        # Crear una ventana principal
        window = tk.Tk()
        
        window.protocol("WM_DELETE_WINDOW", lambda: None)

        # Ajustar el tamaño de la ventana
        window.geometry("400x400")  # Aumenta el tamaño de la ventana
        
        # Establecer el título de la ventana
        window.title("Registro Finalizado")
        window.resizable(False, False)  # Permite redimensionar la ventana
        
        # Calcular la posición para centrar la ventana en la pantalla
        screen_width = window.winfo_screenwidth()  # Ancho de la pantalla
        screen_height = window.winfo_screenheight()  # Altura de la pantalla
        
        # Obtener las dimensiones de la ventana
        window_width = 600  # Ancho de la ventana
        window_height = 200  # Altura de la ventana
        
        # Calcular las coordenadas para centrar la ventana
        position_top = int(screen_height / 2 - window_height / 2)
        position_left = int(screen_width / 2 - window_width / 2)
        
        # Establecer la posición de la ventana
        window.geometry(f"{window_width}x{window_height}+{position_left}+{position_top}")
        
        # Crear un label (etiqueta) para el mensaje inicial
        message1 = "El registro ha finalizado con éxito.\nLos archivos han quedado guardados en:"
        label1 = tk.Label(window, text=message1, font=("Segoe UI", 20), padx=20, pady=20, justify="center")
        label1.pack(expand=True)

        # Crear un label (etiqueta) para la ruta en negrita
        message2 = f"{self.output_folder}{self.output_filename}/"
        label2 = tk.Label(window, text=message2, font=("Segoe UI", 20, "bold"), padx=20, pady=10, justify="center")
        label2.pack(expand=True)

        # Botón para cerrar la ventana
        continue_button = tk.Button(
            window, 
            text="Continuar", 
            command=lambda: self.close_dialog_and_reopen(window, root), 
            font=("Arial", 12),
            bg="green", 
            fg="white",
        )
        continue_button.pack(side="left", padx=20, pady=10)

        # Botón para cerrar la ventana
        close_button = tk.Button(
            window, 
            text="Salir", 
            command=lambda: self.exit_app(root), 
            font=("Arial", 12),
            bg="red", 
            fg="white",
        )
        close_button.pack(side="right", padx=20, pady=10)
        

    def close_dialog_and_reopen(self, window, root):
        window.destroy()
        root.deiconify()
    
    # Función que hace parpadear el círculo
    def blink_circle(self, canvas, circle, root):
        current_color = canvas.itemcget(circle, "fill")
        new_color = "white" if current_color == "red" else "red"
        canvas.itemconfig(circle, fill=new_color)
        root.after(1000, self.blink_circle, canvas, circle, root)

    def toggle_recording(self, record_button, back_button, exit_button, canvas, circle, root, panels):
        self.sync_devices()
        if self.recording:
            self.reinit_panels(panels)
            self.show_result_dialog(root)
            self.recording = False
            self.stop_recording(record_button)
            canvas.itemconfig(circle, state="hidden")  # Ocultar el círculo
            back_button.config(state="normal")
            exit_button.config(state="normal")
        else:
            self.recording = True
            if not os.path.exists(self.output_folder + "/" + self.output_filename):
                os.makedirs(self.output_folder + "/" + self.output_filename)
            self.init_recording(record_button)
            canvas.itemconfig(circle, state="normal")  # Ocultar el círculo
            back_button.config(state="disabled")
            exit_button.config(state="disabled")
            self.blink_circle(canvas, circle, root)  # Iniciar el parpadeo
        self.reinitialize_gaitmelt_variables()

    def send_esp_message(self, IP, message):
        try:
            self.sock.sendto(message.encode(), (IP, self.shared_port))
        except Exception as e:
            print(f"Error sending message {message} to {IP}: {e}")

    def sync_devices(self):
        self.set_selected_motors_vibration_time()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.send_esp_message, self.esp_ips[esp], "reset")
                for esp in self.esp_indexes
            ]
            concurrent.futures.wait(futures)

    def activate_selected_motors(self, selected_esp_indexes):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self.send_esp_message,
                    self.esp_ips[esp],
                    "motor" + str(self.vibration_offset),
                )
                for esp in selected_esp_indexes
            ]
            concurrent.futures.wait(futures)

    def stop_selected_motors(self, selected_esp_indexes):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self.send_esp_message,
                    self.esp_ips[esp],
                    "stop",
                )
                for esp in selected_esp_indexes
            ]
            concurrent.futures.wait(futures)

    def set_selected_motors_vibration_time(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self.send_esp_message,
                    self.esp_ips[esp],
                    "duration" + str(self.vd),
                )
                for esp in self.esp_indexes
            ]
            concurrent.futures.wait(futures)

    def set_selected_motors_motor_power(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self.send_esp_message,
                    self.esp_ips[esp],
                    "power" + str(int(self.motor_power)),
                )
                for esp in self.esp_indexes
            ]
            concurrent.futures.wait(futures)

    def plot_data(self, csv_filename):
        # Lee el archivo CSV
        accSetColors = ["red", "blue", "green"]
        gyrSetColors = ["purple", "orange", "pink"]

        acc_y_lims = (-25, 25)
        gyr_y_lims = (-5, 5)

        try:
            df = pd.read_csv(self.output_folder + "/" + self.output_filename + "/" +  csv_filename, sep=",")
        except FileNotFoundError:
            return

        fig, axs = plt.subplots(
            self.num_esps, 2, figsize=(12, 8), sharex="col", sharey="row"
        )

        sensor_titles = [
            "Sensor 1 - Muslo Izquierdo",
            "Sensor 2 - Muslo Derecho",
            "Sensor 3 - Gemelo Izquierdo",
            "Sensor 4 - Gemelo Derecho",
        ]

        # Plot para acc_data
        axs[0, 0].plot(df["ts_1"], df["acc_x_3"], label="x", color=accSetColors[0])
        axs[0, 0].plot(df["ts_1"], df["acc_y_3"], label="y", color=accSetColors[1])
        axs[0, 0].plot(df["ts_1"], df["acc_z_3"], label="z", color=accSetColors[2])
        axs[0, 0].set_title(f"{sensor_titles[2]}")
        axs[0, 0].set_ylabel("Aceleración")
        if self.right_steps_ts:
            for idx, time_point in enumerate(self.right_steps_ts):
                axs[0, 0].axvline(
                    x=time_point, color="black", linestyle="--", linewidth=1, label="Activación vibración" if idx == 0 else None
                )
        axs[0, 0].legend()
        axs[0, 0].set_ylim(acc_y_lims)

        axs[0, 1].plot(df["ts_1"], df["acc_x_1"], label="x", color=accSetColors[0])
        axs[0, 1].plot(df["ts_1"], df["acc_y_1"], label="y", color=accSetColors[1])
        axs[0, 1].plot(df["ts_1"], df["acc_z_1"], label="z", color=accSetColors[2])
        axs[0, 1].set_title(f"{sensor_titles[0]}")
        axs[0, 1].set_ylabel("Aceleración")
        if self.left_steps_ts:
            for idx, time_point in enumerate(self.left_steps_ts):
                axs[0, 1].axvline(
                    x=time_point, color="black", linestyle="--", linewidth=1, label="Activación vibración" if idx == 0 else None
                )
        axs[0, 1].legend()
        axs[0, 1].set_ylim(acc_y_lims)

        axs[1, 0].plot(df["ts_1"], df["acc_x_4"], label="x", color=accSetColors[0])
        axs[1, 0].plot(df["ts_1"], df["acc_y_4"], label="y", color=accSetColors[1])
        axs[1, 0].plot(df["ts_1"], df["acc_z_4"], label="z", color=accSetColors[2])
        axs[1, 0].set_title(f"{sensor_titles[3]}")
        axs[1, 0].set_ylabel("Aceleración")
        if self.left_steps_ts:
            for idx, time_point in enumerate(self.left_steps_ts):
                axs[1, 0].axvline(
                    x=time_point, color="black", linestyle="--", linewidth=1, label="Activación vibración" if idx == 0 else None
                )
        axs[1, 0].legend()
        axs[1, 0].set_ylim(acc_y_lims)

        axs[1, 1].plot(df["ts_1"], df["acc_x_2"], label="x", color=accSetColors[0])
        axs[1, 1].plot(df["ts_1"], df["acc_y_2"], label="y", color=accSetColors[1])
        axs[1, 1].plot(df["ts_1"], df["acc_z_2"], label="z", color=accSetColors[2])
        axs[1, 1].set_title(f"{sensor_titles[1]}")
        axs[1, 1].set_ylabel("Aceleración")
        if self.right_steps_ts:
            for idx, time_point in enumerate(self.right_steps_ts):
                axs[1, 1].axvline(
                    x=time_point, color="black", linestyle="--", linewidth=1, label="Activación vibración" if idx == 0 else None
                )
        axs[1, 1].legend()
        axs[1, 1].set_ylim(acc_y_lims)

        # Plot para gyr_data
        axs[2, 0].plot(df["ts_1"], df["gyr_x_3"], label="x", color=gyrSetColors[0])
        axs[2, 0].plot(df["ts_1"], df["gyr_y_3"], label="y", color=gyrSetColors[1])
        axs[2, 0].plot(df["ts_1"], df["gyr_z_3"], label="z", color=gyrSetColors[2])
        axs[2, 0].set_title(f"{sensor_titles[2]}")
        axs[2, 0].set_ylabel("Giroscopio")
        if self.right_steps_ts:
            for idx, time_point in enumerate(self.right_steps_ts):
                axs[2, 0].axvline(
                    x=time_point, color="black", linestyle="--", linewidth=1, label="Activación vibración" if idx == 0 else None
                )
        axs[2, 0].legend()
        axs[2, 0].set_ylim(gyr_y_lims)

        axs[2, 1].plot(df["ts_1"], df["gyr_x_1"], label="x", color=gyrSetColors[0])
        axs[2, 1].plot(df["ts_1"], df["gyr_y_1"], label="y", color=gyrSetColors[1])
        axs[2, 1].plot(df["ts_1"], df["gyr_z_1"], label="z", color=gyrSetColors[2])
        axs[2, 1].set_title(f"{sensor_titles[0]}")
        axs[2, 1].set_ylabel("Giroscopio")
        if self.left_steps_ts:
            for idx, time_point in enumerate(self.left_steps_ts):
                axs[2, 1].axvline(
                    x=time_point, color="black", linestyle="--", linewidth=1, label="Activación vibración" if idx == 0 else None
                )
        axs[2, 1].legend()
        axs[2, 1].set_ylim(gyr_y_lims)

        axs[3, 0].plot(df["ts_1"], df["gyr_x_4"], label="x", color=gyrSetColors[0])
        axs[3, 0].plot(df["ts_1"], df["gyr_y_4"], label="y", color=gyrSetColors[1])
        axs[3, 0].plot(df["ts_1"], df["gyr_z_4"], label="z", color=gyrSetColors[2])
        axs[3, 0].set_title(f"{sensor_titles[3]}")
        axs[3, 0].set_ylabel("Giroscopio")
        if self.left_steps_ts:
            for idx, time_point in enumerate(self.left_steps_ts):
                axs[3, 0].axvline(
                    x=time_point, color="black", linestyle="--", linewidth=1, label="Activación vibración" if idx == 0 else None
                )
        axs[3, 0].legend()
        axs[3, 0].set_ylim(gyr_y_lims)

        axs[3, 1].plot(df["ts_1"], df["gyr_x_2"], label="x", color=gyrSetColors[0])
        axs[3, 1].plot(df["ts_1"], df["gyr_y_2"], label="y", color=gyrSetColors[1])
        axs[3, 1].plot(df["ts_1"], df["gyr_z_2"], label="z", color=gyrSetColors[2])
        axs[3, 1].set_title(f"{sensor_titles[1]}")
        axs[3, 1].set_ylabel("Giroscopio")
        if self.right_steps_ts:
            for idx, time_point in enumerate(self.right_steps_ts):
                axs[3, 1].axvline(
                    x=time_point, color="black", linestyle="--", linewidth=1, label="Activación vibración" if idx == 0 else None
                )
        axs[3, 1].legend()
        axs[3, 1].set_ylim(gyr_y_lims)

        fig.supxlabel("Tiempo [s]")

        # Ajustar el diseño
        suptitle = self.output_filename

        plt.suptitle(suptitle)
        plt.tight_layout()
        plt.savefig(
            self.output_folder + "/" + self.output_filename + "/" + "Gráficas.png"
        )  # Guardar el gráfico como una imagen PNG

    # Función para generar el PDF
    def generate_pdf(self):
        # Crear un objeto Canvas
        c = canvas.Canvas(f"{self.output_folder}/{self.output_filename}/Reporte Gaitmelt.pdf", pagesize=letter)
        _, height = letter  # Tamaño de la página
        
        height = height - 30
        # Título
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, 720, "Reporte Gaitmelt")
        
        # Logo en la parte superior derecha
        logo_path = "leufulab.png"  # Cambia esto por la ruta de tu logo
        c.drawImage(logo_path, 500, 730, width=100, height=70)
        
        # Datos
        c.setFont("Helvetica", 12)

        current_date = datetime.now().strftime("%d-%m-%Y")

        total_time = time.time() - self.start_time
        hours = int(total_time // 3600)  # Obtener las horas
        minutes = int((total_time % 3600) // 60)  # Obtener los minutos
        seconds = int(total_time % 60)  # Obtener los segundos
        formatted_time = f"{hours:02}:{minutes:02}:{seconds:02}"

        left_step_count = len(self.left_steps_ts)
        right_step_count = len(self.right_steps_ts)
        total_steps = left_step_count + right_step_count

        # Inicializamos las variables de cadencia como 0 por defecto
        left_step_cadence_avg = 0
        min_left_step_cadence_avg = 0
        max_left_step_cadence_avg = 0
        right_step_cadence_avg = 0
        min_right_step_cadence_avg = 0
        max_right_step_cadence_avg = 0
        general_cadence = 0

        # Verificamos si hay pasos en ambos pies
        if total_steps > 0:
            if left_step_count > 1:  # Si hay pasos en el pie izquierdo
                left_step_cadence = np.diff(self.left_steps_ts) / 1000
                left_step_cadence_avg = np.mean(left_step_cadence)
                min_left_step_cadence_avg = np.min(left_step_cadence)
                max_left_step_cadence_avg = np.max(left_step_cadence)

            if right_step_count > 1:  # Si hay pasos en el pie derecho
                right_step_cadence = np.diff(self.right_steps_ts) / 1000
                right_step_cadence_avg = np.mean(right_step_cadence)
                min_right_step_cadence_avg = np.min(right_step_cadence)
                max_right_step_cadence_avg = np.max(right_step_cadence)

            # Concatenar las cadencias de ambos pies (si existen)
            total_cadence = []
            if left_step_count > 1:
                total_cadence.extend(left_step_cadence)
            if right_step_count > 1:
                total_cadence.extend(right_step_cadence)

            # Calcular la cadencia general si hay datos
            if total_cadence:
                general_cadence = np.mean(total_cadence)

        c.setFont("Helvetica", 12)
        # Dibujar los textos en el documento con separaciones de 40 puntos entre secciones
        c.drawString(50, height - 80, f"Paciente: {self.output_filename}")
        c.drawString(50, height - 100, f"Fecha: {current_date}")
        c.drawString(50, height - 120, f"Hora: {self.init_time}")

        # Separación de 40 puntos entre las siguientes secciones
        c.drawString(50, height - 160, f"- Tiempo total: {formatted_time}")
        c.drawString(50, height - 180, f"- N° total de pasos: {total_steps}")
        c.drawString(50, height - 200, f"- Cadencia promedio del total de pasos: {general_cadence:.2f} segundos")

        # Datos de la pierna izquierda
        c.drawString(50, height - 240, f"- Pierna izquierda:")
        c.drawString(50, height - 260, f"  - N° de pasos: {left_step_count}")
        c.drawString(50, height - 280, f"  - Cadencia mínima: {min_left_step_cadence_avg:.2f} segundos")
        c.drawString(50, height - 300, f"  - Cadencia máxima: {max_left_step_cadence_avg:.2f} segundos")
        c.drawString(50, height - 320, f"  - Cadencia promedio: {left_step_cadence_avg:.2f} segundos")

        # Datos de la pierna derecha
        c.drawString(50, height - 360, f"- Pierna derecha:")
        c.drawString(50, height - 380, f"  - N° de pasos: {right_step_count}")
        c.drawString(50, height - 400, f"  - Cadencia mínima: {min_right_step_cadence_avg:.2f} segundos")
        c.drawString(50, height - 420, f"  - Cadencia máxima: {max_right_step_cadence_avg:.2f} segundos")
        c.drawString(50, height - 440, f"  - Cadencia promedio: {right_step_cadence_avg:.2f} segundos")

        # Agregar más información si es necesario
        c.showPage()  # Añadir una nueva página si se necesita más espacio

        # Guardar el archivo PDF
        c.save()