#!/bin/bash
set -euo pipefail
umask 022

install -d -m 755 /opt/guestbook /etc/guestbook
install -d -m 700 /var/lib/guestbook

if ! id guestbook >/dev/null 2>&1; then
    useradd --system --no-create-home --shell /sbin/nologin guestbook
fi

# Download only the files required by the application.
for file in app.py bootstrap.py schema.sql requirements.txt; do
    aws s3 cp "s3://$CODE_BUCKET/$file" "/opt/guestbook/$file" \
        --region "$AWS_REGION" --only-show-errors
    chmod 644 "/opt/guestbook/$file"
done

# Use AWS's public RDS certificate bundle to verify database connections.
curl --fail --silent --show-error \
    --output /etc/guestbook/rds-ca.pem.tmp \
    https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
mv /etc/guestbook/rds-ca.pem.tmp /etc/guestbook/rds-ca.pem
chmod 644 /etc/guestbook/rds-ca.pem

python3 -m venv /opt/guestbook/venv
/opt/guestbook/venv/bin/python -m pip install \
    -r /opt/guestbook/requirements.txt

# Retrieve the administrator credential and provision the restricted SQL user.
/opt/guestbook/venv/bin/python /opt/guestbook/bootstrap.py

cat > /etc/systemd/system/guestbook.service <<'SERVICE'
[Unit]
Description=Guestbook application API
Wants=network-online.target
After=network-online.target

[Service]
User=guestbook
Group=guestbook
WorkingDirectory=/opt/guestbook
EnvironmentFile=/etc/guestbook/environment
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/opt/guestbook/venv/bin/gunicorn --workers 2 --bind 0.0.0.0:8000 --access-logfile - --error-logfile - app:app
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
UMask=0077

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable guestbook
systemctl restart guestbook

# Mark provisioning complete only when the API can reach its database.
curl --fail --silent --show-error \
    --retry 10 --retry-connrefused --retry-delay 3 \
    http://127.0.0.1:8000/api/health

touch /var/lib/guestbook/initialized