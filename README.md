# procesador_inventario_v3

Procesador de inventario del Centro de Distribución de DIMAULE SpA (Curicó), versión 3.0.
Evaluación sumativa de la Unidad 3 del diplomado *Fundamentos de Programación y Análisis de Datos para la Industria Logística Digital* (Educación Continua INACAP).

## Descripción
El programa lee el archivo `data/inventario_cd.csv`, valida cada registro según las reglas de negocio RN-01 a RN-07, calcula la cantidad y el costo de reposición de los productos bajo stock, identifica los casos de extrema urgencia y genera el archivo `ordenes_compra_urgente_v3.csv`. Los errores y eventos quedan registrados en `errores.log`.

## Archivos
- `analisis_inventario_v2.py`: script base de la Unidad 2 (versión anterior).
- `procesador_inventario_v3.py`: versión 3.0 (en desarrollo).
- `data/inventario_cd.csv`: archivo de entrada.

## Requisitos
- Python 3.10 o superior.
- Solo librería estándar (csv, logging, datetime, re). No requiere instalar paquetes.

## Ejecución
Desde la carpeta del proyecto:

```
py procesador_inventario_v3.py
```

## Autor
Alberto Guarda Caro
