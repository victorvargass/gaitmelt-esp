import tkinter as tk
from tkinter import ttk
from vibracion_continua import create_vibraction_continua_tab
from fsr import create_fsr_tab

# Configuración de la ventana principal
root = tk.Tk()
root.title("Interfaz con Tabs")
root.configure(bg="white")
root.option_add("*Font", "Helvetica 20")
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.geometry(f"{screen_width}x{screen_height}")

# Configurar el estilo de las pestañas
style = ttk.Style()
style.configure("TNotebook.Tab", font=("Helvetica", 16), padding=[10, 5])  # Aumenta tamaño de fuente y padding

# Crear un Notebook para las pestañas
notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

# Crear los contenedores para las pestañas
tab1 = tk.Frame(notebook)
tab2 = tk.Frame(notebook)

# Añadir las pestañas al Notebook
notebook.add(tab1, text="Vibración continua")
notebook.add(tab2, text="FSR")

# Llamar a funciones en tab1.py y tab2.py para añadir contenido
create_vibraction_continua_tab(tab1)
create_fsr_tab(tab2)

# Ejecutar la interfaz
root.mainloop()
