"""CPU y memoria de un proceso cada segundo (script del enunciado §5, con salida como argumento).
Uso: python monitor.py <PID> <salida.csv>   (se detiene con Ctrl+C o kill)"""
import csv
import sys
import time

import psutil

p = psutil.Process(int(sys.argv[1]))
with open(sys.argv[2], "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["hora", "cpu_%", "memoria_MB"])
    try:
        while True:
            w.writerow([time.strftime("%H:%M:%S"), p.cpu_percent(interval=1), round(p.memory_info().rss / 1e6, 1)])
            f.flush()
    except psutil.NoSuchProcess:  # el proceso medido terminó
        pass
