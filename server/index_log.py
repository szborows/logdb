#!/usr/bin/env python3
import argparse
import json
import sqlite3
import pathlib


def index_log(input_path, output_path):
    if pathlib.Path(output_path).exists():
        raise RuntimeError(f'file {output_path} already exists!')
    conn = sqlite3.connect(output_path)

    CREATE_TABLE = '''
        CREATE TABLE logs (
            tags varchar(255),
            labels varchar(512),
            timestamp int,
            line text NOT NULL
        );
    '''
    c = conn.cursor()
    c.execute(CREATE_TABLE)

    with open(input_path) as f:
        for line in f:
            j = json.loads(line)
            tags, labels, timestamp, line = ','.join(j['tags']), ','.join(j['labels']), j['timestamp'], j['line']
            c.execute(
                f'INSERT INTO logs (tags, labels, timestamp, line) VALUES '
                f'("{tags}", "{labels}", "{timestamp}", "{line}")'
            )
        conn.commit()

    conn.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('input_file')
    ap.add_argument('output_file')
    args = ap.parse_args()
    index_log(args.input_file, args.output_file)
