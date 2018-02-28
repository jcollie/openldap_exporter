FROM python:2

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /config

ENTRYPOINT python /usr/src/app/openldap_exporter.py --config /config/openldap_exporter.yml
