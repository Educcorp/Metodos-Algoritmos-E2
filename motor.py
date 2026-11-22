# -*- coding: utf-8 -*-
"""
MODELO DE TRANSPORTE — motor de cálculo (sin librerías)

  Solución factible básica inicial (SFBI):
      1.1 Método de la Esquina Noroeste       (MEN)
      1.2 Método de Aproximación de Vogel     (MAV)
      1.3 Método del Costo Mínimo             (MCM)
  Optimización de la SFBI:
      1.4 Método de Pasos Secuenciales        (Banquillo)
      1.5 Método de Distribución Modificada   (DIMO, multiplicadores ui, vj)

Notación (la misma de las diapositivas):
    Oi    -> origen i (puerto, fábrica, planta...)      i = 1..m
    Dj    -> destino j (planta, ciudad, panadería...)   j = 1..n
    ai    -> oferta del origen i
    bj    -> demanda del destino j
    cij   -> costo de enviar una unidad de Oi a Dj
    xij   -> unidades enviadas de Oi a Dj
    Z     -> costo total = suma de cij · xij   (se MINIMIZA)
    ui,vj -> índices (multiplicadores) del DIMO:  cij = ui + vj  en celdas usadas
    eij   -> costo marginal de una celda no usada

=============================================================================
  ÍNDICE PARA EXPONER  (copiar la etiqueta y buscarla con Ctrl+F)
=============================================================================
    #FRACCIONES     Fracciones exactas (como en la libreta)
    #COSTO_M        ExprM: costos con M (rutas inaceptables)
    #LEER_NUMERO    Texto de una casilla a número
    #TABLA          Cómo se guarda la tabla de transporte
    #EQUILIBRAR     Maximización -> costos, y origen/destino ficticio
    #MOSTRAR        Datos de la tabla para la ventana y costo total
    #ASIGNAR        Asignación MIN(oferta, demanda) y tachar fila/columna
    #MEN-01         Esquina Noroeste
    #MCM-01         Costo Mínimo
    #MAV-01         Vogel (penalidades)
    #SFBI           Comprobar  rutas = m + n - 1  y costo de la SFBI
    #TRAYECTORIA    Trayectoria (+ - + -) de una celda no usada
    #BANQUILLO-01   Pasos Secuenciales (costos marginales por trayectoria)
    #DIMO-01        Distribución Modificada (ui, vj y eij)
    #OPTIMIZAR      Pasos 2, 3 y 4 (comunes a Banquillo y DIMO)
    #RESULTADO      Rutas, costo total y avisos
    #RESOLVER       Punto de entrada que llama la ventana
=============================================================================
"""


# =============================================================================
#   #FRACCIONES
#   Fracciones exactas (no float) para que los resultados salgan igual que
#   en la libreta: 2.5 + 0.5 = 3 y no 2.9999999...
#
#   Variables:
#     a, b   -> números enteros a los que se les saca el MCD
#     x      -> número a convertir (entero o Fraccion)
#     num    -> numerador de la fracción
#     den    -> denominador de la fracción (siempre positivo)
#     g      -> MCD de num y den (se usa para simplificar)
#     self   -> la fracción actual
#     o      -> la otra fracción con la que se opera o compara
#     d      -> copia del denominador para ver si sólo tiene factores 2 y 5
#     cifras -> cuántos decimales tiene el número (2.75 -> 2)
# =============================================================================

def mcd(a, b):
    """Máximo común divisor (algoritmo de Euclides)."""
    while b:
        a, b = b, a % b
    return abs(a)


def fr(x):
    """Convierte un entero a Fraccion (si ya es Fraccion la deja igual)."""
    return x if isinstance(x, Fraccion) else Fraccion(x)


