import tkinter as tk
import threading
from utils import AutomaticVibration  # Asegúrate de que esta importación sea correcta
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

OUTPUT_FILENAME = "Paciente 0X"
OUTPUT_FOLDER = "output_data/fsr/"

READING_MODE = True

THY = 1500
VD = 250  # 500 vibration duration
MOTOR_POWER = 250 # 70
VIBRATION_OFFSET=0


# Crear una instancia de FSR
fsr = AutomaticVibration(
    local_udp_ip=LOCAL_UDP_IP,
    shared_port=SHARED_UDP_PORT,
    esp_ips=ESP_IPS,
    struct_format=STRUCT_FORMAT,
    output_folder=OUTPUT_FOLDER,
    output_filename=OUTPUT_FILENAME,
    thy=THY,
    vd=VD,
    motor_power=MOTOR_POWER,
    vibration_offset=VIBRATION_OFFSET,
    reading_mode=READING_MODE
)

def back_to_main():
    subprocess.Popen(['python', 'main.py'])  # Abrir main.py
    root.destroy()  # Cerrar vibracion.py

# Función para cerrar la aplicación
def exit_app():
    root.quit()  # Cerrar la aplicación

def create_automatic_vibration_tab(parent, root):
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
    panels = []
    # Crear y ubicar los paneles con botones
    for i, text in enumerate(label_texts):
        frame = tk.Frame(parent, padx=5, pady=5, borderwidth=2, relief="solid", bg="white")
        
        # Label dentro del frame
        label = tk.Label(frame, textvariable=text, bg="white")
        label.pack(pady=(10, 5), expand=True, fill='both')
        panels.append(frame)  # Guardamos los frames en una lista

        # Botón dentro del frame
        '''
        button = tk.Button(
            frame,
            text=f"Activar vibrador",
            command=lambda i=i: fsr.activate_selected_motors([i+1]),
            bg="green",
            fg="white",
            font=("Helvetica", 12),
        )
        button.pack(pady=(5, 10))
        '''

        # Determinar las posiciones de acuerdo al número de ESPs
        row, col = new_positions[i]
        
        frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

    # Ordenar los controles adicionales en una columna debajo de los paneles
    start_row = (fsr.num_esps + 1) // 2    
    
    label_output_filename = tk.Label(parent, text="Nombre del archivo", bg="white")
    label_output_filename.grid(row=start_row + 2, column=0, columnspan=3, pady=20)
    input_output_filename = tk.Entry(parent, width=50)
    input_output_filename.grid(row=start_row + 3, column=0, columnspan=3, pady=(20, 0))
    input_output_filename.insert(0, OUTPUT_FILENAME)  # Establecer el valor por defecto
    input_output_filename.bind('<KeyRelease>', fsr.update_output_filename)
    
    # Botón "Volver" para regresar a la ventana principal de selección
    back_button = tk.Button(
        parent,
        text="Volver al menú principal",
        command=lambda: back_to_main(),
        font=("Helvetica", 18),
    )
    back_button.grid(row=start_row + 5, column=0, columnspan=2, pady=(40, 0))

    exit_button = tk.Button(
        parent, 
        text="Salir", 
        font=("Helvetica", 18),
        command=exit_app  # Llamar a la función exit_app al hacer clic en "Exit"
    )
    exit_button.grid(row=start_row + 6, column=0, columnspan=2, pady=(10, 40))

    canvas = tk.Canvas(parent, width=20, height=20, bg="white")
    canvas.grid(row=start_row + 4, column=1, padx=(0, 200), pady=(50, 0))
    
    circle = canvas.create_oval(2, 2, 18, 18, fill="white")
    canvas.itemconfig(circle, state="hidden")  # Ocultar el círculo
    record_button = tk.Button(
        parent,
        text="Iniciar registro",
        command=lambda: fsr.toggle_recording(record_button, back_button, exit_button, canvas, circle, root, panels),
        bg="green",
        fg="white",
    )
    record_button.grid(row=start_row + 4, column=0, columnspan=3, pady=(100, 50))


    # Configurar threads para la recepción de datos y actualización de la GUI
    receive_thread = threading.Thread(target=fsr.receive_data, args=(panels, ))
    receive_thread.daemon = True
    receive_thread.start()

    update_thread = threading.Thread(target=fsr.update_gui, args=(label_texts, root, record_button))

    update_thread.daemon = True
    update_thread.start()

# Crear la nueva ventana
root = tk.Tk()
root.protocol("WM_DELETE_WINDOW", lambda: None)
root.title("Vibración automática")
root.configure(bg="white")
root.option_add("*Font", "Helvetica 20")

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
window_width = int(screen_width * 0.5)
window_height = int(screen_height)
x = (screen_width - window_width) // 2
y = (screen_height - window_height) // 2
root.geometry(f"{window_width}x{window_height}+{x}+{y}")

# Crear la pestaña de FSR
app = tk.Frame(root)
app.configure(bg="white")
create_automatic_vibration_tab(app, root)
app.pack(fill="both", expand=True)
root.mainloop()
