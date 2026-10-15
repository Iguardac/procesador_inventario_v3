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
RUTA_SALIDA = "ordenes_compra_urgente_v3.csv"

CATEGORIAS_VALIDAS = {"Alimentos", "Bebestibles", "Limpieza",
                      "Higiene Personal", "Mascotas", "Lácteos"}
COLUMNAS_ENTERAS = ["stock_actual", "stock_minimo", "stock_maximo",
                    "demanda_semanal", "lead_time_dias"]
COLUMNAS_TEXTO = ["id_producto", "producto", "categoria", "proveedor"]
COLUMNAS_SALIDA = ["id_producto", "producto", "cantidad_a_reponer",
                   "costo_total_reposicion", "proveedor", "dias_estimados_reposicion"]

LEAD_TIME_MIN = 1          # días
LEAD_TIME_MAX = 30         # días
LEAD_TIME_URGENTE = 5      # días: sobre este valor, un bajo stock es de extrema urgencia
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
# SECCIÓN 3: CÁLCULOS
# =========================================================
def calcular_reposicion(registro, lead_time_urgente=LEAD_TIME_URGENTE):
    """
    Calcula el estado de stock, la cantidad a reponer y el costo de reposición.

    Args:
        registro (dict): registro válido.
        lead_time_urgente (int): días sobre los cuales un bajo stock es extrema urgencia.

    Returns:
        dict: copia del registro con bajo_stock, sobrestock, cantidad_a_reponer,
              costo_total_reposicion, extrema_urgencia y dias_estimados_reposicion.
    """
    resultado = dict(registro)
    bajo_stock = registro["stock_actual"] < registro["stock_minimo"]

    resultado["bajo_stock"] = bajo_stock
    resultado["sobrestock"] = registro["stock_actual"] > registro["stock_maximo"]
    resultado["cantidad_a_reponer"] = registro["stock_maximo"] - registro["stock_actual"] if bajo_stock else 0
    resultado["costo_total_reposicion"] = round(resultado["cantidad_a_reponer"] * registro["costo_unitario"], 0)
    resultado["extrema_urgencia"] = bajo_stock and registro["lead_time_dias"] > lead_time_urgente
    resultado["dias_estimados_reposicion"] = registro["lead_time_dias"] if bajo_stock else 0
    return resultado


def generar_resumen(procesados, descartados, total_leidos):
    """
    Reúne los totales del proceso en un diccionario.

    Args:
        procesados (list): registros válidos con sus cálculos.
        descartados (list): tuplas (id_producto, errores) de los registros descartados.
        total_leidos (int): cantidad de filas leídas del archivo.

    Returns:
        dict: totales, categoría más crítica, alertas por proveedor y motivos de descarte.
    """
    bajo_stock = [r for r in procesados if r["bajo_stock"]]
    urgentes = [r for r in bajo_stock if r["extrema_urgencia"]]

    por_categoria = {}
    por_proveedor = {}
    for r in bajo_stock:
        por_categoria[r["categoria"]] = por_categoria.get(r["categoria"], 0) + 1
        por_proveedor[r["proveedor"]] = por_proveedor.get(r["proveedor"], 0) + 1

    motivos = {}
    for _, errores in descartados:
        for error in errores:
            motivos[error["regla"]] = motivos.get(error["regla"], 0) + 1

    categoria_critica = max(por_categoria, key=por_categoria.get) if por_categoria else None
    motivo_principal = max(motivos, key=motivos.get) if motivos else None

    return {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_leidos": total_leidos,
        "validos": len(procesados),
        "descartados": len(descartados),
        "motivos_descarte": motivos,
        "motivo_principal": motivo_principal,
        "bajo_stock": len(bajo_stock),
        "sobrestock": sum(1 for r in procesados if r["sobrestock"]),
        "unidades_reponer": sum(r["cantidad_a_reponer"] for r in bajo_stock),
        "costo_total": sum(r["costo_total_reposicion"] for r in bajo_stock),
        "categoria_critica": categoria_critica,
        "cantidad_categoria_critica": por_categoria.get(categoria_critica, 0),
        "alertas_por_proveedor": por_proveedor,
        "urgentes": urgentes,
    }


# =========================================================
# SECCIÓN 4: ENTRADA Y SALIDA DE ARCHIVOS
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


