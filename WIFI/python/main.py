import tkinter as tk
import subprocess
import os

LOCAL_UDP_IP = "192.168.50.82"
SHARED_UDP_PORT = 4210

cmd = f"lsof -i :{SHARED_UDP_PORT} | grep -v 'PID' | awk '{{print $2}}'"
try:
    pid = subprocess.check_output(cmd, shell=True).decode().strip()
    if pid:
        os.system(f"kill -9 {pid}")
    else:
        pass
except subprocess.CalledProcessError:
    print("No se pudo obtener el PID o no hay proceso asociado al puerto.")

# Variable global para el proceso en ejecución
current_process = None

# Función para ejecutar un script y cerrar el actual
def run_script(script_name):
    global current_process
    stop_script()  # Detener cualquier script actual
    current_process = subprocess.Popen(['python', script_name])  # Ejecutar nuevo script
    root.after(100, root.quit)  # Cerrar la ventana de main después de iniciar el script

# Función para detener el proceso en ejecución
def stop_script():
    global current_process
    if current_process is not None:
        current_process.terminate()  # Terminar el proceso actual
        current_process = None

# Función para cerrar la aplicación
def exit_app():
    stop_script()  # Asegurarse de detener cualquier script en ejecución
    root.quit()  # Cerrar la aplicación

# Configuración de la ventana principal
root = tk.Tk()
root.protocol("WM_DELETE_WINDOW", lambda: None)
root.resizable(False, False)
root.title("Selecciona una opción")
root.configure(bg="white")
window_width, window_height = 1200, 600

# Calcular posición para centrar la ventana en la pantalla
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
position_x = (screen_width - window_width) // 2
position_y = (screen_height - window_height) // 2
root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")  # Centrar ventana

# Cargar la imagen (asegurarse de tener la imagen en el directorio correcto)
logo = tk.PhotoImage(file="src/leufulab.png")
logo = logo.subsample(10, 10)

model = tk.PhotoImage(file="src/model.png")
model = model.subsample(3, 3)

# Crear un Frame para el texto y los botones
main_frame = tk.Frame(root, bg="white")
main_frame.pack(expand=True)

# Colocar la imagen arriba de todo
model_label = tk.Label(main_frame, image=model, bg="white")
model_label.place(x=-30, y=0)

logo_label = tk.Label(main_frame, image=logo, bg="white")
logo_label.pack(pady=20)

# Crear un Label para el texto "Seleccionar tarea"
label_tarea = tk.Label(main_frame, text="Seleccionar tarea", font=("Helvetica", 24), bg="white")
label_tarea.pack(pady=20)

# Crear un Frame para los botones en horizontal
button_frame = tk.Frame(main_frame, bg="white")
button_frame.pack(pady=20)

# Crear los botones con funciones lambda para ejecutar los scripts solo al hacer clic
button_vibracion_continua = tk.Button(
    button_frame, 
    text="Vibración manual", 
    font=("Helvetica", 20),
    bg="#4CAF50", 
    fg="white", 
    width=20, 
    height=2,
    command=lambda: run_script("vibracion_continua.py")  # Usar lambda para evitar ejecución inmediata
)

button_fsr = tk.Button(
    button_frame, 
    text="Vibración con detección", 
    font=("Helvetica", 20),
    bg="#008CBA", 
    fg="white", 
    width=20, 
    height=2,
    command=lambda: run_script("fsr.py")  # Usar lambda para evitar ejecución inmediata
)

button_fsr_avanzado = tk.Button(
    button_frame, 
    text="Vibración con detección avanzada", 
    font=("Helvetica", 20),
    bg="#008CBA", 
    fg="white", 
    width=20, 
    height=2,
    command=lambda: run_script("fsr_avanzada.py")  # Usar lambda para evitar ejecución inmediata
)

# Colocar los botones horizontalmente
button_vibracion_continua.pack(side="left", padx=20)
button_fsr.pack(side="left", padx=20)
button_fsr_avanzado.pack(side="left", padx=20)
button_fsr_avanzado.config(state="disabled")

# Crear y posicionar el botón "Exit" en un frame inferior
exit_button_frame = tk.Frame(root, bg="white")
exit_button_frame.pack(side="bottom", pady=20)

button_exit = tk.Button(
    exit_button_frame, 
    text="Salir", 
    font=("Helvetica", 24),
    bg="red", 
    fg="white", 
    width=20, 
    height=2,
    command=exit_app  # Llamar a la función exit_app al hacer clic en "Exit"
)
button_exit.pack()

# Agregar el texto de la versión en la esquina superior derecha
version_label = tk.Label(root, text="Versión 2.2.01", font=("Helvetica", 16), bg="white", fg="black")
version_label.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)  # Ajustar posición cerca de la esquina

# Ejecutar la interfaz
root.mainloop()
