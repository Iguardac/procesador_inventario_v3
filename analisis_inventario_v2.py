# ---------------------------------------------------------
# PROGRAMA: analisis_inventario.py
# OBJETIVO: Procesar inventario desde archivo CSV y generar
#           alertas de reposición para DIMAULE SpA.
# ---------------------------------------------------------

# 1. Importar librería estándar
import csv

# 2. Definir nombres de archivos
ARCHIVO_ENTRADA = "inventario_cd.csv"
ARCHIVO_SALIDA = "ordenes_compra_urgente.csv"

# 3. Inicializar contadores y acumuladores
total_productos = 0
total_bajo_stock = 0
total_sobrestock = 0
total_unidades_reponer = 0
costo_total_reposicion = 0.0

# 4. Inicializar estructuras de datos
registros_inventario = []
ordenes_compra = []
alertas_por_proveedor = {}
bajo_stock_por_categoria = {}
casos_extrema_urgencia = []

# 5. Leer archivo de entrada
with open(ARCHIVO_ENTRADA, mode="r", encoding="utf-8") as archivo:
    lector = csv.DictReader(archivo)

    for fila in lector:
        # 6. Convertir tipos de datos según corresponda
        id_producto = fila["id_producto"]
        producto = fila["producto"]
        categoria = fila["categoria"]
        proveedor = fila["proveedor"]

        stock_actual = int(fila["stock_actual"])
        stock_minimo = int(fila["stock_minimo"])
        stock_maximo = int(fila["stock_maximo"])
        demanda_semanal = int(fila["demanda_semanal"])
        costo_unitario = float(fila["costo_unitario"])
        lead_time_dias = int(fila["lead_time_dias"])

        # 7. Guardar registro leído en una lista de diccionarios
        registros_inventario.append({
            "id_producto": id_producto,
            "producto": producto,
            "categoria": categoria,
            "stock_actual": stock_actual,
            "stock_minimo": stock_minimo,
            "stock_maximo": stock_maximo,
            "demanda_semanal": demanda_semanal,
            "costo_unitario": costo_unitario,
            "proveedor": proveedor,
            "lead_time_dias": lead_time_dias
        })

        # 8. Contar productos procesados
        total_productos += 1

        # 9. Identificar productos bajo stock
        if stock_actual < stock_minimo:
            total_bajo_stock += 1

            cantidad_a_reponer = stock_maximo - stock_actual
            costo_reposicion = cantidad_a_reponer * costo_unitario

            total_unidades_reponer += cantidad_a_reponer
            costo_total_reposicion += costo_reposicion

            # Registrar producto en orden de compra urgente
            ordenes_compra.append({
                "id_producto": id_producto,
                "producto": producto,
                "cantidad_a_reponer": cantidad_a_reponer,
                "costo_total_reposicion": round(costo_reposicion, 0),
                "proveedor": proveedor
            })

            # Agrupar productos bajo stock por categoría
            if categoria not in bajo_stock_por_categoria:
                bajo_stock_por_categoria[categoria] = 0

            bajo_stock_por_categoria[categoria] += 1

            # Agrupar productos bajo stock por proveedor
            if proveedor not in alertas_por_proveedor:
                alertas_por_proveedor[proveedor] = 0

            alertas_por_proveedor[proveedor] += 1

            # Identificar casos de extrema urgencia
            if lead_time_dias > 5:
                casos_extrema_urgencia.append({
                    "id_producto": id_producto,
                    "producto": producto
                })

        # 10. Identificar productos con sobrestock
        if stock_actual > stock_maximo:
            total_sobrestock += 1

# 11. Determinar categoría con mayor cantidad de productos bajo stock
categoria_mas_critica = None
cantidad_categoria_critica = 0

for categoria, cantidad in bajo_stock_por_categoria.items():
    if cantidad > cantidad_categoria_critica:
        categoria_mas_critica = categoria
        cantidad_categoria_critica = cantidad

# 12. Escribir archivo de salida con órdenes de compra urgente
columnas_salida = [
    "id_producto",
    "producto",
    "cantidad_a_reponer",
    "costo_total_reposicion",
    "proveedor"
]

with open(ARCHIVO_SALIDA, mode="w", encoding="utf-8", newline="") as archivo_salida:
    escritor = csv.DictWriter(archivo_salida, fieldnames=columnas_salida)
    escritor.writeheader()
    escritor.writerows(ordenes_compra)

# 13. Mostrar resumen de resultados por consola
print("===== RESUMEN DE INVENTARIO DIMAULE SpA =====")
print(f"Total de productos procesados: {total_productos}")
print(f"Productos bajo stock: {total_bajo_stock}")
print(f"Productos con sobrestock: {total_sobrestock}")
print(f"Total de unidades a reponer: {total_unidades_reponer}")
print(f"Costo total de reposición: ${costo_total_reposicion:,.0f}")
print(f"Categoría más crítica: {categoria_mas_critica}")
print("")

print("===== ALERTAS POR PROVEEDOR =====")
for proveedor, cantidad in alertas_por_proveedor.items():
    print(f"{proveedor}: {cantidad} productos")

print("")

print("===== CASOS DE EXTREMA URGENCIA =====")
for caso in casos_extrema_urgencia:
    print(f"{caso['id_producto']} - {caso['producto']}")

print("")
print(f"Archivo generado: {ARCHIVO_SALIDA}")
