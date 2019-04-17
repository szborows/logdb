#!/usr/bin/env python3

import argparse
import datetime
import hashlib
import random
import math
import json
import requests


word_site = "http://svnweb.freebsd.org/csrg/share/dict/words?view=co&content-type=text/plain"
_response = requests.get(word_site)
_response.raise_for_status()
WORDS = [x.decode() for x in _response.content.splitlines()]


def is_prime(n):
    if n % 2 == 0 and n > 2: 
        return False
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        if n % i == 0:
            return False
    return True

def is_fib(n):
    return n in (0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765, 10946, 17711, 28657, 46368, 75025, 121393, 196418, 317811, 514229, 832040, 1346269, 2178309, 3524578, 5702887, 9227465, 14930352, 24157817, 39088169, 63245986, 102334155, 165580141, 267914296, 433494437, 701408733, 1134903170, 1836311903, 2971215073, 4807526976, 7778742049)


def generate(size):
    dt = datetime.datetime(year=1989, month=5, day=11)
    ipv4 = '192.168.0.42'
    step = datetime.timedelta(seconds=1)
    fdt = datetime.datetime.strftime

    def gen_line(nr, dt, line):
        ci_chars = 'abcdef0123456789'
        ci = ''.join([random.choice(ci_chars), random.choice(ci_chars)])
        component = random.choice(['CMP1-1234', 'CMP2-1010', 'CMP3-4202'])
        app = random.choice(['app1', 'app2', 'app3', 'app4', 'app5'])
        return '{line_number:07} {dt} [{ipv4}] {component} {severity}/{app}: {line}'.format(
            line_number=int(str(nr)[-7:]),
            dt=fdt(dt, '%m.%y %H:%M:%S.000'),
            ipv4=ipv4,
            component=component,
            severity='DBG',
            app=app,
            line=line)

    for i in range(size):
        even_specifier = ['even', 'odd'][i % 2]
        dt_ = dt + i * step
        line = gen_line(i, dt_, ' '.join([random.choice(WORDS) for x in range(10)]))
        file_id = int(i / 100000) + 1
        res_line = gen_line(i, dt_, line)
        tags = [[], ['prime']][is_prime(i)] + [[], ['fib']][is_fib(i)]
        labels = {'file': file_id}
        print(json.dumps({'tags': tags, 'labels': labels, 'timestamp': int(dt_.timestamp()), 'line': line}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('size', type=int)
    args = parser.parse_args()
    generate(args.size)
