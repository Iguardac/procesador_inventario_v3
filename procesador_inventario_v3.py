# ---------------------------------------------------------
# PROYECTO: procesador_inventario_v3
# Curso: Programación en Python - Unidad 3
# Caso: DIMAULE SpA - Centro de Distribución Curicó
# Autor: Alberto Guarda Caro
# ---------------------------------------------------------

import csv
import re
from datetime import datetime


# =========================================================
# SECCIÓN 1: CONFIGURACIÓN GLOBAL (scope global)
# Constantes que usan varias funciones. Se dejan en scope
# global porque son reglas fijas del negocio y no cambian
# durante la ejecución: si cambian, se modifican solo aquí.
# =========================================================
RUTA_ENTRADA = "data/inventario_cd.csv"

CATEGORIAS_VALIDAS = {"Alimentos", "Bebestibles", "Limpieza",
                      "Higiene Personal", "Mascotas", "Lácteos"}
COLUMNAS_ENTERAS = ["stock_actual", "stock_minimo", "stock_maximo",
                    "demanda_semanal", "lead_time_dias"]
COLUMNAS_TEXTO = ["id_producto", "producto", "categoria", "proveedor"]

LEAD_TIME_MIN = 1          # días
LEAD_TIME_MAX = 30         # días
PATRON_ID = re.compile(r"^[A-Z]\d{3}$")   # letra mayúscula + 3 dígitos (ej. P001)


# =========================================================
# SECCIÓN 2: VALIDACIONES
# =========================================================
def validar_tipos(registro):
    """
    Convierte las columnas numéricas de un registro crudo y limpia los textos.
    Captura ValueError y TypeError en cada conversión por separado.

    Args:
        registro (dict): fila del CSV tal como fue leída (todo es texto).

    Returns:
        tuple: (es_valido, registro_convertido, errores)
            es_valido (bool): True si todas las conversiones funcionaron.
            registro_convertido (dict): datos con int, float y textos sin espacios.
            errores (list): un diccionario por cada error (regla, columna, valor, detalle).
    """
    convertido = {}
    errores = []

    for columna in COLUMNAS_TEXTO:
        valor = registro.get(columna)
        convertido[columna] = valor.strip() if isinstance(valor, str) else ""

    for columna in COLUMNAS_ENTERAS:
        valor = registro.get(columna)
        try:
            convertido[columna] = int(valor.strip() if isinstance(valor, str) else valor)
        except (ValueError, TypeError):
            errores.append({"regla": "TIPO", "columna": columna, "valor": valor,
                            "detalle": "se esperaba un número entero"})

    valor = registro.get("costo_unitario")
    try:
        convertido["costo_unitario"] = float(valor.strip() if isinstance(valor, str) else valor)
    except (ValueError, TypeError):
        errores.append({"regla": "TIPO", "columna": "costo_unitario", "valor": valor,
                        "detalle": "se esperaba un número decimal"})

    return len(errores) == 0, convertido, errores


