import streamlit as st
import pymysql
import os

def get_conn():
    try: 
        cfg = st.secrets["AIVEN"]
    except: 
        cfg = {
            "host": str(os.getenv("AIVEN_HOST")),
            "port": int(os.getenv("AIVEN_PORT")),
            "user": str(os.getenv("AIVEN_USER")),
            "password": str(os.getenv("AIVEN_PASSWORD")),
            "db": str(os.getenv("AIVEN_DB"))
        }

    timeout = 10
    conn = pymysql.connect(
        host=cfg["host"],
        port=int(cfg["port"]),
        user=cfg["user"],
        password=cfg["password"],
        db=cfg["db"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=timeout,
        read_timeout=timeout,
        write_timeout=timeout,
        ssl={"ssl": {}}  # this enables SSL without needing the cert path
    )
    return conn
