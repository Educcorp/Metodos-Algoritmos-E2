# -*- coding: utf-8 -*-
"""
MODELO DE TRANSPORTE — Ventana del programa
    SFBI:         Esquina Noroeste · Costo Mínimo · Vogel
    Optimización: Banquillo (Pasos Secuenciales) · DIMO (Distribución Modificada)

Ejecución: doble clic sobre este archivo, o bien   py ModeloTransporte.pyw

tkinter se usa para la ventana y matplotlib para dibujar las tablas.
Todos los cálculos están en motor.py, sin librerías.

Uso:
  1. Elegir el método, Minimizar/Maximizar, número de orígenes y de destinos.
     (En Banquillo y DIMO se elige también con qué método sacar la SFBI.)
  2. Presionar "Crear tabla" y escribir los costos cij, las ofertas ai y las
     demandas bj. Se aceptan 3, 2.5, 3/4, y M para una ruta inaceptable.
  3. Presionar "Resolver": abajo aparecen los pasos y el resultado.
     "Comparar los 5" resuelve con todos los métodos y arma un cuadro.

=============================================================================
  ÍNDICE PARA EXPONER  (copiar la etiqueta y buscarla con Ctrl+F)
=============================================================================
    #VENTANA-01  __init__()          Menú de métodos, Min/Max, tamaño del problema
    #VENTANA-02  crear_casillas()    Casillas de costos, ofertas y demandas
    #VENTANA-03  resolver()          Lee las casillas y llama al motor (motor.py)
    #VENTANA-04  figura_tabla()      Dibuja la tabla de transporte con matplotlib

  Los métodos (#MEN-01, #MCM-01, #MAV-01, #BANQUILLO-01, #DIMO-01...) están
  en motor.py.
=============================================================================
"""

import tkinter as tk
from tkinter import messagebox, scrolledtext
from io import BytesIO

from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

import motor

# Colores de las tablas (los mismos del programa de Programación Lineal)
ENCABEZADO = "#2F3E66"      # fila y columna de títulos
MAS = "#DCE8FF"             # celda con signo + de la trayectoria
MENOS = "#FFE9C7"           # celda con signo - de la trayectoria
PIVOTE = "#F4A62A"          # celda que se acaba de asignar / ruta que entra
TOTALES = "#EEF0F4"         # oferta, demanda, penalidades, ui, vj
TACHADO = "#E4E6EB"         # renglón o columna tachado
BORDE = "#C8CDD8"
NEGATIVO = "#C0392B"        # costo marginal negativo (todavía no es óptima)

# Ejemplo RPG de las diapositivas (puertos -> plantas)
EJEMPLO = {"costos": [["12", "13", "4", "6"], ["6", "4", "10", "11"], ["10", "9", "12", "4"]],
           "oferta": ["500", "700", "800"], "demanda": ["400", "900", "200", "500"]}

METODOS = [("men", "Esquina Noroeste"), ("mcm", "Costo Mínimo"), ("mav", "Vogel"),
           ("banquillo", "Banquillo"), ("dimo", "DIMO")]
SFBI = [("men", "Esquina Noroeste"), ("mcm", "Costo Mínimo"), ("mav", "Vogel")]


