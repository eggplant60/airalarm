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

# Primary key の重複は無視してコピー(UPSERT)
def process_file(con, cur, table_name, file_object):
    cur.execute(sql_create % "tmp")
    sql_copy = "COPY tmp FROM STDIN WITH CSV HEADER DELIMITER AS ','"
    cur.copy_expert(sql=sql_copy, file=file_object)
    sql_upsert = """INSERT INTO %s (date, humidity, temperature, pressure, illuminance)
                        SELECT date, humidity, temperature, pressure, illuminance
                        FROM tmp
                    ON CONFLICT ON CONSTRAINT environment_pkey
                    DO NOTHING;""" % table_name  # environment_pkey は制約名
    cur.execute(sql_upsert)
    cur.execute("DROP TABLE %s;" % "tmp")  # 削除
    con.commit() # auto commitではないので、明示的なcommitの実行が必要


if __name__ == '__main__':
    table_name = "environment"
    csv_path   = "log.csv"

    sql_create = """CREATE TABLE IF NOT EXISTS %s (
                           date timestamp PRIMARY KEY,
                           humidity float,
                           temperature float,
                           pressure float,
                           illuminance float);
    """
    with get_connection() as con:
        with con.cursor() as cur:
            # コメントインしない
            #cur.execute("DROP TABLE %s;" % table_name)
            cur.execute(sql_create % table_name)

            # むやみにコメントインしない
            # cur.execute("DELETE FROM %s;" % table_name)

            with open(csv_path, "r") as f:
                process_file(con, cur, table_name, f)

            cur.execute("SELECT COUNT(*) FROM %s;" % table_name)
            results = cur.fetchall()
            print(results)

#cur.execute("INSERT INTO test (num, data) VALUES (%s, %s)", (200, "ghi_jkl"))
