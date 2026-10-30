# Evidencia ejecutada

Ejecutado por la herramienta (no por el modelo) sobre el commit `cd6d7253bf3ed565daee07fb83b64277227340fd`.

| Verificación | Comando | Resultado |
|---|---|---|
| Pruebas automatizadas | `python -m pytest -q -p no:cacheprovider` | PASÓ |
| Trazabilidad spec → pruebas | `python tools/check_trazabilidad.py` | PASÓ |
| Contrato OpenAPI → API real | `python tools/check_contrato.py` | PASÓ |

#### Salida real: Pruebas automatizadas
```text
....................................................                     [100%]
52 passed in 2.49s
```

#### Salida real: Trazabilidad spec → pruebas
```text
Trazabilidad spec → pruebas
  ✓ CA-1: tests/test_ca1_pasos_visibles.py (5 funciones de prueba)
  ✓ CA-2: tests/test_ca2_validaciones.py (6 funciones de prueba)
  ✓ CA-3: tests/test_ca3_activacion.py (5 funciones de prueba)
  ✓ CA-4: tests/test_ca4_eventos.py (5 funciones de prueba)
  ✓ CA-5: tests/test_ca5_ca6_analitica.py (7 funciones de prueba)
  ✓ CA-6: tests/test_ca5_ca6_analitica.py (7 funciones de prueba)
OK
```

#### Salida real: Contrato OpenAPI → API real
```text
Contrato (13 operaciones) frente a la API real
OK
```