class App(tk.Tk):

    # =========================================================================
    #   #VENTANA-01   __init__() — menú de métodos y datos del problema
    #
    #   Variables:
    #     self.metodo   -> método elegido: 'men', 'mcm', 'mav', 'banquillo', 'dimo'
    #     self.sfbi     -> nombre del método de la SFBI para Banquillo y DIMO
    #     self.sentido  -> 'min' (costos) o 'max' (beneficios)
    #     self.m        -> número de orígenes (O1 ... Om)
    #     self.n        -> número de destinos (D1 ... Dn)
    #     menu          -> recuadro con las opciones del método
    #     clave         -> nombre interno del método (el que usa motor.py)
    #     nombre        -> texto que ve el usuario en el menú
    #     conf          -> fila con Min/Max, orígenes, destinos y "Crear tabla"
    #     self.op_sfbi  -> menú para elegir la SFBI (sólo activo en Banquillo/DIMO)
    #     self.marco    -> recuadro donde van las casillas del problema
    #     botones       -> fila de botones Resolver / Comparar / Ejemplo
    #     self.texto    -> área donde se muestran los pasos y el resultado
    #     self.lienzos  -> imágenes de las tablas (se guardan para que no las borre
    #                      el recolector de basura de Python)
    # =========================================================================
    def __init__(self):
        super().__init__()
        self.title("Modelo de Transporte - MEN, MCM, Vogel, Banquillo y DIMO")
        self.metodo = tk.StringVar(value="men")
        self.sfbi = tk.StringVar(value=SFBI[0][1])
        self.sentido = tk.StringVar(value="min")
        self.m = tk.IntVar(value=3)         # número de orígenes
        self.n = tk.IntVar(value=4)         # número de destinos

        # ---- Menú de métodos (la clave es el nombre que usa motor.resolver)
        menu = tk.LabelFrame(self, text="Método", padx=5, pady=5)
        menu.pack(fill="x", padx=10, pady=5)
        tk.Label(menu, text="SFBI:").pack(side="left")
        for clave, nombre in METODOS[:3]:
            tk.Radiobutton(menu, text=nombre, variable=self.metodo, value=clave,
                           command=self.cambiar_metodo).pack(side="left", padx=5)
        tk.Label(menu, text="     Solución óptima:").pack(side="left")
        for clave, nombre in METODOS[3:]:
            tk.Radiobutton(menu, text=nombre, variable=self.metodo, value=clave,
                           command=self.cambiar_metodo).pack(side="left", padx=5)
        tk.Label(menu, text="   partiendo de:").pack(side="left")
        self.op_sfbi = tk.OptionMenu(menu, self.sfbi, *[nombre for _, nombre in SFBI])
        self.op_sfbi.pack(side="left")

        # ---- Tipo de problema y tamaño
        conf = tk.Frame(self)
        conf.pack(fill="x", padx=10)
        tk.Radiobutton(conf, text="Minimizar (costos)", variable=self.sentido,
                       value="min").pack(side="left")
        tk.Radiobutton(conf, text="Maximizar (beneficios)", variable=self.sentido,
                       value="max").pack(side="left")
        tk.Label(conf, text="   Orígenes:").pack(side="left")
        tk.Spinbox(conf, from_=1, to=10, width=3, textvariable=self.m,
                   state="readonly").pack(side="left")
        tk.Label(conf, text="   Destinos:").pack(side="left")
        tk.Spinbox(conf, from_=1, to=10, width=3, textvariable=self.n,
                   state="readonly").pack(side="left")
        tk.Button(conf, text="Crear tabla", command=self.crear_casillas).pack(side="left", padx=10)
        tk.Label(conf, text="Se acepta: 3,  2.5,  3/4  y  M (ruta inaceptable)",
                 fg="#555").pack(side="left", padx=10)

        # ---- Casillas del problema (se llenan en crear_casillas)
        self.marco = tk.LabelFrame(self, text="Tabla de transporte (forma matricial)",
                                   padx=5, pady=5)
        self.marco.pack(fill="x", padx=10, pady=5)

        botones = tk.Frame(self)
        botones.pack(pady=5)
        tk.Button(botones, text="Resolver", width=15, command=self.resolver).pack(side="left", padx=5)
        tk.Button(botones, text="Comparar los 5", width=15,
                  command=lambda: self.resolver(comparar=True)).pack(side="left", padx=5)
        tk.Button(botones, text="Cargar ejemplo RPG", width=18,
                  command=self.cargar_ejemplo).pack(side="left", padx=5)

        # ---- Área donde se muestran los pasos (texto + tablas)
        self.texto = scrolledtext.ScrolledText(self, width=120, height=30, font=("Segoe UI", 10))
        self.texto.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.texto.tag_configure("titulo", font=("Segoe UI", 11, "bold"))
        self.lienzos = []                   # imágenes de las tablas (referencias vivas)

        self.crear_casillas()
        self.cambiar_metodo()

    def cambiar_metodo(self):
        """El menú de la SFBI sólo se usa en Banquillo y DIMO."""
        activo = self.metodo.get() in ("banquillo", "dimo")
        self.op_sfbi.config(state="normal" if activo else "disabled")

    def casilla(self, fila, columna):
        """Crea una casilla de texto para un número en la posición indicada."""
        e = tk.Entry(self.marco, width=7, justify="center")
        e.grid(row=fila, column=columna, padx=2, pady=2)
        return e

    # =========================================================================
    #   #VENTANA-02   crear_casillas() — costos cij, ofertas ai y demandas bj
    #
    #   Variables:
    #     m, n         -> número de orígenes y de destinos elegidos
    #     i            -> número de origen (O1, O2, ...)
    #     j            -> número de destino (D1, D2, ...)
    #     self.c       -> casillas de los costos: self.c[i][j] = cij
    #     self.a       -> casillas de la oferta de cada origen (ai)
    #     self.b       -> casillas de la demanda de cada destino (bj)
    #     fila         -> casillas de los costos de UN origen
    # =========================================================================
    def crear_casillas(self):
        """Dibuja la forma matricial:  renglones O1..Om, columnas D1..Dn, Oferta y Demanda."""
        for w in self.marco.winfo_children():
            w.destroy()
        m, n = self.m.get(), self.n.get()

        for j in range(n):
            tk.Label(self.marco, text="D%d" % (j + 1), font=("Segoe UI", 9, "bold")
                     ).grid(row=0, column=1 + j)
        tk.Label(self.marco, text="Oferta (ai)", font=("Segoe UI", 9, "bold")
                 ).grid(row=0, column=n + 1, padx=(10, 0))

        self.c, self.a = [], []
        for i in range(m):
            tk.Label(self.marco, text="O%d" % (i + 1), font=("Segoe UI", 9, "bold")
                     ).grid(row=1 + i, column=0, padx=(0, 5))
            fila = [self.casilla(1 + i, 1 + j) for j in range(n)]
            self.c.append(fila)
            self.a.append(self.casilla(1 + i, n + 1))
            self.a[-1].grid_configure(padx=(10, 2))

        tk.Label(self.marco, text="Demanda (bj)", font=("Segoe UI", 9, "bold")
                 ).grid(row=m + 1, column=0, padx=(0, 5), pady=(6, 0))
        self.b = [self.casilla(m + 1, 1 + j) for j in range(n)]
        for e in self.b:
            e.grid_configure(pady=(6, 2))

    def cargar_ejemplo(self):
        """Llena las casillas con el ejemplo RPG (3 puertos, 4 plantas)."""
        self.m.set(3)
        self.n.set(4)
        self.sentido.set("min")
        self.crear_casillas()
        for fila, valores in zip(self.c, EJEMPLO["costos"]):
            for e, v in zip(fila, valores):
                e.insert(0, v)
        for e, v in zip(self.a, EJEMPLO["oferta"]):
            e.insert(0, v)
        for e, v in zip(self.b, EJEMPLO["demanda"]):
            e.insert(0, v)

    @staticmethod
    def leer(casilla, costo=False):
        """Lee una casilla (vacía = 0). Los costos pueden ser M."""
        texto = casilla.get().strip() or "0"
        return motor.leer_costo(texto) if costo else motor.leer_numero(texto)

    # =========================================================================
    #   #VENTANA-03   resolver() — lee el problema y llama al motor
    #
    #   Variables:
    #     comparar  -> True si se presionó "Comparar los 5"
    #     costos    -> matriz cij ya convertida (ExprM, puede tener M)
    #     oferta    -> lista ai ya convertida a fracción
    #     demanda   -> lista bj ya convertida a fracción
    #     sfbi      -> clave del método de la SFBI ('men', 'mcm', 'mav')
    #     prob      -> problema completo que se manda al motor
    #     pasos     -> lo que devuelve el motor: textos y tablas (dict)
    #     paso      -> cada uno de esos pasos
    #     titulo    -> True si el texto es un título (se escribe en negritas)
    # =========================================================================
    def resolver(self, comparar=False):
        """Lee el problema de las casillas, lo resuelve con motor.py y muestra los pasos."""
        try:
            costos = [[self.leer(e, costo=True) for e in fila] for fila in self.c]
            oferta = [self.leer(e) for e in self.a]
            demanda = [self.leer(e) for e in self.b]
        except ValueError:
            messagebox.showerror("Error", "Solo se permiten números: enteros (4), "
                                          "decimales (2.5), fracciones (3/4) o M en los costos.")
            return
        if any(v < 0 for v in oferta + demanda):
            messagebox.showerror("Error", "Las ofertas y demandas no pueden ser negativas.")
            return
        if sum(oferta, motor.Fraccion(0)) == 0 or sum(demanda, motor.Fraccion(0)) == 0:
            messagebox.showerror("Error", "Escriba las ofertas y las demandas.")
            return
        sfbi = next(clave for clave, nombre in SFBI if nombre == self.sfbi.get())
        prob = {"sentido": self.sentido.get(), "costos": costos,
                "oferta": oferta, "demanda": demanda, "sfbi": sfbi}

        # Borrar la solución anterior (al borrar el texto también se borran sus imágenes).
        self.texto.config(state="normal")
        self.texto.delete("1.0", "end")
        self.lienzos = []

        # Aquí se ejecuta el método elegido (en motor.py: #RESOLVER).
        pasos = motor.comparar(prob) if comparar else motor.resolver(self.metodo.get(), prob)
        for paso in pasos:
            if isinstance(paso, dict):
                self.insertar_figura(figura_tabla(paso))
            else:
                titulo = paso.lstrip().startswith(("---", "===", "RESULTADO"))
                self.texto.insert("end", paso + "\n", "titulo" if titulo else "")
        self.texto.config(state="disabled")     # solo lectura

    def insertar_figura(self, fig):
        """Convierte la figura a PNG y la inserta como imagen en el área de resultados
        (así no queda un widget vivo que haya que redibujar en cada scroll)."""
        buffer = BytesIO()
        fig.savefig(buffer, format="png")
        imagen = tk.PhotoImage(data=buffer.getvalue())
        self.texto.image_create("end", image=imagen)
        self.texto.insert("end", "\n")
        self.lienzos.append(imagen)             # referencia viva (si no, Tk la borra)