class Fraccion:
    """Número racional num/den, siempre simplificado y con den > 0."""

    def __init__(self, num=0, den=1):
        if den == 0:
            raise ZeroDivisionError("División entre cero")
        if den < 0:                     # el signo se guarda en el numerador
            num, den = -num, -den
        g = mcd(num, den) or 1          # simplificar:  6/8 -> 3/4
        self.num, self.den = num // g, den // g

    # a/b + c/d = (ad + cb)/bd      a/b · c/d = ac/bd      a/b ÷ c/d = ad/bc
    def __add__(self, o):
        o = fr(o)
        return Fraccion(self.num * o.den + o.num * self.den, self.den * o.den)

    __radd__ = __add__                  # para que sum() funcione (0 + Fraccion)

    def __neg__(self):
        return Fraccion(-self.num, self.den)

    def __sub__(self, o):
        return self + (-fr(o))

    def __mul__(self, o):
        o = fr(o)
        return Fraccion(self.num * o.num, self.den * o.den)

    def __truediv__(self, o):
        o = fr(o)
        return Fraccion(self.num * o.den, self.den * o.num)

    # Para comparar a con b se revisa el signo de (a - b).
    def __eq__(self, o):
        o = fr(o)
        return self.num == o.num and self.den == o.den

    def __lt__(self, o):
        return (self - o).num < 0

    def __gt__(self, o):
        return (self - o).num > 0

    def __le__(self, o):
        return not self > o

    def __ge__(self, o):
        return not self < o

    def __str__(self):
        """Entero -> '12'.  Decimal exacto -> '2.5'.  Si no -> '1/3'."""
        if self.den == 1:
            return str(self.num)
        d, cifras = self.den, 0
        while d % 10 == 0:
            d //= 10
            cifras += 1
        while d % 2 == 0 or d % 5 == 0:     # 1/4 = 0.25, 1/8 = 0.125 ...
            d //= 2 if d % 2 == 0 else 5
            cifras += 1
        if d != 1:                          # 1/3 no tiene decimal exacto
            return "%d/%d" % (self.num, self.den)
        texto = str(abs(self.num) * 10 ** cifras // self.den).rjust(cifras + 1, "0")
        texto = (texto[:-cifras] + "." + texto[-cifras:]).rstrip("0").rstrip(".")
        return ("-" if self.num < 0 else "") + texto


# =============================================================================
#   #COSTO_M   class ExprM — costos con M (rutas inaceptables)
#
#   Las diapositivas usan un costo M "suficientemente grande" para las rutas
#   que no se pueden usar (por ejemplo, producir en abril para vender en
#   febrero). En vez de poner 99999 se guarda la M aparte:
#       M + 20  ->  m = 1, c = 20
#   Al comparar manda la parte de M; si es igual, decide la constante.
#   Los costos normales tienen m = 0 y se comportan como números comunes.
#
#   Variables:
#     m      -> coeficiente de M          (en 3M - 1/2, m = 3)
#     c      -> constante, parte sin M    (en 3M - 1/2, c = -1/2)
#     o      -> la otra expresión con la que se opera o compara
#     k      -> número que multiplica a la expresión (unidades xij)
#     v      -> parte que decide el signo (m si no es 0; si no, c)
#     texto  -> cómo se escribe la expresión en pantalla ("M+20")
# =============================================================================

def em(x):
    """Convierte un número a ExprM (si ya es ExprM la deja igual)."""
    return x if isinstance(x, ExprM) else ExprM(0, x)


class ExprM:
    """Costo de la forma  m·M + c."""

    def __init__(self, m=0, c=0):
        self.m, self.c = fr(m), fr(c)

    def __add__(self, o):
        o = em(o)
        return ExprM(self.m + o.m, self.c + o.c)

    __radd__ = __add__

    def __neg__(self):
        return ExprM(-self.m, -self.c)

    def __sub__(self, o):
        return self + (-em(o))

    def __mul__(self, k):
        """Producto por un número:  k·(mM + c) = kmM + kc."""
        return ExprM(self.m * k, self.c * k)

    def signo(self):
        # Si hay parte en M, esa decide el signo; si no, decide la constante.
        v = self.m if self.m != 0 else self.c
        return (v.num > 0) - (v.num < 0)

    def __eq__(self, o):
        return (self - em(o)).signo() == 0

    def __lt__(self, o):
        return (self - em(o)).signo() < 0

    def __gt__(self, o):
        return (self - em(o)).signo() > 0

    def __le__(self, o):
        return not self > o

    def __ge__(self, o):
        return not self < o

    def __str__(self):
        if self.m == 0:
            return str(self.c)
        if self.m == 1:
            texto = "M"
        elif self.m == -1:
            texto = "-M"
        else:
            texto = "%sM" % self.m
        if self.c == 0:
            return texto
        return texto + ("+%s" % self.c if self.c > 0 else "%s" % self.c)


# =============================================================================
#   #LEER_NUMERO   leer_numero(), leer_costo() — texto de una casilla a número
#
#   Variables:
#     texto    -> lo que el usuario escribió en la casilla
#     t        -> el texto sin espacios (se va recortando)
#     a, b     -> numerador y denominador cuando se escribe una fracción "a/b"
#     den      -> el denominador ya convertido a Fraccion
#     signo    -> 1 si es positivo, -1 si es negativo
#     entero   -> parte antes del punto   ("2.75" -> "2")
#     decimal  -> parte después del punto ("2.75" -> "75")
# =============================================================================

def leer_numero(texto):
    """Convierte '3', '-2.5' o '3/4' a Fraccion. Lanza ValueError si no es número."""
    t = texto.strip()
    if "/" in t:                                    # fracción a/b
        a, b = t.split("/", 1)
        den = leer_numero(b)
        if den == 0:
            raise ValueError("denominador cero")
        return leer_numero(a) / den
    signo = 1
    if t[:1] in ("+", "-"):
        signo = -1 if t[0] == "-" else 1
        t = t[1:]
    entero, _, decimal = t.partition(".")           # 2.75 -> 275/100
    if not (entero + decimal).isdigit():
        raise ValueError("número inválido")
    return Fraccion(signo * int(entero + decimal), 10 ** len(decimal))


def leer_costo(texto):
    """Como leer_numero(), pero además acepta 'M' (ruta inaceptable)."""
    t = texto.strip().upper()
    if t == "M":
        return ExprM(1, 0)
    return ExprM(0, leer_numero(t))


# =============================================================================
#   #TABLA   class TablaTransporte — cómo se guarda la tabla de transporte
#
#   Ejemplo RPG (3 puertos, 4 plantas), forma matricial:
#
#                 D1    D2    D3    D4  | Oferta (ai)
#         O1      12    13     4     6  |  500
#         O2       6     4    10    11  |  700
#         O3      10     9    12     4  |  800
#         Demanda (bj) 400  900  200  500  | 2000
#
#   Variables:
#     origenes   -> nombre de cada renglón: O1, O2, ... (y el ficticio)
#     destinos   -> nombre de cada columna: D1, D2, ... (y el ficticio)
#     c          -> c[i][j] = costo cij (ExprM, puede tener M)
#     a          -> a[i] = oferta del origen i
#     b          -> b[j] = demanda del destino j
#     x          -> x[i][j] = unidades xij de una celda USADA (básica).
#                   None = celda NO usada.  Una celda usada puede valer 0
#                   (degeneración), y aun así cuenta como ruta de la base.
#     m, n       -> número de orígenes y de destinos
#     sentido    -> 'min' (costos) o 'max' (beneficios)
#     beneficio  -> tabla original de beneficios (sólo si sentido = 'max')
#     ficticio   -> 'origen', 'destino' o None (qué se agregó al equilibrar)
# =============================================================================

class TablaTransporte:
    def __init__(self, c, a, b):
        self.c = c                                   # costos cij
        self.a = a                                   # ofertas ai
        self.b = b                                   # demandas bj
        self.m, self.n = len(a), len(b)
        self.origenes = ["O%d" % (i + 1) for i in range(self.m)]
        self.destinos = ["D%d" % (j + 1) for j in range(self.n)]
        self.x = [[None] * self.n for _ in range(self.m)]   # todavía sin asignar
        self.sentido = "min"
        self.beneficio = None
        self.ficticio = None

    def usadas(self):
        """Celdas usadas (básicas), en orden de renglón: (i, j)."""
        return [(i, j) for i in range(self.m) for j in range(self.n)
                if self.x[i][j] is not None]

    def no_usadas(self):
        """Celdas no usadas (no básicas), en orden de renglón: (i, j)."""
        return [(i, j) for i in range(self.m) for j in range(self.n)
                if self.x[i][j] is None]


def nombre_celda(i, j, letra="C"):
    """(0, 2) -> 'C13'  (índices desde 1, como en las diapositivas)."""
    if i < 9 and j < 9:
        return "%s%d%d" % (letra, i + 1, j + 1)
    return "%s%d,%d" % (letra, i + 1, j + 1)


# =============================================================================
#   #EQUILIBRAR   preparar() — maximización y problema equilibrado
#
#   1) Maximización (Situaciones especiales, 1): se convierte la tabla de
#      beneficios en tabla de costos:  cij = (beneficio mayor) - beneficio_ij.
#      Una celda con M en maximización es una ruta inaceptable (beneficio -M),
#      por eso queda con costo  mayor + M.
#   2) Teorema: el problema tiene solución si  suma(ai) = suma(bj).
#      Caso 1. Oferta < Demanda -> origen ficticio  O(m+1), a = diferencia, c = 0
#      Caso 2. Demanda < Oferta -> destino ficticio D(n+1), b = diferencia, c = 0
#
#   Variables:
#     prob        -> problema capturado: {'sentido', 'costos', 'oferta', 'demanda'}
#     salida      -> lista de textos y tablas que se muestran en pantalla
#     c           -> tabla de costos cij (copia)
#     a, b        -> ofertas ai y demandas bj (copias)
#     beneficio   -> tabla original de beneficios (en maximización)
#     finitos     -> beneficios que no son M (para buscar el mayor)
#     mayor       -> beneficio mayor de la tabla
#     oferta_total, demanda_total -> suma(ai) y suma(bj)
#     dif         -> diferencia que absorbe el ficticio
#     t           -> la tabla de transporte ya lista
# =============================================================================

def preparar(prob, salida):
    c = [list(fila) for fila in prob["costos"]]
    a, b = list(prob["oferta"]), list(prob["demanda"])
    beneficio = None

    if prob["sentido"] == "max":
        beneficio = [list(fila) for fila in c]
        finitos = [v for fila in c for v in fila if v.m == 0]
        mayor = max(finitos) if finitos else ExprM()
        # M en maximización = ruta inaceptable: beneficio -M -> costo mayor + M.
        c = [[mayor - v if v.m == 0 else mayor + v for v in fila] for fila in c]
        salida.append("=== MAXIMIZACIÓN: tabla de beneficios -> tabla de costos ===")
        salida.append("Beneficio mayor = %s.  En cada celda:  cij = %s - beneficio_ij"
                      % (mayor, mayor))

    oferta_total, demanda_total = sum(a, Fraccion(0)), sum(b, Fraccion(0))
    salida.append("Oferta total = %s = %s      Demanda total = %s = %s"
                  % (" + ".join(map(str, a)), oferta_total,
                     " + ".join(map(str, b)), demanda_total))

    ficticio = None
    if oferta_total < demanda_total:                         # Caso 1
        dif = demanda_total - oferta_total
        c.append([ExprM() for _ in b])
        a.append(dif)
        if beneficio:
            beneficio.append([ExprM() for _ in b])
        ficticio = "origen"
        salida.append("Oferta < Demanda: se agrega un ORIGEN FICTICIO O%d con oferta "
                      "%s - %s = %s y costo 0 (esos destinos no se satisfacen en la realidad)."
                      % (len(a), demanda_total, oferta_total, dif))
    elif demanda_total < oferta_total:                       # Caso 2
        dif = oferta_total - demanda_total
        for fila in c:
            fila.append(ExprM())
        if beneficio:
            for fila in beneficio:
                fila.append(ExprM())
        b.append(dif)
        ficticio = "destino"
        salida.append("Demanda < Oferta: se agrega un DESTINO FICTICIO D%d con demanda "
                      "%s - %s = %s y costo 0 (unidades que se quedan sin enviar)."
                      % (len(b), oferta_total, demanda_total, dif))
    else:
        salida.append("Oferta = Demanda: el problema ya está equilibrado.")

    t = TablaTransporte(c, a, b)
    t.sentido, t.beneficio, t.ficticio = prob["sentido"], beneficio, ficticio
    if ficticio == "origen":
        t.origenes[-1] += " (fict.)"
    elif ficticio == "destino":
        t.destinos[-1] += " (fict.)"
    return t


# =============================================================================
#   #MOSTRAR   foto_tabla(), costo_total() — datos para la pantalla
#
#   Variables:
#     t          -> la tabla de transporte
#     extra      -> marcas opcionales para la ventana:
#        resta_a, resta_b    -> oferta / demanda que falta por asignar
#        tach_f, tach_c      -> renglones / columnas tachados
#        asignada            -> celda (i, j) que se acaba de asignar
#        pen_f, pen_c        -> penalidades de Vogel de renglones / columnas
#        linea               -> ('f', i) o ('c', j): renglón/columna elegido en Vogel
#        e                   -> {(i, j): eij} costos marginales de celdas no usadas
#        ruta                -> trayectoria [(i, j), ...]  (signos + - + -)
#        u, v                -> índices ui y vj del DIMO
#     texto(v)   -> el valor como texto ('' si es None)
#     terminos   -> textos 'xij*cij' de cada ruta usada
#     z          -> costo total Z
# =============================================================================

def texto(v):
    return "" if v is None else str(v)


def foto_tabla(t, **extra):
    """Copia (en texto) de la tabla para que la ventana la dibuje."""
    foto = {"origenes": list(t.origenes), "destinos": list(t.destinos),
            "c": [[str(v) for v in fila] for fila in t.c],
            "x": [[texto(v) for v in fila] for fila in t.x],
            "a": [str(v) for v in t.a], "b": [str(v) for v in t.b],
            "total": str(sum(t.a, Fraccion(0)))}
    for clave in ("resta_a", "resta_b", "pen_f", "pen_c", "u", "v"):
        if clave in extra:
            foto[clave] = [texto(v) for v in extra[clave]]
    if "e" in extra:
        foto["e"] = {k: str(v) for k, v in extra["e"].items()}
    for clave in ("tach_f", "tach_c", "asignada", "linea", "ruta"):
        if clave in extra:
            foto[clave] = extra[clave]
    return foto


def costo_total(t, tabla=None):
    """Devuelve (Z, texto 'x11*c11 + x12*c12 + ... = Z') de las rutas usadas.

    tabla: matriz de costos a usar (por defecto t.c; en maximización t.beneficio).
    """
    tabla = tabla or t.c
    z, terminos = ExprM(), []
    for i, j in t.usadas():
        if t.x[i][j] != 0:
            z = z + tabla[i][j] * t.x[i][j]
            terminos.append("%s*%s" % (t.x[i][j], tabla[i][j]))
    return z, "%s = %s" % (" + ".join(terminos) or "0", z)


# =============================================================================
#   #ASIGNAR   asignar() — el paso que repiten MEN, MCM y MAV
#
#   Unidades = MIN(oferta que queda, demanda que queda). Luego se tacha el
#   renglón (oferta agotada) o la columna (demanda satisfecha).
#   Si se agotan las DOS a la vez se tacha SÓLO UNA (diapositiva: "Tachar fila 1
#   ó columna 1, sólo una de ellas"); la otra queda con 0 y más adelante recibe
#   una asignación de 0. Así siempre resultan  m + n - 1  rutas usadas y se
#   evita la degeneración.
#
#   Variables:
#     t            -> la tabla de transporte
#     i, j         -> celda donde se asigna
#     resta_a      -> oferta que le queda a cada origen
#     resta_b      -> demanda que le falta a cada destino
#     filas        -> renglones que siguen sin tachar
#     cols         -> columnas que siguen sin tachar
#     salida       -> lista de textos y tablas que se muestran en pantalla
#     unidades     -> MIN(resta_a[i], resta_b[j]), lo que se envía por la ruta
#     agota_f      -> True si la oferta del origen i llegó a 0
#     agota_c      -> True si la demanda del destino j llegó a 0
#     tachado      -> texto de lo que se tachó (para la pantalla)
# =============================================================================

def asignar(t, i, j, resta_a, resta_b, filas, cols, salida):
    unidades = min(resta_a[i], resta_b[j])
    salida.append("Unidades a asignar en %s = MIN(%s, %s) = %s"
                  % (nombre_celda(i, j), resta_a[i], resta_b[j], unidades))
    t.x[i][j] = unidades
    resta_a[i] = resta_a[i] - unidades
    resta_b[j] = resta_b[j] - unidades

    agota_f, agota_c = resta_a[i] == 0, resta_b[j] == 0
    if agota_f and agota_c:
        if len(filas) == 1 and len(cols) == 1:          # última asignación
            filas.remove(i)
            cols.remove(j)
            tachado = "se tachan el renglón %s y la columna %s (última asignación)" \
                      % (t.origenes[i], t.destinos[j])
        elif len(filas) > 1:
            filas.remove(i)
            tachado = ("se agotan oferta y demanda a la vez: se tacha SÓLO el renglón %s "
                       "(la columna %s queda con demanda 0)" % (t.origenes[i], t.destinos[j]))
        else:
            cols.remove(j)
            tachado = ("se agotan oferta y demanda a la vez: se tacha SÓLO la columna %s "
                       "(el renglón %s queda con oferta 0)" % (t.destinos[j], t.origenes[i]))
    elif agota_f:
        filas.remove(i)
        tachado = "se tacha el renglón %s (oferta agotada)" % t.origenes[i]
    else:
        cols.remove(j)
        tachado = "se tacha la columna %s (demanda satisfecha)" % t.destinos[j]
    salida.append("Ajuste: oferta %s = %s, demanda %s = %s;  %s."
                  % (t.origenes[i], resta_a[i], t.destinos[j], resta_b[j], tachado))


def foto_paso(t, i, j, resta_a, resta_b, filas, cols, **extra):
    """Foto de un paso de la SFBI (con tachados y lo que resta)."""
    return foto_tabla(t, resta_a=resta_a, resta_b=resta_b, asignada=(i, j),
                      tach_f=[k for k in range(t.m) if k not in filas],
                      tach_c=[k for k in range(t.n) if k not in cols], **extra)


# =============================================================================
#   #MEN-01   esquina_noroeste() — MÉTODO DE LA ESQUINA NOROESTE
#
#   1. Se inicia en la esquina superior izquierda (noroeste).
#   2. Unidades = MIN(disponibilidad, demanda).
#   3. Si se agotó la oferta se baja (renglón siguiente); si se satisfizo la
#      demanda se va a la derecha (columna siguiente).
#   Dicho de otra forma: siempre se asigna en la esquina noroeste de la parte
#   de la tabla que todavía no está tachada.
#
#   Variables:
#     t        -> la tabla de transporte
#     salida   -> lista de textos y tablas que se muestran en pantalla
#     resta_a  -> oferta que le queda a cada origen
#     resta_b  -> demanda que le falta a cada destino
#     filas    -> renglones sin tachar;   cols -> columnas sin tachar
#     paso     -> número de asignación
#     i, j     -> esquina noroeste actual = primer renglón y primera columna sin tachar
# =============================================================================

def esquina_noroeste(t, salida):
    salida.append("\n=== 1.1 MÉTODO DE LA ESQUINA NOROESTE (MEN) ===")
    salida.append("Tabla inicial:")
    salida.append(foto_tabla(t))
    resta_a, resta_b = list(t.a), list(t.b)
    filas, cols = list(range(t.m)), list(range(t.n))
    paso = 0
    while filas and cols:
        paso += 1
        i, j = filas[0], cols[0]                         # esquina noroeste
        salida.append("\n--- Asignación %d ---" % paso)
        salida.append("Esquina noroeste de lo que queda: %s (costo %s)"
                      % (nombre_celda(i, j), t.c[i][j]))
        asignar(t, i, j, resta_a, resta_b, filas, cols, salida)
        salida.append(foto_paso(t, i, j, resta_a, resta_b, filas, cols))


# =============================================================================
#   #MCM-01   costo_minimo() — MÉTODO DEL COSTO MÍNIMO
#
#   1. Asignar la mayor cantidad de unidades a la ruta con el MENOR costo
#      unitario de toda la tabla (sin contar lo tachado).
#   2. Tachar la fila o columna satisfecha.
#   3. Ajustar oferta y demanda.
#   4. Si queda más de una fila o columna sin tachar, repetir.
#   Empates: se elige la primera en el orden de la tabla (las diapositivas
#   dicen que se resuelven arbitrariamente).
#
#   Variables:
#     t        -> la tabla de transporte
#     salida   -> lista de textos y tablas que se muestran en pantalla
#     resta_a  -> oferta que le queda a cada origen
#     resta_b  -> demanda que le falta a cada destino
#     filas    -> renglones sin tachar;   cols -> columnas sin tachar
#     paso     -> número de asignación
#     libres   -> celdas que no están tachadas
#     i, j     -> celda de costo mínimo
#     empates  -> otras celdas con el mismo costo mínimo
# =============================================================================

def costo_minimo(t, salida):
    salida.append("\n=== 1.3 MÉTODO DEL COSTO MÍNIMO (MCM) ===")
    salida.append("Tabla inicial:")
    salida.append(foto_tabla(t))
    resta_a, resta_b = list(t.a), list(t.b)
    filas, cols = list(range(t.m)), list(range(t.n))
    paso = 0
    while filas and cols:
        paso += 1
        libres = [(i, j) for i in filas for j in cols]
        i, j = libres[0]
        for (p, q) in libres:                            # la de menor cij
            if t.c[p][q] < t.c[i][j]:
                i, j = p, q
        empates = [nombre_celda(p, q) for (p, q) in libres
                   if (p, q) != (i, j) and t.c[p][q] == t.c[i][j]]
        salida.append("\n--- Asignación %d ---" % paso)
        salida.append("Ruta de costo menor -> %s (costo %s)%s"
                      % (nombre_celda(i, j), t.c[i][j],
                         "   [empate con %s, se elige la primera]" % ", ".join(empates)
                         if empates else ""))
        asignar(t, i, j, resta_a, resta_b, filas, cols, salida)
        salida.append(foto_paso(t, i, j, resta_a, resta_b, filas, cols))


# =============================================================================
#   #MAV-01   vogel() — MÉTODO DE APROXIMACIÓN DE VOGEL
#
#   Paso 0. Penalidad de cada fila y columna = (segundo costo menor) - (costo
#           menor). Es el costo adicional por no usar la mejor ruta.
#   Paso 1. Identificar la fila o columna con la MÁXIMA penalidad.
#   Paso 2. Asignar MIN(oferta, demanda) a la ruta de menor costo de esa
#           fila o columna.
#   Paso 3. Reajustar oferta y demanda.
#   Paso 4. Eliminar la columna con demanda 0 (o la fila con oferta 0).
#   Paso 5. Calcular las nuevas penalidades y repetir.
#   Cuando sólo queda una fila o una columna ya no hay penalidad que
#   comparar: lo que resta se asigna por costo mínimo.
#   Empates: el primero encontrado (filas antes que columnas).
#
#   Variables:
#     t         -> la tabla de transporte
#     salida    -> lista de textos y tablas que se muestran en pantalla
#     resta_a   -> oferta que le queda a cada origen
#     resta_b   -> demanda que le falta a cada destino
#     filas     -> renglones sin tachar;   cols -> columnas sin tachar
#     paso      -> número de asignación
#     pen_f     -> penalidad de cada renglón (None si está tachado)
#     pen_c     -> penalidad de cada columna (None si está tachada)
#     linea     -> ('f', i) renglón o ('c', j) columna con la máxima penalidad
#     mayor     -> la máxima penalidad
#     celdas    -> celdas sin tachar de la línea elegida
#     i, j      -> celda de menor costo en la línea elegida
# =============================================================================

def penalidad(costos):
    """Diferencia entre los dos costos más pequeños de la lista."""
    ordenados = sorted(costos)
    return ordenados[1] - ordenados[0]


def vogel(t, salida):
    salida.append("\n=== 1.2 MÉTODO DE APROXIMACIÓN DE VOGEL (MAV) ===")
    salida.append("Tabla inicial:")
    salida.append(foto_tabla(t))
    resta_a, resta_b = list(t.a), list(t.b)
    filas, cols = list(range(t.m)), list(range(t.n))
    paso = 0
    while filas and cols:
        paso += 1
        salida.append("\n--- Asignación %d ---" % paso)
        pen_f, pen_c = [None] * t.m, [None] * t.n

        if len(filas) == 1 or len(cols) == 1:
            # Ya no hay dos costos que comparar: se asigna por costo mínimo.
            celdas = [(i, j) for i in filas for j in cols]
            linea = ("f", filas[0]) if len(filas) == 1 else ("c", cols[0])
            salida.append("Sólo queda %s: lo que resta se asigna por costo mínimo."
                          % ("el renglón " + t.origenes[filas[0]] if linea[0] == "f"
                             else "la columna " + t.destinos[cols[0]]))
        else:
            # Paso 0 / Paso 5: penalidades de las filas y columnas sin tachar.
            for i in filas:
                pen_f[i] = penalidad([t.c[i][j] for j in cols])
            for j in cols:
                pen_c[j] = penalidad([t.c[i][j] for i in filas])
            salida.append("Penalidades:  " +
                          "   ".join("%s = %s" % (t.origenes[i], pen_f[i]) for i in filas) +
                          "   |   " +
                          "   ".join("%s = %s" % (t.destinos[j], pen_c[j]) for j in cols))

            # Paso 1: la máxima penalidad (renglones primero, luego columnas).
            linea, mayor = None, None
            for i in filas:
                if mayor is None or pen_f[i] > mayor:
                    linea, mayor = ("f", i), pen_f[i]
            for j in cols:
                if pen_c[j] > mayor:
                    linea, mayor = ("c", j), pen_c[j]
            if linea[0] == "f":
                celdas = [(linea[1], j) for j in cols]
                salida.append("Máxima penalidad: renglón %s (penalidad = %s)"
                              % (t.origenes[linea[1]], mayor))
            else:
                celdas = [(i, linea[1]) for i in filas]
                salida.append("Máxima penalidad: columna %s (penalidad = %s)"
                              % (t.destinos[linea[1]], mayor))

        # Paso 2: ruta de menor costo dentro de la línea elegida.
        i, j = celdas[0]
        for (p, q) in celdas:
            if t.c[p][q] < t.c[i][j]:
                i, j = p, q
        salida.append("Ruta de menor costo en esa línea: %s (costo %s)"
                      % (nombre_celda(i, j), t.c[i][j]))
        # Pasos 3 y 4: reajustar y tachar.
        foto_antes = dict(pen_f=pen_f, pen_c=pen_c, linea=linea)
        asignar(t, i, j, resta_a, resta_b, filas, cols, salida)
        salida.append(foto_paso(t, i, j, resta_a, resta_b, filas, cols, **foto_antes))


# =============================================================================
#   #SFBI   comprobar_sfbi() — ¿es solución factible básica?  ¿m + n - 1?
#
#   Variables:
#     t        -> la tabla con la SFBI ya armada
#     nombre   -> nombre del método con que se obtuvo
#     salida   -> lista de textos y tablas que se muestran en pantalla
#     rutas    -> número de celdas usadas (incluye las de valor 0)
#     z        -> costo asociado (valor de la función objetivo)
#     detalle  -> texto 'x*c + x*c + ... = Z'
# =============================================================================

def comprobar_sfbi(t, nombre, salida):
    rutas = len(t.usadas())
    salida.append("\n=== SFBI (solución factible básica inicial) por %s ===" % nombre)
    salida.append(foto_tabla(t))
    salida.append("¿Es solución factible?  ¿rutas = m + n - 1 = %d + %d - 1 = %d?   "
                  "rutas usadas = %d   ->   %s"
                  % (t.m, t.n, t.m + t.n - 1, rutas,
                     "SÍ" if rutas == t.m + t.n - 1 else "NO"))
    z, detalle = costo_total(t)
    salida.append("Valor FO (costo asociado):  Z = %s" % detalle)
    return z


# =============================================================================
#   #TRAYECTORIA   trayectoria() — camino cerrado + - + - de una celda no usada
#
#   Reglas (diapositiva "Paso 1"):
#     - Un + en la celda no ocupada de interés.
#     - Un - en una celda usada del mismo renglón.
#     - Un + en una celda usada de la misma columna... alternando.
#     - Todo renglón o columna con un + debe tener también un -.
#   Cómo se encuentra:
#     a) Se toman las celdas usadas más la celda de interés.
#     b) Se borran una y otra vez las celdas que quedan SOLAS en su renglón
#        o en su columna (esas no pueden estar en un camino cerrado).
#     c) Lo que queda es la trayectoria; se recorre desde la celda de
#        interés moviéndose por renglón, luego por columna, y así.
#
#   Variables:
#     t        -> la tabla de transporte
#     i0, j0   -> la celda no usada de interés (lleva el +)
#     celdas   -> celdas candidatas a la trayectoria
#     cambio   -> True mientras se siga borrando alguna celda
#     en_fila  -> cuántas candidatas hay en el renglón de la celda
#     en_col   -> cuántas candidatas hay en la columna de la celda
#     ruta     -> trayectoria en orden: ruta[0] lleva +, ruta[1] -, ruta[2] +...
#     actual   -> celda donde va el recorrido
#     por_fila -> True si el siguiente movimiento es por el renglón
#     sig      -> siguiente celda de la trayectoria
# =============================================================================

def trayectoria(t, i0, j0):
    celdas = set(t.usadas()) | {(i0, j0)}
    cambio = True
    while cambio:
        cambio = False
        for (i, j) in list(celdas):
            en_fila = sum(1 for (p, q) in celdas if p == i)
            en_col = sum(1 for (p, q) in celdas if q == j)
            if en_fila < 2 or en_col < 2:
                celdas.discard((i, j))
                cambio = True

    ruta, actual, por_fila = [(i0, j0)], (i0, j0), True
    while True:
        if por_fila:
            sig = next(k for k in celdas if k[0] == actual[0] and k != actual)
        else:
            sig = next(k for k in celdas if k[1] == actual[1] and k != actual)
        if sig == (i0, j0):
            return ruta
        ruta.append(sig)
        actual, por_fila = sig, not por_fila


def ruta_txt(ruta):
    """[(0,2), (0,1), (2,1), (2,2)] -> '+C13 -C12 +C32 -C33'."""
    return " ".join(("+" if k % 2 == 0 else "-") + nombre_celda(i, j)
                    for k, (i, j) in enumerate(ruta))


# =============================================================================
#   #BANQUILLO-01   banquillo() — MÉTODO DE PASOS SECUENCIALES (banquillo)
#
#   Paso 1. Para cada ruta NO usada se arma su trayectoria y se calcula su
#           costo marginal = +c -c +c -c ...  (lo que cambia Z si se envía
#           una unidad por esa ruta).
#   Paso 2. Si todos los costos marginales son >= 0 la solución es óptima.
#           Si no, se elige el más negativo.            -> #OPTIMIZAR
#   Paso 3. Se mueven las unidades por la trayectoria.  -> #OPTIMIZAR
#   Paso 4. Regresar al paso 1.
#
#   Variables:
#     t          -> la tabla de transporte (ya con la SFBI)
#     salida     -> lista de textos y tablas que se muestran en pantalla
#     e          -> {(i, j): costo marginal} de cada ruta no usada
#     rutas      -> {(i, j): trayectoria} de cada ruta no usada
#     k          -> número de trayectoria (1, 2, 3...)
#     i, j       -> celda no usada
#     ruta       -> su trayectoria
#     costos     -> texto '+(4) -(13) +(9) -(12)'
#     cm         -> costo marginal de la ruta
# =============================================================================

def marginales_banquillo(t, salida):
    """Paso 1 del Banquillo: costos marginales por trayectorias."""
    salida.append("Paso 1: trayectorias y costos marginales de las rutas no usadas")
    e, rutas = {}, {}
    for k, (i, j) in enumerate(t.no_usadas(), 1):
        ruta = trayectoria(t, i, j)
        cm = ExprM()
        for s, (p, q) in enumerate(ruta):
            cm = cm + t.c[p][q] if s % 2 == 0 else cm - t.c[p][q]
        costos = " ".join("%s(%s)" % ("+" if s % 2 == 0 else "-", t.c[p][q])
                          for s, (p, q) in enumerate(ruta))
        salida.append("  %d: %s   ->   %s = %s" % (k, ruta_txt(ruta), costos, cm))
        e[(i, j)], rutas[(i, j)] = cm, ruta
    return e, rutas, {}


def banquillo(t, salida):
    salida.append("\n=== 1.4 MÉTODO DE PASOS SECUENCIALES (BANQUILLO) ===")
    return optimizar(t, salida, marginales_banquillo)


# =============================================================================
#   #DIMO-01   dimo() — MÉTODO DE DISTRIBUCIÓN MODIFICADA (multiplicadores)
#
#   Paso 0. Asociar a cada fila un índice ui y a cada columna un índice vj.
#   Paso 1.a) Hacer u1 = 0 y resolver  cij = ui + vj  en cada celda USADA
#             (hay m + n - 1 ecuaciones y m + n incógnitas, por eso se fija u1).
#   Paso 1.b) Para cada celda NO usada:  eij = cij - (ui + vj)
#             eij es el costo marginal de introducir la ruta i, j.
#   Los pasos 2 a 4 son los mismos que en el método secuencial. -> #OPTIMIZAR
#
#   Variables:
#     t          -> la tabla de transporte (ya con la SFBI)
#     salida     -> lista de textos y tablas que se muestran en pantalla
#     u          -> u[i] = índice ui de cada renglón   (None = aún sin calcular)
#     v          -> v[j] = índice vj de cada columna   (None = aún sin calcular)
#     usadas     -> celdas usadas: cada una da una ecuación  ui + vj = cij
#     avance     -> True si en la vuelta se calculó algún índice nuevo
#     e          -> {(i, j): eij} de cada ruta no usada
#     k          -> número de la celda no usada (1, 2, 3...)
# =============================================================================

def mas(a, b):
    """'(0 + 16)' o '(-7 - 4)': escribe la suma ui + vj como en la libreta."""
    return "(%s %s %s)" % (a, "-" if b < 0 else "+", -b if b < 0 else b)


def menos(a, b):
    """'12 - 0' o '12 - (-4)': escribe la resta cij - ui como en la libreta."""
    return "%s - %s" % (a, "(%s)" % b if b < 0 else b)


def marginales_dimo(t, salida):
    """Pasos 1.a y 1.b del DIMO: índices ui, vj y costos marginales eij."""
    u, v = [None] * t.m, [None] * t.n
    usadas = t.usadas()

    salida.append("Paso 1.a) Ecuaciones  ui + vj = cij  de las rutas en uso:")
    for (i, j) in usadas:
        salida.append("  Ruta %s   costo %s   ->   u%d + v%d = %s"
                      % (nombre_celda(i, j, ""), t.c[i][j], i + 1, j + 1, t.c[i][j]))

    u[0] = ExprM()
    salida.append("Hay %d ecuaciones y %d incógnitas: se hace u1 = 0 y se despeja el resto:"
                  % (len(usadas), t.m + t.n))
    avance = True
    while avance and any(k is None for k in u + v):     # mientras falte algún índice
        avance = False
        for (i, j) in usadas:
            if u[i] is not None and v[j] is None:
                v[j] = t.c[i][j] - u[i]
                salida.append("  v%d = c%d%d - u%d = %s = %s"
                              % (j + 1, i + 1, j + 1, i + 1, menos(t.c[i][j], u[i]), v[j]))
                avance = True
            elif v[j] is not None and u[i] is None:
                u[i] = t.c[i][j] - v[j]
                salida.append("  u%d = c%d%d - v%d = %s = %s"
                              % (i + 1, i + 1, j + 1, j + 1, menos(t.c[i][j], v[j]), u[i]))
                avance = True

    salida.append("Paso 1.b) Costos marginales de las rutas no usadas:  eij = cij - (ui + vj)")
    e = {}
    for k, (i, j) in enumerate(t.no_usadas(), 1):
        e[(i, j)] = t.c[i][j] - (u[i] + v[j])
        salida.append("  %d) e%d%d = c%d%d - (u%d + v%d) = %s - %s = %s"
                      % (k, i + 1, j + 1, i + 1, j + 1, i + 1, j + 1,
                         t.c[i][j], mas(u[i], v[j]), e[(i, j)]))
    return e, None, {"u": u, "v": v}


def dimo(t, salida):
    salida.append("\n=== 1.5 MÉTODO DE DISTRIBUCIÓN MODIFICADA (DIMO) ===")
    salida.append("Paso 0: se asocia un índice ui a cada renglón y vj a cada columna.")
    return optimizar(t, salida, marginales_dimo)


# =============================================================================
#   #OPTIMIZAR   optimizar() — Pasos 2, 3 y 4 (comunes a Banquillo y DIMO)
#
#   Paso 2. Prueba de optimalidad: si todos los costos marginales son >= 0,
#           la solución es óptima. Si no, entra la ruta más negativa.
#   Paso 3. Generación de la nueva tabla:
#           unidades = la menor cantidad de las celdas con signo - (decrecientes)
#           celdas +  -> aumentan esas unidades
#           celdas -  -> disminuyen esas unidades; la que llega a 0 sale
#   Paso 4. Volver al paso 1.
#
#   Variables:
#     t          -> la tabla de transporte
#     salida     -> lista de textos y tablas que se muestran en pantalla
#     paso1      -> función del Paso 1 (marginales_banquillo o marginales_dimo)
#     max_iter   -> máximo de iteraciones (evita ciclos infinitos)
#     it         -> número de iteración
#     e          -> {(i, j): costo marginal} de las rutas no usadas
#     rutas      -> trayectorias ya calculadas (Banquillo) o None (DIMO)
#     indices    -> {'u': [...], 'v': [...]} en el DIMO (para la tabla)
#     entra      -> ruta no usada con el costo marginal más negativo
#     ruta       -> trayectoria de la ruta que entra
#     menos      -> celdas con signo - de la trayectoria
#     unidades   -> unidades que se pueden mover por la trayectoria
#     sale       -> celda con signo - que llega a 0 (deja de usarse)
#     z          -> costo total después de la iteración
#     alternas   -> rutas no usadas con costo marginal 0 (otro óptimo)
# =============================================================================

def optimizar(t, salida, paso1, max_iter=100):
    it = 0
    while True:
        salida.append("\n--- Iteración %d ---" % (it + 1))
        e, rutas, indices = paso1(t, salida)

        # Paso 2: prueba de optimalidad.
        entra = None
        for celda in t.no_usadas():
            if e[celda] < 0 and (entra is None or e[celda] < e[entra]):
                entra = celda
        if entra is None:
            salida.append(foto_tabla(t, e=e, **indices))
            salida.append("Paso 2: prueba de optimalidad -> no hay costos marginales "
                          "negativos, por lo tanto la solución ES ÓPTIMA.")
            alternas = [nombre_celda(i, j) for (i, j) in t.no_usadas() if e[(i, j)] == 0]
            if alternas:
                salida.append("Hay costo marginal 0 en %s: existen otras soluciones óptimas "
                              "con el mismo costo (soluciones alternas)." % ", ".join(alternas))
            return "optimo"
        if it == max_iter:
            return "limite"
        it += 1

        ruta = rutas[entra] if rutas else trayectoria(t, *entra)
        salida.append(foto_tabla(t, e=e, ruta=ruta, **indices))
        salida.append("Paso 2: hay costos negativos, por lo tanto NO es óptima. "
                      "Se elige %s (costo marginal más negativo, %s)."
                      % (nombre_celda(*entra), e[entra]))
        salida.append("Trayectoria de reasignación: %s" % ruta_txt(ruta))

        # Paso 3: ¿cuántas unidades se pueden asignar a la ruta elegida?
        menos = ruta[1::2]
        unidades = min(t.x[i][j] for (i, j) in menos)
        salida.append("Paso 3: unidades disponibles en las celdas decrecientes (-):  "
                      + ",  ".join("%s = %s" % (nombre_celda(i, j), t.x[i][j])
                                   for (i, j) in menos)
                      + "   ->   se mueven MIN = %s" % unidades)
        for k, (i, j) in enumerate(ruta):
            accion = "Aumentar" if k % 2 == 0 else "Disminuir"
            salida.append("    %s %s unidades en %s" % (accion, unidades, nombre_celda(i, j)))
        sale = next(k for k in menos if t.x[k[0]][k[1]] == unidades)
        for k, (i, j) in enumerate(ruta):
            if k == 0:
                t.x[i][j] = unidades
            elif k % 2 == 0:
                t.x[i][j] = t.x[i][j] + unidades
            else:
                t.x[i][j] = t.x[i][j] - unidades
        t.x[sale[0]][sale[1]] = None
        salida.append("Entra la ruta %s y sale la ruta %s."
                      % (nombre_celda(*entra), nombre_celda(*sale)))
        z, detalle = costo_total(t)
        salida.append("Nueva tabla:")
        salida.append(foto_tabla(t, asignada=entra))
        salida.append("Costo:  Z = %s" % detalle)
        salida.append("Paso 4: volver al Paso 1.")


# =============================================================================
#   #RESULTADO   mostrar_resultado() — rutas, costo total y avisos
#
#   Variables:
#     t         -> la tabla final
#     salida    -> lista de textos y tablas que se muestran en pantalla
#     titulo    -> qué se obtuvo ('SFBI' o 'solución óptima')
#     i, j      -> cada ruta usada
#     nota      -> aviso si la ruta va a un ficticio o tiene costo M
#     z         -> costo total;  detalle -> 'x*c + ... = Z'
#     g         -> beneficio total (sólo en maximización)
# =============================================================================

def mostrar_resultado(t, salida, titulo):
    salida.append("\n" + "=" * 60 + "\nRESULTADO (%s)" % titulo)
    for (i, j) in t.usadas():
        if t.x[i][j] == 0:
            continue
        nota = ""
        if t.ficticio == "origen" and i == t.m - 1:
            nota = "   <- origen ficticio: demanda de %s NO satisfecha" % t.destinos[j]
        elif t.ficticio == "destino" and j == t.n - 1:
            nota = "   <- destino ficticio: se quedan en %s sin enviar" % t.origenes[i]
        if t.c[i][j].m != 0:
            nota += "   <- ¡ruta inaceptable (costo M)!"
        salida.append("x%d%d = %s   (%s -> %s)%s" % (i + 1, j + 1, t.x[i][j],
                                                    t.origenes[i], t.destinos[j], nota))
    z, detalle = costo_total(t)
    if t.sentido == "max":
        g, detalle_g = costo_total(t, t.beneficio)
        salida.append("Costo (tabla convertida):  Z = %s" % detalle)
        salida.append("BENEFICIO TOTAL MÁXIMO = %s" % detalle_g)
    else:
        salida.append("COSTO TOTAL = %s" % detalle)
    if z.m != 0:
        salida.append("Aviso: la solución usa una ruta con costo M; sin esa ruta inaceptable "
                      "el problema no tiene solución factible.")
    return z


# =============================================================================
#   #RESOLVER   resolver(), comparar() — punto de entrada que llama la ventana
#
#   Variables:
#     SFBI     -> métodos de solución inicial:  clave -> (nombre, función)
#     OPTIMOS  -> métodos de optimización:      clave -> (nombre, función)
#     metodo   -> 'men', 'mcm', 'mav', 'banquillo' o 'dimo'
#     prob     -> problema capturado en la ventana:
#       prob['sentido']  -> 'min' o 'max'
#       prob['costos']   -> matriz cij (ExprM)
#       prob['oferta']   -> lista ai
#       prob['demanda']  -> lista bj
#       prob['sfbi']     -> 'men', 'mcm' o 'mav' (solución inicial del Banquillo/DIMO)
#     salida   -> lista de pasos (textos y tablas) que se devuelve
#     t        -> la tabla de transporte
#     estado   -> cómo terminó la optimización: 'optimo' o 'limite'
#     filas    -> renglones del cuadro comparativo: (método, rutas, costo)
# =============================================================================

SFBI = {"men": ("Esquina Noroeste (MEN)", esquina_noroeste),     # -> #MEN-01
        "mcm": ("Costo Mínimo (MCM)", costo_minimo),             # -> #MCM-01
        "mav": ("Vogel (MAV)", vogel)}                           # -> #MAV-01

OPTIMOS = {"banquillo": ("Banquillo (Pasos Secuenciales)", banquillo),   # -> #BANQUILLO-01
           "dimo": ("DIMO (Distribución Modificada)", dimo)}             # -> #DIMO-01


def resolver_en(metodo, prob, salida):
    """Resuelve con un método y devuelve la tabla final."""
    t = preparar(prob, salida)                                   # -> #EQUILIBRAR
    if metodo in SFBI:
        nombre, funcion = SFBI[metodo]
        funcion(t, salida)
        comprobar_sfbi(t, nombre, salida)                        # -> #SFBI
        mostrar_resultado(t, salida, "SFBI por " + nombre)       # -> #RESULTADO
        return t
    nombre, funcion = SFBI[prob["sfbi"]]
    salida.append("Primero se obtiene la SFBI con %s:" % nombre)
    funcion(t, salida)
    comprobar_sfbi(t, nombre, salida)
    estado = OPTIMOS[metodo][1](t, salida)                       # -> #OPTIMIZAR
    if estado == "limite":
        salida.append("No se llegó al óptimo dentro del máximo de iteraciones.")
    mostrar_resultado(t, salida, "solución óptima por " + OPTIMOS[metodo][0])
    return t


def resolver(metodo, prob):
    """Devuelve la lista de pasos: textos (str) y tablas (dict de foto_tabla)."""
    salida = []
    resolver_en(metodo, prob, salida)
    return salida


def comparar(prob):
    """Resuelve con los 5 métodos y arma el cuadro comparativo (como la diapositiva 60)."""
    salida, filas = [], []
    for metodo in ("men", "mav", "mcm", "banquillo", "dimo"):
        t = resolver_en(metodo, prob, [])
        nombre = (SFBI.get(metodo) or OPTIMOS[metodo])[0]
        if metodo in OPTIMOS:
            nombre += "  desde " + SFBI[prob["sfbi"]][0]
        tabla = t.beneficio if t.sentido == "max" else t.c
        filas.append((nombre, len([k for k in t.usadas() if t.x[k[0]][k[1]] != 0]),
                      costo_total(t, tabla)[0]))
    salida.append("=== COMPARACIÓN DE LOS 5 MÉTODOS ===")
    salida.append({"comparacion": [("Método", "Rutas", "Beneficio" if prob["sentido"] == "max"
                                     else "Costo")] +
                   [(n, str(r), str(z)) for n, r, z in filas]})
    salida.append("Los tres primeros entregan soluciones básicas factibles, pero ninguno "
                  "asegura que la solución sea óptima. Banquillo y DIMO parten de una SFBI "
                  "y llegan a la solución óptima.")
    return salida