def escribir_csv_salida(ruta, registros, columnas=COLUMNAS_SALIDA):
    """
    Escribe el archivo CSV con las órdenes de compra urgentes.

    Args:
        ruta (str): ruta del archivo de salida.
        registros (list): registros bajo stock a escribir.
        columnas (list): columnas del archivo. Por defecto, COLUMNAS_SALIDA.

    Returns:
        int: cantidad de filas escritas.
    """
    with open(ruta, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(registros)
    return len(registros)

# =========================================================
# SECCIÓN 5: REPORTE POR CONSOLA
# =========================================================
def generar_reporte_consola(resumen):
    """
    Imprime el resumen ejecutivo y la recomendación final al Jefe del CD.

    Args:
        resumen (dict): totales generados por generar_resumen().

    Returns:
        str: el texto del reporte que se mostró por consola.
    """
    lineas = [
        "===== RESUMEN EJECUTIVO - DIMAULE SpA (v3.0) =====",
        f"Fecha de proceso           : {resumen['fecha']}",
        f"Registros leídos           : {resumen['total_leidos']}",
        f"Registros válidos          : {resumen['validos']}",
        f"Registros descartados      : {resumen['descartados']}",
        f"Motivo principal de descarte: {resumen['motivo_principal'] or 'ninguno'} "
        f"{resumen['motivos_descarte']}",
        "",
        f"Productos bajo stock       : {resumen['bajo_stock']}",
        f"Productos con sobrestock   : {resumen['sobrestock']}",
        f"Unidades a reponer         : {resumen['unidades_reponer']:,}".replace(",", "."),
        f"Costo total de reposición  : ${resumen['costo_total']:,.0f}".replace(",", "."),
        f"Categoría más crítica      : {resumen['categoria_critica']} "
        f"({resumen['cantidad_categoria_critica']} productos)",
        "",
        "--- Alertas por proveedor ---",
    ]
    for proveedor, cantidad in sorted(resumen["alertas_por_proveedor"].items()):
        lineas.append(f"{proveedor}: {cantidad} productos bajo stock")

    lineas.append("")
    lineas.append(f"--- Casos de extrema urgencia (lead time > {LEAD_TIME_URGENTE} días): "
                  f"{len(resumen['urgentes'])} ---")
    for caso in resumen["urgentes"]:
        lineas.append(f"{caso['id_producto']} - {caso['producto']} ({caso['proveedor']}, "
                      f"{caso['lead_time_dias']} días)")

    proveedores_urgentes = sorted({c["proveedor"] for c in resumen["urgentes"]})
    lineas += [
        "",
        "--- Recomendación al Jefe del CD ---",
        f"Emitir de inmediato las {len(resumen['urgentes'])} órdenes de extrema urgencia "
        f"({', '.join(proveedores_urgentes) or 'sin proveedor'}), priorizar la reposición de "
        f"{resumen['categoria_critica']} y revisar con Supply Chain los "
        f"{resumen['descartados']} registros descartados, en especial por "
        f"{resumen['motivo_principal'] or 'ningún motivo'}, antes de la próxima compra.",
    ]

    texto = "\n".join(lineas)
    print(texto)
    return texto


# =========================================================
# SECCIÓN 6: PROGRAMA PRINCIPAL
# =========================================================
def main(ruta_entrada=RUTA_ENTRADA, ruta_salida=RUTA_SALIDA):
    """
    Orquesta el flujo completo: leer, validar, calcular, escribir y reportar.

    Args:
        ruta_entrada (str): archivo de inventario a procesar.
        ruta_salida (str): archivo CSV de órdenes urgentes.

    Returns:
        int: cantidad de órdenes escritas en el archivo de salida.
    """
    crudos = leer_csv(ruta_entrada)
    procesados, descartados = [], []

    for fila in crudos:
        id_producto = (fila.get("id_producto") or "").strip()

        ok_t, registro, errores_t = validar_tipos(fila)
        if not ok_t:
            descartados.append((id_producto, errores_t))
            continue

        ok_n, errores_n = validar_reglas_negocio(registro)
        if not ok_n:
            descartados.append((id_producto, errores_n))
            continue

        procesados.append(calcular_reposicion(registro))

    resumen = generar_resumen(procesados, descartados, len(crudos))
    ordenes = [r for r in procesados if r["bajo_stock"]]
    escritas = escribir_csv_salida(ruta_salida, ordenes)
    generar_reporte_consola(resumen)
    print(f"\nArchivo generado: {ruta_salida} ({escritas} órdenes)")
    return escritas


if __name__ == "__main__":
    main()
