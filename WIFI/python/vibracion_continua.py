import tkinter as tk
import os
import threading
from utils import VibracionContinua  # Asegúrate de que esta importación sea correcta
import subprocess

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

cmd = f"lsof -i :{SHARED_UDP_PORT} | grep {LOCAL_UDP_IP} | awk '{{print $2}}'"

try:
    pid = subprocess.check_output(cmd, shell=True).decode().strip()
    if pid:
        print(f"Terminando proceso con PID {pid} que está usando el puerto {SHARED_UDP_PORT}")
        os.system(f"kill -9 {pid}")
except subprocess.CalledProcessError:
    print("No se pudo obtener el PID o no hay proceso asociado al puerto.")
    
OUTPUT_FILENAME = "Paciente 0X"
OUTPUT_FOLDER = "output_data/vibracion_continua/"

MOTOR_POWER = 250

# Crear una instancia de VibractionContinua
vibracion_continua = VibracionContinua(
    local_udp_ip=LOCAL_UDP_IP,
    shared_port=SHARED_UDP_PORT,
    esp_ips=ESP_IPS,
    struct_format=STRUCT_FORMAT,
    output_folder=OUTPUT_FOLDER,
    output_filename=OUTPUT_FILENAME,
    motor_power=MOTOR_POWER,
)

def back_to_main():
    subprocess.Popen(['python', 'main.py'])  # Abrir main.py
    root.destroy()  # Cerrar vibracion.py

# Función para cerrar la aplicación
def exit_app():
    root.quit()  # Cerrar la aplicación

def create_vibraction_continua_tab(parent):
    """Crea el contenido de la pestaña 1 con la interfaz de control y visualización de ESPs."""
    
    # Configuración de ESPs
    label_texts = [tk.StringVar() for _ in range(vibracion_continua.num_esps)]
    for i, text in enumerate(label_texts):
        text.set(f"Board {i+1} no conectada")

    # Configurar la cuadrícula para que sea flexible
    for i in range(2):  # Supone que habrá 2 columnas
        parent.grid_columnconfigure(i, weight=1)
    for i in range((vibracion_continua.num_esps + 1) // 2):  # Configura las filas necesarias
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
            command=lambda i=i: vibracion_continua.activate_selected_motors([i+1]),
            bg="green",
            fg="white",
            font=("Helvetica", 12),
        )
        button.pack(pady=(5, 10))

        # Determinar las posiciones de acuerdo al número de ESPs
        row, col = new_positions[i]
        
        frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

    # Ordenar los controles adicionales en una columna debajo de los paneles
    start_row = (vibracion_continua.num_esps + 1) // 2  # Comienza justo después de los paneles

    label_output_filename = tk.Label(parent, text="Nombre del archivo")
    label_output_filename.grid(row=start_row + 2, column=0, columnspan=3, pady=(20, 0))
    input_output_filename = tk.Entry(parent, width=50)
    input_output_filename.grid(row=start_row + 3, column=0, columnspan=3, pady=(20, 0))
    input_output_filename.insert(0, OUTPUT_FILENAME)  # Establecer el valor por defecto
    input_output_filename.bind('<KeyRelease>', vibracion_continua.update_output_filename)

    canvas = tk.Canvas(parent, width=20, height=20)
    canvas.grid(row=start_row + 4, column=1, padx=0)
    
    circle = canvas.create_oval(2, 2, 18, 18, fill="white")
    canvas.itemconfig(circle, state="hidden")  # Ocultar el círculo

    record_with_vibration_button = tk.Button(
        parent,
        text="Iniciar registro con vibración",
        command=lambda: vibracion_continua.toggle_recording(record_with_vibration_button, True, back_button, exit_button, canvas, circle, root),
        bg="green",
        fg="white",
    )
    record_with_vibration_button.grid(row=start_row + 4, column=0, columnspan=2, pady=(20, 0))

    record_without_vibration_button = tk.Button(
        parent,
        text="Iniciar registro sin vibración",
        command=lambda: vibracion_continua.toggle_recording(record_without_vibration_button, False, back_button, exit_button, canvas, circle, root),
        bg="green",
        fg="white",
    )
    record_without_vibration_button.grid(row=start_row + 5, column=0, columnspan=2, pady=(20, 0))

    # Botón "Volver" para regresar a la ventana principal de selección
    back_button = tk.Button(
        parent,
        text="Volver",
        command=lambda: back_to_main(),
        bg="red",
        fg="white",
        font=("Helvetica", 14),
    )
    back_button.grid(row=start_row + 6, column=0, columnspan=2, pady=20)

    exit_button = tk.Button(
        parent, 
        text="Salir", 
        font=("Helvetica", 14),
        bg="red", 
        fg="white",
        command=exit_app  # Llamar a la función exit_app al hacer clic en "Exit"
    )
    exit_button.grid(row=start_row + 7, column=0, columnspan=2, pady=20)

    # Configurar threads para la recepción de datos y actualización de la GUI
    receive_thread = threading.Thread(target=vibracion_continua.receive_data)
    receive_thread.daemon = True
    receive_thread.start()

    update_thread = threading.Thread(target=vibracion_continua.update_gui, args=(label_texts, root))

    update_thread.daemon = True
    update_thread.start()


# Crear la nueva ventana
root = tk.Tk()
root.protocol("WM_DELETE_WINDOW", lambda: None)
root.title("Vibración continua")
root.configure(bg="white")
root.option_add("*Font", "Helvetica 20")

window_width, window_height = 1000, 1200
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
position_x = (screen_width - window_width) // 2
position_y = (screen_height - window_height) // 2
root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")

# Crear la pestaña de vibración continua
app = tk.Frame(root)
create_vibraction_continua_tab(app)
app.pack(fill="both", expand=True)
root.mainloop()