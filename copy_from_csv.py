# -*- coding:utf-8 -*-
import psycopg2
from postgres import * # user, password


def get_connection():
    return psycopg2.connect(
        host = "192.168.11.205",
        port = 5432,
        database = "airalarm",
        user = user,
        password = password)


def process_file(con, cur, table_name, file_object):
    cur.copy_expert(
        sql="COPY %s FROM STDIN WITH CSV HEADER DELIMITER AS ','" % table_name,
        file=file_object
    )
    con.commit() # auto commitではないので、明示的なcommitの実行が必要


if __name__ == '__main__':
    table_name = "environment"
    csv_path   = "log.csv"

    with get_connection() as con:
        with con.cursor() as cur:
            cur.execute("DROP TABLE %s;" % table_name)
            cur.execute("""CREATE TABLE IF NOT EXISTS %s (
                             date timestamp PRIMARY KEY, 
                             humidity float,
                             temperature float,
                             pressure float,
                             illuminance float
            );""" % table_name)

            # cur.execute("DELETE FROM %s;" % table_name)

            with open(csv_path, "r") as f:
                process_file(con, cur, table_name, f)

            cur.execute("SELECT COUNT(*) FROM %s;" % table_name)
            results = cur.fetchall()
            print(results)

#cur.execute("INSERT INTO test (num, data) VALUES (%s, %s)", (200, "ghi_jkl"))
