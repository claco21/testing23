#!/usr/bin/env python3
"""
Script sencillo de monitorización (sin dependencias externas).
- Registra uso de RAM y disco.
- Busca procesos `java` y reporta uso RSS (kB) por PID.
- Es idóneo para ejecutar manualmente o desde cron.
"""

import os
import shutil
import subprocess
import time
from datetime import datetime
import argparse

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOG_PATH = os.path.join(BASE_DIR, 'monitor.log')
TH_RAM = 80    # umbral % de RAM usada para alerta
TH_DISK = 90   # umbral % de disco usado para alerta (raíz '/')


def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"{ts} - {msg}\n"
    with open(LOG_PATH, 'a') as f:
        f.write(line)
    print(line, end='')


def get_mem_percent():
    try:
        with open('/proc/meminfo', 'r') as f:
            info = f.read()
        mem = {}
        for l in info.splitlines():
            parts = l.split(':')
            if len(parts) < 2:
                continue
            key = parts[0]
            val = parts[1].strip().split()[0]
            mem[key] = int(val)
        total = mem.get('MemTotal', 0)
        avail = mem.get('MemAvailable', mem.get('MemFree', 0) + mem.get('Buffers', 0) + mem.get('Cached', 0))
        if total == 0:
            return 0
        used_pct = (total - avail) / total * 100
        return round(used_pct, 1)
    except Exception as e:
        return 0


def get_disk_percent(path='/'):
    try:
        total, used, free = shutil.disk_usage(path)
        return round(used / total * 100, 1)
    except Exception:
        return 0


def find_java_pids():
    try:
        out = subprocess.check_output(['pgrep', '-f', 'java']).decode().strip()
        if not out:
            return []
        return [int(x) for x in out.split() if x.strip()]
    except subprocess.CalledProcessError:
        return []
    except Exception:
        return []


def get_rss_kb(pid):
    try:
        with open(f'/proc/{pid}/status', 'r') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    return int(line.split()[1])
    except Exception:
        pass
    return 0


def get_cmdline(pid):
    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as f:
            raw = f.read().replace(b'\x00', b' ').strip()
            return raw.decode(errors='ignore')
    except Exception:
        return ''


def watch_java(interval=2, filter_keywords=None):
    """Muestra en tiempo real el uso RSS (MB) de procesos java.
    Si se proporcionan `filter_keywords` se priorizan procesos cuyo
    cmdline contenga alguna de esas palabras (ej. 'forge', 'minecraft').
    """
    if filter_keywords is None:
        filter_keywords = ['forge', 'minecraft', 'kubejs', 'server', 'paper', 'spigot']

    try:
        while True:
            # recoger pids java
            pids = find_java_pids()
            rows = []
            for pid in pids:
                rss_kb = get_rss_kb(pid)
                mb = round(rss_kb / 1024, 1)
                cmd = get_cmdline(pid)
                score = 0
                for kw in filter_keywords:
                    if kw.lower() in cmd.lower():
                        score += 1
                rows.append((score, pid, mb, cmd))

            # ordenar: primero por score (procesos que parecen servidor), luego por uso memoria
            rows.sort(key=lambda x: (x[0], x[2]), reverse=True)

            # limpiar pantalla simple
            print('\033[H\033[J', end='')
            print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            if not rows:
                print('No se encontraron procesos java.')
            else:
                print(f"{'PID':>6} {'MB':>7}  CMD")
                for score, pid, mb, cmd in rows:
                    mark = '*' if score > 0 else ' '
                    short = cmd if len(cmd) < 120 else cmd[:117] + '...'
                    print(f"{mark}{pid:6} {mb:7}  {short}")

            print('\nPresiona Ctrl+C para salir. Actualizando en {}s...'.format(interval))
            time.sleep(interval)
    except KeyboardInterrupt:
        print('\nSaliendo del modo watch...')


def main():
    mem = get_mem_percent()
    disk = get_disk_percent('/')
    log(f"RAM usada: {mem}% | Disco (/) usado: {disk}%")

    if mem >= TH_RAM:
        log(f"ALERTA: RAM usada >= {TH_RAM}% -> {mem}%")
    if disk >= TH_DISK:
        log(f"ALERTA: Disco usado >= {TH_DISK}% -> {disk}%")

    pids = find_java_pids()
    if not pids:
        log("No se han encontrado procesos java activos.")
    else:
        details = []
        for pid in pids:
            rss = get_rss_kb(pid)
            # convertir a MB
            mb = round(rss / 1024, 1)
            # obtener cmdline si es posible
            try:
                with open(f'/proc/{pid}/cmdline', 'rb') as f:
                    raw = f.read().replace(b'\x00', b' ').strip()
                    cmd = raw.decode(errors='ignore')
            except Exception:
                cmd = ''
            details.append((pid, mb, cmd))
        # ordenar por memoria descendente
        details.sort(key=lambda x: x[1], reverse=True)
        log('Procesos java (PID, RSS_MB, cmdline):')
        for pid, mb, cmd in details:
            log(f"  {pid} - {mb} MB - {cmd}")


def _build_argparser():
    p = argparse.ArgumentParser(description='Monitor simple de RAM/disco y procesos Java')
    p.add_argument('--watch', action='store_true', help='Modo interactivo: mostrar uso en tiempo real de procesos java')
    p.add_argument('--interval', type=float, default=2.0, help='Intervalo (s) para --watch (por defecto 2s)')
    p.add_argument('--filter', type=str, help='Palabras separadas por comas para priorizar procesos (ej: forge,minecraft)')
    return p


if __name__ == '__main__':
    parser = _build_argparser()
    args = parser.parse_args()
    if args.watch:
        kws = None
        if args.filter:
            kws = [x.strip() for x in args.filter.split(',') if x.strip()]
        watch_java(interval=args.interval, filter_keywords=kws)
    else:
        main()