# =============================================================================
#   #VENTANA-04   figura_tabla() — tabla de transporte con matplotlib
#
#   Cada celda de ruta se dibuja como en las diapositivas: el costo cij en un
#   cuadrito arriba a la derecha y las unidades xij grandes en el centro.
#   En Banquillo/DIMO las celdas NO usadas muestran su costo marginal (rojo
#   si es negativo) y la trayectoria lleva sus signos + y -.
#
#   Variables:
#     foto        -> datos de la tabla que manda el motor (foto_tabla)
#     m, n        -> número de orígenes y destinos
#     columnas    -> títulos de columna: D1..Dn, Oferta, [Resta], [Penalidad], [ui]
#     renglones   -> títulos de renglón: O1..Om, Demanda, [Resta], [Penalidad], [vj]
#     AN, AL      -> ancho y alto de una celda;  AN0 -> ancho de la columna de títulos
#     fig, ax     -> la figura de matplotlib y su área de dibujo
#     signo       -> {(i, j): '+' o '-'} de la trayectoria
#     tach_f/c    -> renglones / columnas tachados
#     x0, y0      -> esquina superior izquierda de la celda que se dibuja
#     fondo       -> color de fondo de la celda
#     extra_f     -> valores extra de cada renglón (oferta, resta, penalidad, ui)
#     extra_c     -> valores extra de cada columna (demanda, resta, penalidad, vj)
# =============================================================================