def validar_reglas_negocio(registro, categorias=CATEGORIAS_VALIDAS):
    """
    Verifica las reglas de negocio RN-01 a RN-07 sobre un registro ya convertido.

    Args:
        registro (dict): registro con los tipos ya convertidos por validar_tipos().
        categorias (set): categorías permitidas. Por defecto, CATEGORIAS_VALIDAS.

    Returns:
        tuple: (ok, errores)
            ok (bool): True si el registro cumple todas las reglas.
            errores (list): un diccionario por regla incumplida.
    """
    errores = []

    # RN-01: columnas enteras mayores o iguales a cero
    for columna in COLUMNAS_ENTERAS:
        if registro[columna] < 0:
            errores.append({"regla": "RN-01", "columna": columna, "valor": registro[columna],
                            "detalle": "debe ser un entero mayor o igual a cero"})

    # RN-02: costo unitario estrictamente mayor que cero
    if registro["costo_unitario"] <= 0:
        errores.append({"regla": "RN-02", "columna": "costo_unitario",
                        "valor": registro["costo_unitario"],
                        "detalle": "debe ser mayor que cero (revisión manual)"})

    # RN-03: stock mínimo menor o igual que stock máximo
    if registro["stock_minimo"] > registro["stock_maximo"]:
        errores.append({"regla": "RN-03", "columna": "stock_minimo",
                        "valor": f"{registro['stock_minimo']} > {registro['stock_maximo']}",
                        "detalle": "stock_minimo no puede ser mayor que stock_maximo"})

    # RN-04: lead time entre 1 y 30 días
    if not (LEAD_TIME_MIN <= registro["lead_time_dias"] <= LEAD_TIME_MAX):
        errores.append({"regla": "RN-04", "columna": "lead_time_dias",
                        "valor": registro["lead_time_dias"],
                        "detalle": f"debe estar entre {LEAD_TIME_MIN} y {LEAD_TIME_MAX} días"})

    # RN-05: categoría dentro del listado permitido
    if registro["categoria"] not in categorias:
        errores.append({"regla": "RN-05", "columna": "categoria", "valor": registro["categoria"],
                        "detalle": "categoría fuera del listado permitido"})

    # RN-06: proveedor no vacío
    if registro["proveedor"] == "":
        errores.append({"regla": "RN-06", "columna": "proveedor", "valor": "(vacío)",
                        "detalle": "el proveedor no puede estar vacío"})

    # RN-07: id_producto con formato letra mayúscula + 3 dígitos
    if not PATRON_ID.match(registro["id_producto"]):
        errores.append({"regla": "RN-07", "columna": "id_producto", "valor": registro["id_producto"],
                        "detalle": "formato esperado: letra mayúscula + 3 dígitos (ej. P001)"})

    return len(errores) == 0, errores


def formatear_error(id_producto, error):
    """
    Arma un mensaje claro para el operador a partir de un error de validación.

    Args:
        id_producto (str): código del producto afectado.
        error (dict): error con las claves regla, columna, valor y detalle.

    Returns:
        str: mensaje con producto, columna, valor recibido y regla incumplida.
    """
    return (f"Producto {id_producto or 'SIN_ID'} | columna: {error['columna']} | "
            f"valor recibido: {error['valor']!r} | {error['regla']}: {error['detalle']}")


# =========================================================
# SECCIÓN 3: ENTRADA Y SALIDA DE ARCHIVOS
# =========================================================
def leer_csv(ruta=RUTA_ENTRADA, encoding="utf-8"):
    """
    Lee el archivo CSV de inventario y retorna sus filas como diccionarios crudos.

    Args:
        ruta (str): ruta del archivo. Por defecto, data/inventario_cd.csv.
        encoding (str): codificación del archivo. Por defecto, utf-8.

    Returns:
        list: una lista con un diccionario por fila.
    """
    with open(ruta, "r", encoding=encoding) as archivo:
        return list(csv.DictReader(archivo))

# =========================================================
# SECCIÓN 4: PROGRAMA PRINCIPAL
# =========================================================
def main(ruta_entrada=RUTA_ENTRADA):
    """
    Lee el archivo, valida cada registro y muestra el resumen de la validación.

    Args:
        ruta_entrada (str): archivo de inventario a procesar.

    Returns:
        tuple: (validos, descartados) con los registros de cada grupo.
    """
    crudos = leer_csv(ruta_entrada)
    validos, descartados = [], []

    for fila in crudos:
        id_producto = (fila.get("id_producto") or "").strip()

        ok_t, registro, errores_t = validar_tipos(fila)
        if not ok_t:
            descartados.append((id_producto, errores_t))
            for error in errores_t:
                print(formatear_error(id_producto, error))
            continue

        ok_n, errores_n = validar_reglas_negocio(registro)
        if not ok_n:
            descartados.append((id_producto, errores_n))
            for error in errores_n:
                print(formatear_error(id_producto, error))
            continue

        validos.append(registro)

    motivos = {}
    for _, errores in descartados:
        for error in errores:
            motivos[error["regla"]] = motivos.get(error["regla"], 0) + 1
    motivo_principal = max(motivos, key=motivos.get) if motivos else "ninguno"

    print("")
    print("===== RESUMEN DE VALIDACIÓN =====")
    print(f"Registros leídos     : {len(crudos)}")
    print(f"Registros válidos    : {len(validos)}")
    print(f"Registros descartados: {len(descartados)}")
    print(f"Motivo principal     : {motivo_principal} {motivos}")
    return validos, descartados


if __name__ == "__main__":
    main()
