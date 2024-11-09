import tkinter as tk
import queue
import threading
from utils import FSR  # Asegúrate de que esta importación sea correcta
import subprocess

# Configuración de los ESPs
ESP_IPS = {
    1: "192.168.50.21",
    2: "192.168.50.22",
    3: "192.168.50.23",
    4: "192.168.50.24",
}
STRUCT_FORMAT = "i fff fff ii i"
LOCAL_UDP_IP = "192.168.50.82"
SHARED_UDP_PORT = 4210

OUTPUT_FILENAME = "Voluntario 04 - TUG SV1"
OUTPUT_FOLDER = "output_data/"

READING_MODE = True

NUM_ESPS = 4
THY = 3000
VD = 1000  # 500 vibration duration
TIME_BETWEEN_VIBRATIONS = 0.8  # quiza modificar
TIME_BETWEEN_HEEL_DETECTION = None
MIN_DURATION_BETWEEN_HEELS = None
MOTOR_POWER = 250 # 70
VIBRATION_OFFSET=None

ESP_INDEXES = [1, 2, 3, 4]

# Crear una instancia de FSR
fsr = FSR(
    local_udp_ip=LOCAL_UDP_IP,
    shared_port=SHARED_UDP_PORT,
    num_esps=NUM_ESPS,
    esp_indexes=ESP_INDEXES,
    esp_ips=ESP_IPS,
    struct_format=STRUCT_FORMAT,
    output_folder=OUTPUT_FOLDER,
    output_filename=OUTPUT_FILENAME,
    time_between_vibrations=TIME_BETWEEN_VIBRATIONS,
    time_between_heel_detection=TIME_BETWEEN_HEEL_DETECTION,
    thy=THY,
    vd=VD,
    motor_power=MOTOR_POWER,
    min_duration_between_heels=MIN_DURATION_BETWEEN_HEELS,
    vibration_offset=VIBRATION_OFFSET,
    reading_mode=READING_MODE
)

def back_to_main():
    subprocess.Popen(['python', 'main.py'])  # Abrir main.py
    root.destroy()  # Cerrar vibracion.py

def create_fsr_tab(parent):
    """Crea el contenido de la pestaña 1 con la interfaz de control y visualización de ESPs."""
    
    # Configuración de ESPs
    label_texts = [tk.StringVar() for _ in range(fsr.num_esps)]
    for i, text in enumerate(label_texts):
        text.set(f"Board {i+1} no conectada")

    # Configurar la cuadrícula para que sea flexible
    for i in range(2):
        parent.grid_columnconfigure(i, weight=1)
    for i in range((fsr.num_esps + 1) // 2):
        parent.grid_rowconfigure(i, weight=1)

    new_positions = {
        0: (0, 1),
        1: (1, 1),
        2: (0, 0),
        3: (1, 0)
    }

    # Crear y ubicar los paneles con botones
    for i, text in enumerate(label_texts):
        frame = tk.Frame(parent, padx=5, pady=5, borderwidth=2, relief="solid", bg="white")
        
        # Label dentro del frame
        label = tk.Label(frame, textvariable=text, bg="white")
        label.pack(pady=(10, 5), expand=True, fill='both')

        # Botón dentro del frame
        button = tk.Button(
            frame,
            text=f"Activar vibrador",
            command=lambda i=i: fsr.activate_selected_motors([i+1]),
            bg="green",
            fg="white",
            font=("Helvetica", 12),
        )
        button.pack(pady=(5, 10))

        # Determinar las posiciones de acuerdo al número de ESPs
        if fsr.num_esps == 4:
            row, col = new_positions[i]
        else:
            row = i // 2
            col = i % 2
        
        frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

    # Ordenar los controles adicionales en una columna debajo de los paneles
    start_row = (fsr.num_esps + 1) // 2

    all_motors_button = tk.Button(
        parent,
        text="Activar todos",
        command=lambda: fsr.activate_selected_motors(fsr.esp_indexes),
        bg="green",
        fg="white",
    )
    all_motors_button.grid(row=start_row, column=0, columnspan=2, pady=(20, 0))

    all_motors_stop_button = tk.Button(
        parent,
        text="Detener todos",
        command=lambda: fsr.stop_selected_motors(fsr.esp_indexes),
        bg="red",
        fg="white",
    )
    all_motors_stop_button.grid(row=start_row + 1, column=0, columnspan=2, pady=(20, 0))

    sync_button = tk.Button(
        parent,
        text="Sincronizar dispositivos",
        command=lambda: fsr.sync_devices(),
        bg="yellow",
        fg="white",
    )
    sync_button.grid(row=start_row + 2, column=0, columnspan=2, pady=(20, 0))

    # Configurar los sliders y demás controles
    vd_slider_label = tk.Label(parent, text="Duración vibración [ms]", bg="white")
    vd_slider_label.grid(row=start_row + 3, column=0, columnspan=2, pady=(20, 0))

    vd_slider = tk.Scale(
        parent,
        from_=10,
        resolution=10,
        to=20000,
        orient="horizontal",
        length=200,
        bg="white",
        command=lambda value: fsr.update_vd(vd_slider.get()),
    )
    vd_slider.set(fsr.vd)
    vd_slider.grid(row=start_row + 4, column=0, columnspan=2)

    # Configurar threads para la recepción de datos y actualización de la GUI
    esp_data = [None] * NUM_ESPS
    data_queue = queue.Queue()
    
    back_button = tk.Button(
        parent,
        text="Volver",
        command=lambda: back_to_main(),
        bg="red",
        fg="white",
        font=("Helvetica", 14),
    )
    back_button.grid(row=start_row + 5, column=0, columnspan=2, pady=20)

    # Configurar threads para la recepción de datos y actualización de la GUI
    receive_thread = threading.Thread(
        target=fsr.receive_data, args=(data_queue, esp_data)
    )
    receive_thread.daemon = True
    receive_thread.start()

    update_thread = threading.Thread(
        target=fsr.update_gui,
        args=(data_queue, label_texts, parent),
    )
    update_thread.daemon = True
    update_thread.start()

# Crear la nueva ventana
root = tk.Tk()
root.title("FSR")
root.configure(bg="white")
root.option_add("*Font", "Helvetica 20")
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.geometry(f"{screen_width}x{screen_height}")

# Crear la pestaña de FSR
app = tk.Frame(root)
create_fsr_tab(app)
app.pack(fill="both", expand=True)
root.mainloop()
