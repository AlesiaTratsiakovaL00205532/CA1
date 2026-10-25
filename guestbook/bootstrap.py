import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile

import pymysql


def main():
    if os.geteuid() != 0:
        raise PermissionError("Run database bootstrap as root.")

    host = os.environ["DB_HOST"]
    region = os.environ["AWS_REGION"]
    parameter_name = os.environ["DB_ADMIN_PARAMETER"]
    ca_path = "/etc/guestbook/rds-ca.pem"

    # Capture the decrypted password in memory, not terminal output.
    result = subprocess.run(
        [
            "aws", "ssm", "get-parameter",
            "--name", parameter_name,
            "--with-decryption",
            "--region", region,
            "--query", "Parameter.Value",
            "--output", "json",
            "--no-cli-pager",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    admin_password = json.loads(result.stdout)
    app_password = secrets.token_hex(24)

    with pymysql.connect(
        host=host,
        user="guestbookadmin",
        password=admin_password,
        database="guestbook",
        charset="utf8mb4",
        autocommit=True,
        connect_timeout=10,
        read_timeout=10,
        write_timeout=10,
        ssl_ca=ca_path,
        ssl_verify_cert=True,
        ssl_verify_identity=True,
    ) as connection:
        with connection.cursor() as cursor:
            schema = Path(__file__).with_name("schema.sql").read_text(
                encoding="utf-8"
            )
            cursor.execute(schema)

            cursor.execute(
                "CREATE USER IF NOT EXISTS 'guestbookapp'@'%%' "
                "IDENTIFIED BY %s REQUIRE SSL",
                (app_password,),
            )
            # A rerun rotates this user's password; restart the API afterward.
            cursor.execute(
                "ALTER USER 'guestbookapp'@'%%' IDENTIFIED BY %s REQUIRE SSL",
                (app_password,),
            )
            cursor.execute(
                "GRANT SELECT, INSERT ON guestbook.messages "
                "TO 'guestbookapp'@'%'"
            )

    # The API looks through this directory to get the public CA certificate.
    config_directory = Path("/etc/guestbook")
    config_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
    config_directory.chmod(0o755)

    # JSON strings provide quoted values suitable for systemd EnvironmentFile.
    settings = {
        "DB_HOST": host,
        "DB_USER": "guestbookapp",
        "DB_PASSWORD": app_password,
        "DB_NAME": "guestbook",
        "DB_SSL_CA": ca_path,
    }

    descriptor, temporary_path = tempfile.mkstemp(
        prefix=".environment-",
        dir=config_directory,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as config:
            # Only root reads this file; systemd passes values to the API.
            os.fchmod(config.fileno(), 0o600)
            for name, value in settings.items():
                config.write(f"{name}={json.dumps(value)}\n")

        os.replace(temporary_path, config_directory / "environment")
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)

    print("Database initialization completed.")


if __name__ == "__main__":
    main()