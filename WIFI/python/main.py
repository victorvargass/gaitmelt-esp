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
OUTPUT_FILENAME = "Paciente 01"

OUTPUT_FOLDER = "output_data/"

NUM_ESPS = 4
MOTOR_POWER = 250

ESP_INDEXES = [1, 2, 3, 4]

SCREEN_SIZE = "1300x700" if NUM_ESPS == 2 else "1300x900"

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
    motor_power=MOTOR_POWER,
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

new_positions = {
    0: (0, 1),
    1: (1, 1),
    2: (0, 0),
    3: (1, 0)
}

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

    # Determinar las posiciones de acuerdo al número de ESPs
    if NUM_ESPS == 4:
        # Usar el diccionario de posiciones cuando hay 4 ESPs
        row, col = new_positions[i]
    else:
        # Calcular dinámicamente para otros números (como 2)
        row = i // 2  # División entera para determinar la fila
        col = i % 2   # Residuo para determinar la columna (0 o 1)
    
    frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

# Asegura que las filas bajo los paneles puedan expandirse
for i in range(NUM_ESPS // 2, 10):  # Configura las filas adicionales necesarias
    root.grid_rowconfigure(i, weight=0)

# Ordenar los controles adicionales en una columna debajo de los paneles
start_row = (NUM_ESPS + 1) // 2  # Comienza justo después de los paneles


label_output_filename = tk.Label(root, text="Nombre del archivo")
label_output_filename.grid(row=start_row + 2, column=0, columnspan=2, pady=(20, 0))
input_output_filename = tk.Entry(root)
input_output_filename.grid(row=start_row + 3, column=0, columnspan=2, pady=(20, 0))
input_output_filename.insert(0, OUTPUT_FILENAME)  # Establecer el valor por defecto
input_output_filename.bind('<KeyRelease>', gaitmelt.update_output_filename)


record_with_vibration_button = tk.Button(
    root,
    text="Iniciar registro con vibración",
    command=lambda: gaitmelt.toggle_recording(record_with_vibration_button, True),
    bg="green",
    fg="white",
)
record_with_vibration_button.grid(row=start_row + 4, column=0, columnspan=2, pady=(20, 0))

record_without_vibration_button = tk.Button(
    root,
    text="Iniciar registro sin vibración",
    command=lambda: gaitmelt.toggle_recording(record_without_vibration_button, False),
    bg="green",
    fg="white",
)
record_without_vibration_button.grid(row=start_row + 5, column=0, columnspan=2, pady=(20, 0))

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
