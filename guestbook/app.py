import os

import pymysql
from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4096


def connect_database():
    """Open a database connection with certificate and hostname verification."""
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=5,
        read_timeout=5,
        write_timeout=5,
        ssl_ca=os.environ["DB_SSL_CA"],
        ssl_verify_cert=True,
        ssl_verify_identity=True,
    )


@app.errorhandler(pymysql.MySQLError)
def handle_database_error(error):
    # Log the failure without exposing database details to visitors.
    app.logger.error(
        "Database operation failed",
        exc_info=(type(error), error, error.__traceback__),
    )
    return jsonify(error="Database temporarily unavailable."), 503


@app.get("/api/health")
def health():
    with connect_database() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    return jsonify(status="ok")


@app.get("/api/messages")
def list_messages():
    with connect_database() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, message FROM messages ORDER BY id DESC LIMIT 50"
            )
            messages = cursor.fetchall()

    return jsonify(messages=messages)


@app.post("/api/messages")
def add_message():
    payload = request.get_json()

    if not isinstance(payload, dict):
        return jsonify(error="Expected a JSON object."), 400

    message = payload.get("message")
    if not isinstance(message, str):
        return jsonify(error="Message must be text."), 400

    message = message.strip()
    if not 1 <= len(message) <= 500:
        return jsonify(error="Message must contain 1 to 500 characters."), 400

    with connect_database() as connection:
        with connection.cursor() as cursor:
            # Parameter binding keeps visitor input separate from SQL syntax.
            cursor.execute(
                "INSERT INTO messages (message) VALUES (%s)",
                (message,),
            )
            message_id = cursor.lastrowid

    return jsonify(id=message_id, message=message), 201