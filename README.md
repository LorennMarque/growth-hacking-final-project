# growth-hacking-final-project

Modelo cuantitativo de growth para LatamTV basado en el workbook del caso.

## Uso

Buscar la mejor asignacion con presupuesto maximo de USD 60.000 e incrementos
semanales de USD 100:

```bash
python3 main.py --budget 60000 --step 100 --top 10
```

Buscar solo combinaciones que gasten exactamente USD 60.000:

```bash
python3 main.py --budget 60000 --step 100 --top 10 --require-full-budget
```

Exportar resultados:

```bash
python3 main.py --save-all data/processed/allocation_search.csv
python3 main.py --save-top data/processed/top_allocations.csv
```
