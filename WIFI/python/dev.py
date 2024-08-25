import tkinter as tk
import queue
import threading
from utils import GaitMelt  # Asegúrate de que esta importación sea correcta

# Configuración de los ESPs
ESP_IPS = {
    1: "192.168.50.11",
    2: "192.168.50.12",
    3: "192.168.50.13",
    4: "192.168.50.14",
}

STRUCT_FORMAT = "i fff fff i"
LOCAL_UDP_IP = "192.168.50.82"
SHARED_UDP_PORT = 4210
OUTPUT_FILENAME = "Voluntario 04 - TUG SV1"

OUTPUT_FOLDER = "output_data/"
READING_MODE = True

NUM_ESPS = 4
THY = 1.5
VD = 1000  # 500 vibration duration
TIME_BETWEEN_VIBRATIONS = 0.8  # quiza modificar
TIME_BETWEEN_HEEL_DETECTION = None
MIN_DURATION_BETWEEN_HEELS = None
MOTOR_POWER = 250 # 70
VIBRATION_OFFSET=None

ESP_INDEXES = [1, 2] if NUM_ESPS == 2 else [1, 2, 3, 4]

SCREEN_SIZE = "1600x700" if NUM_ESPS == 2 else "1600x1000"

# Crear una instancia de GaitMelt
gaitmelt = GaitMelt(
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

# Configurar la interfaz gráfica
root = tk.Tk()
root.geometry(SCREEN_SIZE)
root.configure(bg="white")
root.option_add("*Font", "Helvetica 20")

label_texts = [tk.StringVar() for _ in range(NUM_ESPS)]
for i, text in enumerate(label_texts):
    text.set(f"Board {i+1} no conectada")

# Configurar la cuadrícula para que sea flexible
for i in range(2):  # Supone que habrá 2 columnas
    root.grid_columnconfigure(i, weight=1)
for i in range((NUM_ESPS + 1) // 2):  # Configura las filas necesarias
    root.grid_rowconfigure(i, weight=1)

# Crear y ubicar los paneles con botones
for i, text in enumerate(label_texts):
    frame = tk.Frame(root, padx=5, pady=5, borderwidth=2, relief="solid", bg="white")
    
    # Label dentro del frame
    label = tk.Label(frame, textvariable=text, bg="white")
    label.pack(pady=(10, 5), expand=True, fill='both')

    # Botón dentro del frame
    button = tk.Button(
        frame,
        text=f"Activar vibrador",
        command=lambda i=i: gaitmelt.activate_selected_motors([i+1]),
        bg="green",
        fg="white",
        font=("Helvetica", 12),
    )
    button.pack(pady=(5, 10))

    row = i // 2
    col = i % 2
    frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")


# Asegura que las filas bajo los paneles puedan expandirse
for i in range(NUM_ESPS // 2, 10):  # Configura las filas adicionales necesarias
    root.grid_rowconfigure(i, weight=0)

# Ordenar los controles adicionales en una columna debajo de los paneles
start_row = (NUM_ESPS + 1) // 2  # Comienza justo después de los paneles

all_motors_button = tk.Button(
    root,
    text="Activar todos",
    command=lambda: gaitmelt.activate_selected_motors(ESP_INDEXES),
    bg="green",
    fg="white",
)
all_motors_button.grid(row=start_row, column=0, columnspan=2, pady=(20, 0))

all_motors_stop_button = tk.Button(
    root,
    text="Detener todos",
    command=lambda: gaitmelt.stop_selected_motors(ESP_INDEXES),
    bg="red",
    fg="white",
)
all_motors_stop_button.grid(row=start_row + 1, column=0, columnspan=2, pady=(20, 0))

sync_button = tk.Button(
    root,
    text="Sincronizar dispositivos",
    command=lambda: gaitmelt.sync_devices(),
    bg="yellow",
    fg="white",
)
sync_button.grid(row=start_row + 2, column=0, columnspan=2, pady=(20, 0))

vd_slider_label = tk.Label(root, text="Duración vibración [ms]", bg="white")
vd_slider_label.grid(row=start_row + 3, column=0, columnspan=2, pady=(20, 0))

vd_slider = tk.Scale(
    root,
    from_=10,
    resolution=10,
    to=20000,
    orient="horizontal",
    length=200,
    bg="white",
    command=lambda value: gaitmelt.update_vd(vd_slider.get()),
)
vd_slider.set(gaitmelt.vd)
vd_slider.grid(row=start_row + 4, column=0, columnspan=2)

motor_power_slider_label = tk.Label(root, text="Potencia motor", bg="white")
motor_power_slider_label.grid(row=start_row + 5, column=0, columnspan=2, pady=(20, 0))

motor_power_slider = tk.Scale(
    root,
    from_=10,
    resolution=10,
    to=250,
    orient="horizontal",
    length=200,
    bg="white",
    command=lambda value: gaitmelt.update_motor_power(motor_power_slider.get()),
)
motor_power_slider.set(gaitmelt.motor_power)
motor_power_slider.grid(row=start_row + 6, column=0, columnspan=2)


label_output_filename = tk.Label(root, text="Nombre del archivo", bg="white")
label_output_filename.grid(row=start_row, column=1, columnspan=2, pady=(20, 0))

input_output_filename = tk.Entry(root)
input_output_filename.grid(row=start_row + 1, column=1, columnspan=3, pady=(20, 0))
input_output_filename.insert(0, OUTPUT_FILENAME)
input_output_filename.bind('<KeyRelease>', gaitmelt.update_output_filename)

record_button = tk.Button(
    root,
    text="Iniciar grabación",
    command=lambda: gaitmelt.toggle_recording(record_button),
    bg="green",
    fg="white",
)
record_button.grid(row=start_row + 2, column=1, columnspan=2, pady=(20, 0))

reading_mode_var = tk.BooleanVar()
reading_mode_var.set(READING_MODE)
toggle_button = tk.Checkbutton(root, text="Modo de Lectura", variable=reading_mode_var, 
                               command=gaitmelt.update_reading_mode, bg="white")
toggle_button.grid(row=start_row + 3, column=1, columnspan=2, pady=(20, 0))

# Configurar threads para la recepción de datos y actualización de la GUI
esp_data = [None] * NUM_ESPS
data_queue = queue.Queue()

receive_thread = threading.Thread(
    target=gaitmelt.receive_data, args=(data_queue, esp_data)
)
receive_thread.daemon = True
receive_thread.start()

update_thread = threading.Thread(
    target=gaitmelt.update_gui,
    args=(data_queue, label_texts, root),
)
update_thread.daemon = True
update_thread.start()

root.mainloop()
