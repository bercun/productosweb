import tkinter as tk
from tkinter import ttk, messagebox  # Componentes adicionales de tkinter
import sqlite3  # Para manejo de base de datos SQLite
import requests  # Para realizar peticiones HTTP
from bs4 import BeautifulSoup  # Para análisis de HTML
import threading  # Para ejecutar tareas en segundo plano

class DatabaseConnection:
    """Clase para manejar la conexión a la base de datos de forma segura usando context manager"""
    def __init__(self, db_name='webscraper.db'):
        self.db_name = db_name

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_name)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

class WebScraperGUI:
    """Clase principal que implementa la interfaz gráfica del Web Scraper"""
    def __init__(self, root):
        # Configuración inicial de la ventana
        self.root = root
        self.root.title("Web Scraper")
        self.root.geometry("800x600")

        # Inicialización de la base de datos
        self.create_database()

        # Configuración del frame principal
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Campo de entrada para URL
        ttk.Label(self.main_frame, text="URL:").grid(row=0, column=0, sticky=tk.W)
        self.url_entry = ttk.Entry(self.main_frame, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5)

        # Campo de entrada para selector CSS
        ttk.Label(self.main_frame, text="Selector CSS:").grid(row=1, column=0, sticky=tk.W)
        self.selector_entry = ttk.Entry(self.main_frame, width=50)
        self.selector_entry.grid(row=1, column=1, padx=5, pady=5)

        # Configuración de botones
        ttk.Button(self.main_frame, text="Agregar URL", command=self.add_url).grid(row=0, column=2, padx=5)
        ttk.Button(self.main_frame, text="Iniciar Scraping", command=self.start_scraping).grid(row=1, column=2, padx=5)

        # Lista de URLs y selectores guardados
        self.url_list = ttk.Treeview(self.main_frame, columns=("URL", "Selector"), show="headings")
        self.url_list.heading("URL", text="URL")
        self.url_list.heading("Selector", text="Selector CSS")
        self.url_list.grid(row=2, column=0, columnspan=3, pady=10)

        # Área de resultados
        ttk.Label(self.main_frame, text="Resultados:").grid(row=3, column=0, sticky=tk.W)
        self.results_text = tk.Text(self.main_frame, height=10, width=70)
        self.results_text.grid(row=4, column=0, columnspan=3, pady=5)

        # Carga inicial de URLs existentes
        self.load_urls()

    def create_database(self):
        """Crea las tablas necesarias en la base de datos si no existen"""
        with DatabaseConnection() as conn:
            c = conn.cursor()
            # Tabla para almacenar URLs y selectores
            c.execute('''CREATE TABLE IF NOT EXISTS urls
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         url TEXT NOT NULL,
                         selector TEXT NOT NULL)''')
            # Tabla para almacenar resultados del scraping
            c.execute('''CREATE TABLE IF NOT EXISTS results
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         url_id INTEGER,
                         result TEXT,
                         timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                         FOREIGN KEY(url_id) REFERENCES urls(id))''')
            conn.commit()

    def add_url(self):
        """Agrega una nueva URL y su selector a la base de datos y la lista visual"""
        url = self.url_entry.get()
        selector = self.selector_entry.get()
        
        if url and selector:
            with DatabaseConnection() as conn:
                c = conn.cursor()
                c.execute("INSERT INTO urls (url, selector) VALUES (?, ?)", (url, selector))
                conn.commit()
            
            self.url_list.insert('', 'end', values=(url, selector))
            self.url_entry.delete(0, tk.END)
            self.selector_entry.delete(0, tk.END)
        else:
            messagebox.showerror("Error", "Por favor ingrese URL y selector CSS")

    def load_urls(self):
        """Carga las URLs existentes desde la base de datos"""
        with DatabaseConnection() as conn:
            c = conn.cursor()
            c.execute("SELECT url, selector FROM urls")
            for url, selector in c.fetchall():
                self.url_list.insert('', 'end', values=(url, selector))

    def scrape_url(self, url, selector):
        """Realiza el web scraping de una URL específica usando su selector"""
        try:
            response = requests.get(url, timeout=10)  # Timeout de 10 segundos
            soup = BeautifulSoup(response.text, 'html.parser')
            results = soup.select(selector)
            return [result.text.strip() for result in results]
        except Exception as e:
            return [f"Error: {str(e)}"]

    def start_scraping(self):
        """Inicia el proceso de scraping en un hilo separado"""
        def scrape_thread():
            # Limpia resultados anteriores
            self.results_text.delete(1.0, tk.END)
            
            # Procesa cada URL en la lista
            for item in self.url_list.get_children():
                url, selector = self.url_list.item(item)['values']
                results = self.scrape_url(url, selector)
                
                with DatabaseConnection() as conn:
                    c = conn.cursor()
                    c.execute("SELECT id FROM urls WHERE url=?", (url,))
                    url_id = c.fetchone()[0]
                    
                    for result in results:
                        c.execute("INSERT INTO results (url_id, result) VALUES (?, ?)", 
                                (url_id, result))
                        self.results_text.insert(tk.END, f"URL: {url}\nResultado: {result}\n\n")
                    conn.commit()

        # Inicia el scraping en un hilo separado para no bloquear la interfaz
        threading.Thread(target=scrape_thread, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = WebScraperGUI(root)
    root.mainloop()