def figura_tabla(foto):
    if "comparacion" in foto:
        return figura_comparacion(foto["comparacion"])

    m, n = len(foto["origenes"]), len(foto["destinos"])
    columnas = list(foto["destinos"]) + ["Oferta"]
    extra_f = [foto["a"]]
    renglones = list(foto["origenes"]) + ["Demanda"]
    extra_c = [foto["b"] + [foto["total"]]]
    for clave, titulo in (("resta_a", "Resta"), ("pen_f", "Penalidad"), ("u", "ui")):
        if clave in foto:
            columnas.append(titulo)
            extra_f.append(foto[clave])
    for clave, titulo in (("resta_b", "Resta"), ("pen_c", "Penalidad"), ("v", "vj")):
        if clave in foto:
            renglones.append(titulo)
            extra_c.append(foto[clave] + [""])

    AN, AL, AN0 = 0.85, 0.52, 1.15
    ancho, alto = AN0 + AN * len(columnas), AL * (len(renglones) + 1)
    fig = Figure(figsize=(ancho, alto), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, ancho)
    ax.set_ylim(alto, 0)                     # y crece hacia abajo, como una tabla
    ax.axis("off")

    ruta = foto.get("ruta") or []
    signo = {tuple(k): ("+" if s % 2 == 0 else "-") for s, k in enumerate(ruta)}
    tach_f, tach_c = foto.get("tach_f", []), foto.get("tach_c", [])
    linea = foto.get("linea")
    asignada = tuple(foto["asignada"]) if foto.get("asignada") else None

    def celda(x0, y0, w, fondo, txt="", color="black", negrita=False, tam=10):
        ax.add_patch(Rectangle((x0, y0), w, AL, facecolor=fondo, edgecolor=BORDE, lw=1))
        if txt != "":
            ax.text(x0 + w / 2, y0 + AL / 2, txt, ha="center", va="center", fontsize=tam,
                    color=color, fontweight="bold" if negrita else "normal")

    # Títulos de columna y de renglón.
    celda(0, 0, AN0, ENCABEZADO)
    for k, titulo in enumerate(columnas):
        celda(AN0 + k * AN, 0, AN, ENCABEZADO, titulo, "white", True, 9)
    for k, titulo in enumerate(renglones):
        celda(0, AL * (k + 1), AN0, ENCABEZADO, titulo, "white", True, 9)

    # Celdas de las rutas: costo cij (cuadrito) + unidades xij (centro).
    for i in range(m):
        for j in range(n):
            x0, y0 = AN0 + j * AN, AL * (i + 1)
            tachada = i in tach_f or j in tach_c
            fondo = "white"
            if tachada:
                fondo = TACHADO
            if (i, j) in signo:
                fondo = MAS if signo[(i, j)] == "+" else MENOS
            if (ruta and (i, j) == tuple(ruta[0])) or (i, j) == asignada:
                fondo = PIVOTE
            celda(x0, y0, AN, fondo)
            ax.add_patch(Rectangle((x0 + AN * 0.6, y0), AN * 0.4, AL * 0.42,
                                   facecolor="white", edgecolor=BORDE, lw=0.8))
            ax.text(x0 + AN * 0.8, y0 + AL * 0.21, foto["c"][i][j], ha="center",
                    va="center", fontsize=7.5, color="#333")
            if foto["x"][i][j] != "":
                ax.text(x0 + AN * 0.42, y0 + AL * 0.62, foto["x"][i][j], ha="center",
                        va="center", fontsize=11, fontweight="bold",
                        color="#777" if tachada and (i, j) != asignada else "black")
            elif "e" in foto and (i, j) in foto["e"]:
                e = foto["e"][(i, j)]
                negativo = e.startswith("-")
                ax.text(x0 + AN * 0.42, y0 + AL * 0.62, e if negativo or e == "0" else "+" + e,
                        ha="center", va="center", fontsize=9, style="italic",
                        color=NEGATIVO if negativo else "#4A6FA5",
                        fontweight="bold" if negativo else "normal")
            if (i, j) in signo:
                ax.text(x0 + AN * 0.1, y0 + AL * 0.25, signo[(i, j)], ha="center",
                        va="center", fontsize=12, fontweight="bold", color=ENCABEZADO)

    # Columnas extra de cada renglón (Oferta, Resta, Penalidad, ui).
    for k, valores in enumerate(extra_f):
        for i in range(m):
            elegida = linea and columnas[n + k] == "Penalidad" and tuple(linea) == ("f", i)
            celda(AN0 + (n + k) * AN, AL * (i + 1), AN, PIVOTE if elegida else TOTALES,
                  valores[i], negrita=(k == 0 or elegida))
        celda(AN0 + (n + k) * AN, AL * (m + 1), AN, TOTALES,
              foto["total"] if k == 0 else "", negrita=True)
    # Renglones extra de cada columna (Demanda, Resta, Penalidad, vj).
    for k, valores in enumerate(extra_c):
        for j in range(n):
            elegida = linea and renglones[m + k] == "Penalidad" and tuple(linea) == ("c", j)
            celda(AN0 + j * AN, AL * (m + 1 + k), AN, PIVOTE if elegida else TOTALES,
                  valores[j], negrita=(k == 0 or elegida))
        for kk in range(1, len(extra_f)):
            celda(AN0 + (n + kk) * AN, AL * (m + 1 + k), AN, TOTALES)
        if k > 0:
            celda(AN0 + n * AN, AL * (m + 1 + k), AN, TOTALES)
    return fig


def figura_comparacion(filas):
    """Cuadro comparativo de los 5 métodos (como la diapositiva 'Comparación')."""
    anchos = [max(len(r[k]) for r in filas) + 4 for k in range(3)]
    fig = Figure(figsize=(sum(anchos) * 0.085, 0.32 * len(filas)), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    tabla = ax.table(cellText=[list(r) for r in filas[1:]], colLabels=list(filas[0]),
                     cellLoc="center", colWidths=[a / sum(anchos) for a in anchos],
                     bbox=[0, 0, 1, 1])
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(10)
    for (r, c), cel in tabla.get_celld().items():
        cel.set_edgecolor(BORDE)
        if r == 0:
            cel.set_facecolor(ENCABEZADO)
            cel.get_text().set_color("white")
            cel.get_text().set_fontweight("bold")
        elif r >= 4:                            # Banquillo y DIMO: solución óptima
            cel.set_facecolor(MAS)
    return fig


if __name__ == "__main__":
    App().mainloop()
