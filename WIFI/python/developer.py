import tkinter as tk
import queue
import threading
from utils import Developer  # Asegúrate de que esta importación sea correcta
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
OUTPUT_FOLDER = "output_data/testing/"

READING_MODE = True

THY = 3000
VD = 1000  # 500 vibration duration
MOTOR_POWER = 250 # 70
VIBRATION_OFFSET = 0

# Crear una instancia de FSR
developer = Developer(
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

def create_developer_tab(parent, root):
    """Crea el contenido de la pestaña 1 con la interfaz de control y visualización de ESPs."""
    
    # Configuración de ESPs
    label_texts = [tk.StringVar() for _ in range(developer.num_esps)]
    for i, text in enumerate(label_texts):
        text.set(f"Board {i+1} no conectada")

    # Configurar la cuadrícula para que sea flexible
    for i in range(2):
        parent.grid_columnconfigure(i, weight=1)
    for i in range((developer.num_esps + 1) // 2):
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
        button = tk.Button(
            frame,
            text=f"Activar vibrador",
            command=lambda i=i: developer.activate_selected_motors([i+1]),
            bg="green",
            fg="white",
            font=("Helvetica", 12),
        )
        button.pack(pady=(5, 10))

        # Determinar las posiciones de acuerdo al número de ESPs
        row, col = new_positions[i]
        
        frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

    # Ordenar los controles adicionales en una columna debajo de los paneles
    start_row = (developer.num_esps + 1) // 2    
    
    label_output_filename = tk.Label(parent, text="Nombre del archivo", bg="white")
    label_output_filename.grid(row=start_row + 0, column=1, columnspan=1, pady=20)
    input_output_filename = tk.Entry(parent, width=30)
    input_output_filename.grid(row=start_row + 1, column=1, columnspan=1, pady=20)
    input_output_filename.insert(0, OUTPUT_FILENAME)  # Establecer el valor por defecto
    input_output_filename.bind('<KeyRelease>', developer.update_output_filename)
    
    # Botón "Volver" para regresar a la ventana principal de selección
    back_button = tk.Button(
        parent,
        text="Volver al menú principal",
        command=lambda: back_to_main(),
        font=("Helvetica", 18),
    )
    back_button.grid(row=start_row + 6, column=1, columnspan=1, pady=20)

    exit_button = tk.Button(
        parent, 
        text="Salir", 
        font=("Helvetica", 18),
        command=exit_app  # Llamar a la función exit_app al hacer clic en "Exit"
    )
    exit_button.grid(row=start_row + 7, column=1, columnspan=1, pady=20)

    canvas = tk.Canvas(parent, width=20, height=20, bg="white")
    canvas.grid(row=start_row + 2, column=1, padx=0)
    
    circle = canvas.create_oval(2, 2, 18, 18, fill="white")
    canvas.itemconfig(circle, state="hidden")  # Ocultar el círculo
    record_button = tk.Button(
        parent,
        text="Iniciar registro",
        command=lambda: developer.toggle_recording(record_button, back_button, exit_button, canvas, circle, root, panels),
        bg="green",
        fg="white",
    )
    record_button.grid(row=start_row + 2, column=1, columnspan=1, pady=20)


    # Configurar threads para la recepción de datos y actualización de la GUI
    receive_thread = threading.Thread(target=developer.receive_data, args=(panels, ))
    receive_thread.daemon = True
    receive_thread.start()

    update_thread = threading.Thread(target=developer.update_gui, args=(label_texts, root, record_button))

    update_thread.daemon = True
    update_thread.start()

    
    all_motors_button = tk.Button(
        parent,
        text="Activar todos",
        command=lambda: developer.activate_selected_motors(developer.esp_indexes),
        bg="green",
        fg="white",
    )
    all_motors_button.grid(row=start_row + 0, column=0, columnspan=1, pady=(20, 0))

    all_motors_stop_button = tk.Button(
        parent,
        text="Detener todos",
        command=lambda: developer.stop_selected_motors(developer.esp_indexes),
        bg="red",
        fg="white",
    )
    all_motors_stop_button.grid(row=start_row + 1, column=0, columnspan=1, pady=(20, 0))

    # Configurar los sliders y demás controles
    vd_slider_label = tk.Label(parent, text="Duración vibración [ms]", bg="white")
    vd_slider_label.grid(row=start_row + 2, column=0, columnspan=1, pady=(20, 0))

    vd_slider = tk.Scale(
        parent,
        from_=10,
        resolution=10,
        to=10000,
        orient="horizontal",
        length=200,
        bg="white"
    )
    vd_slider.set(developer.vd)
    vd_slider.bind(
        "<ButtonRelease-1>",
        lambda event: developer.update_vd(vd_slider.get())
    )
    vd_slider.grid(row=start_row + 3, column=0, columnspan=1)


    # Slider para acc_y_threshold (ThY)
    thy_slider_label = tk.Label(parent, text="Umbral FSR", bg="white")
    thy_slider_label.grid(row=start_row + 4, column=0, columnspan=1, pady=(20, 0))

    thy_slider = tk.Scale(
        parent,
        from_=10,
        resolution=1,
        to=4095,
        orient="horizontal",
        length=200,
        bg="white"
    )
    thy_slider.set(developer.thy)
    thy_slider.bind(
        "<ButtonRelease-1>",
        lambda event: developer.update_thy(thy_slider.get())
    )
    thy_slider.grid(row=start_row + 5, column=0, columnspan=1)

    # Slider para acc_y_threshold (ThY)
    delay_slider_label = tk.Label(parent, text="Delay vibración [ms]", bg="white")
    delay_slider_label.grid(row=start_row + 6, column=0, columnspan=1, pady=(20, 0))

    delay_slider = tk.Scale(
        parent,
        from_=0,
        resolution=10,
        to=2000,
        orient="horizontal",
        length=200,
        bg="white"
    )
    delay_slider.set(developer.vibration_offset)
    delay_slider.bind(
        "<ButtonRelease-1>",
        lambda event: developer.update_vibration_offset(delay_slider.get())
    )
    delay_slider.grid(row=start_row + 7, column=0, columnspan=1)

# Crear la nueva ventana
root = tk.Tk()
root.protocol("WM_DELETE_WINDOW", lambda: None)
root.title("Modo Desarrollador")
root.configure(bg="white")
root.option_add("*Font", "Helvetica 20")

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
window_width = int(screen_width * 0.9)
window_height = int(screen_height)
x = (screen_width - window_width) // 2
y = (screen_height - window_height) // 2
root.geometry(f"{window_width}x{window_height}+{x}+{y}")

# Crear la pestaña de FSR
app = tk.Frame(root)
app.configure(bg="white")
create_developer_tab(app, root)
app.pack(fill="both", expand=True)
root.mainloop()
