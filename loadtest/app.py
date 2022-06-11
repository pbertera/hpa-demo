#!/usr/bin/python
from flask import Flask, request, jsonify, make_response
import requests
from multiprocessing import Pool
from threading import Thread, current_thread
import time
import psutil
import os

application = Flask(__name__)

@application.route('/api/loadtest/v1/healthz')
def healthz():
    return make_response(jsonify({"health": "ok"}), 200)

def allocate_memory(size, seconds):
    thread = current_thread().name
    print('{} - Started allocating {} MB for {} seconds'.format(thread, size, seconds))
    try:
      dummy = ' ' * 1024 * 1024 * size
    except MemoryError:
      print("Ran out of memory", 400)
    time.sleep(seconds)
    print('{} - Done, freeing memory'.format(thread))
    dummy = ''

@application.route('/api/loadtest/v1/mem/<int:size>/<int:seconds>')
def memory(size, seconds):
    thread = Thread(target=allocate_memory, args=(size,seconds))
    thread.daemon = True
    thread.start()
    return make_response(jsonify(message="Allocated {} Megabytes for {} seconds".format(size, seconds)), 200)

def allocate_cpu(x, seconds):
    pid = psutil.Process().pid
    start = time.time()
    print('{} - Started using 1 CPU core for {} seconds'.format(pid, seconds))
    while True:
      now = time.time()
      if (now - start) > seconds:
        break
      x*x
    print('{} - Done, freeing 1 core'.format(pid))

@application.route('/api/loadtest/v1/cpu/<int:cpus>/<int:seconds>')
def cpu(cpus, seconds):
    if (cpus > psutil.cpu_count()):
        return make_response(jsonify(error="Requested cpus > number of cores available."), 400)

    print('Utilizing %d cores' % cpus)
    pool = Pool(processes=cpus)
    for c in range(cpus):
        pool.apply_async(allocate_cpu, (c, seconds,))
    return make_response(jsonify(message="Allocated {} cores for {} seconds".format(cpus, seconds)), 200)

@application.route('/api/loadtest/v1/stats')
def stats():
    stats = {'hostname': os.environ.get('HOSTNAME', 'null'), 'processes': [], 'cores': psutil.cpu_count()}
    p = psutil.Process()
    proc_cpu = p.cpu_percent(interval=0.1)
    proc_mem = p.memory_info().rss / 1024 / 1024
    stats['processes'].append({'pid': p.pid,'cpu': proc_cpu, 'mem': proc_mem})
    for children in p.children():
        proc_cpu = children.cpu_percent(interval=0.1)
        proc_mem = children.memory_info().rss / 1024 /1024
        stats['processes'].append({'pid': children.pid, 'cpu': proc_cpu, 'mem': proc_mem})
    return make_response(jsonify(stats), 200)

if __name__ == '__main__':
    start_cpu_peak_seconds = int(os.environ.get('START_CPU_PEAK_SEC', 0))
    start_cpu_peak_cores = int(os.environ.get('START_CPU_PEAK_CORES', 1))
    if start_cpu_peak_seconds > 0:
        pool = Pool(processes=start_cpu_peak_cores)
        for c in range(start_cpu_peak_cores):
            pool.apply_async(allocate_cpu, (c, start_cpu_peak_seconds,))
    application.run(host='0.0.0.0',port=8080)
