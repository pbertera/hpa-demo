#!/usr/bin/python
from flask import Flask, request, jsonify, make_response
import requests
from multiprocessing import Pool
from multiprocessing import cpu_count
from threading import Thread, current_thread
import time

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
    return make_response("Started memory thread {}".format(thread.name), 200)

def f(x):
    loop_count = 1000 * 1024 * 250
    while loop_count > 0:
      x*x
      loop_count = loop_count - 1

@application.route('/api/loadtest/v1/cpu/<int:cpus>')
def cpu(cpus):

    print('Number of cpus available: %d' % cpu_count())
    if (cpus > cpu_count()):
        return make_response("Requested cpus > number of cores available.", 400)

    print('-' * 20)
    print('Running load on CPU(s)')
    print('Utilizing %d cores' % cpus)
    print('-' * 20)
    pool = Pool(cpus)
    pool.map(f, range(cpus))
    pool.close()

    return make_response("", 200)

if __name__ == '__main__':
     application.run(host='0.0.0.0',port=8080)
