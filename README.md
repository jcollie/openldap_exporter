# Prometheus OpenLDAP Exporter

Export metrics from your [OpenLDAP](http://www.openldap.org/) servers
to your [Prometheus](http://prometheus.io) monitoring system.

## Prerequisites

You'll need a working OpenLDAP server, and a working Prometheus
server.  Setup and installation of those is left as an exercise to the
reader.

The exporter service is developed and tested using Python 2. The
[ldaptor](https://github.com/twisted/ldaptor) requires features in
[Twisted](http://twistedmatrix.com/trac/) that have not been ported to
Python 3 as of Twisted 16.4.0.

## How it Works

The OpenLDAP exporter opens up a new LDAP connection to the OpenLDAP
server each time Prometheus scrapes the exporter. LDAP objects with
the ```objectClass``` of ```monitorCounterObject``` or
```monitoredObject``` under the ```cn=Monitor``` base are searched
for. Any objects that are found that have data that can be converted
to a floating point number are exported as metrics with the object's
distinguished name as a label.

See the [OpenLDAP
Manual](http://www.openldap.org/doc/admin24/monitoringslapd.html) for
more information on how OpenLDAP exposes performance metrics.


## Installation

```bash
git clone https://github.com/jcollie/openldap_exporter.git
cd openldap_exporter
virtualenv --python=/usr/bin/python2 /opt/openldap_exporter
/opt/openldap_exporter/bin/pip install --requirement requirements.txt
cp openldap_exporter.py /opt/openldap_exporter
cp openldap_exporter.yml /opt/openldap_exporter
vi /opt/openldap_exporter/openldap_exporter.yml
# edit configuration file
cp openldap_exporter.service /etc/systemd/system
systemctl daemon-reload
systemctl enable openldap_exporter
systemctl start openldap_exporter
```

## Configuration

### OpenLDAP

The OpenLDAP configuration needs to be modified to allow querying the
monitoring database over a remote connection. The following command should be run
on the OpenLDAP server:

```
# ldapmodify -Y EXTERNAL -H ldapi:// <<EOF
dn: olcDatabase={1}monitor,cn=config
changetype: modify
replace: olcAccess
olcAccess: to * by dn.base="gidNumber=0+uidNumber=0,cn=peercred,cn=external,cn=auth" read by dn.base="cn=Manager,dc=example,dc=com" read by * none
-
EOF
```

Replace ```cn=Manager,dc=example,dc=com``` with the distinguished name
of the user that you want to read the metrics with.

Consult the OpenLDAP manual for more information on configuring
OpenLDAP access lists.

### Exporter

The exporter is configured using command line options:

```
usage: openldap_exporter [-h] --config CONFIG

Prometheus OpenLDAP exporter

optional arguments:
  -h, --help       show this help message and exit
  --config CONFIG  configuration file
```

The configuration file is a YAML formatted file that looks like this:

```
---
server: tcp:port=9142
client: tcp:host=127.0.0.1:port=389
binddn: cn=Manager,dc=example,dc=com
bindpw: changeme
```

Twisted server endpoint specifiers are described
[here](https://twistedmatrix.com/documents/current/core/howto/endpoints.html#servers). Twisted
client endpoint specifiers are described
[here](https://twistedmatrix.com/documents/current/core/howto/endpoints.html#clients).

### Prometheus

Add a job to your Promethus configuration that looks like the following:

```
scrape_configs:
  - job_name: 'openldap'
    scrape_interval: 30s
    scrape_timeout: 10s
    target_groups:
      - targets:
        - 'localhost:9142'
```

## Example Output

```
openldap_up 1
openldap_monitor_counter_object{dn="cn=Max File Descriptors,cn=Connections,cn=Monitor"} 1024.0
openldap_monitor_counter_object{dn="cn=Total,cn=Connections,cn=Monitor"} 1553.0
openldap_monitor_counter_object{dn="cn=Current,cn=Connections,cn=Monitor"} 5.0
openldap_monitor_counter_object{dn="cn=Bytes,cn=Statistics,cn=Monitor"} 57082372.0
openldap_monitor_counter_object{dn="cn=PDU,cn=Statistics,cn=Monitor"} 2243556.0
openldap_monitor_counter_object{dn="cn=Entries,cn=Statistics,cn=Monitor"} 567713.0
openldap_monitor_counter_object{dn="cn=Referrals,cn=Statistics,cn=Monitor"} 0.0
openldap_monitor_counter_object{dn="cn=Read,cn=Waiters,cn=Monitor"} 5.0
openldap_monitor_counter_object{dn="cn=Write,cn=Waiters,cn=Monitor"} 0.0
openldap_monitored_object{dn="cn=Max,cn=Threads,cn=Monitor"} 16.0
openldap_monitored_object{dn="cn=Max Pending,cn=Threads,cn=Monitor"} 0.0
openldap_monitored_object{dn="cn=Open,cn=Threads,cn=Monitor"} 9.0
openldap_monitored_object{dn="cn=Starting,cn=Threads,cn=Monitor"} 0.0
openldap_monitored_object{dn="cn=Active,cn=Threads,cn=Monitor"} 1.0
openldap_monitored_object{dn="cn=Pending,cn=Threads,cn=Monitor"} 0.0
openldap_monitored_object{dn="cn=Backload,cn=Threads,cn=Monitor"} 1.0
openldap_monitored_object{dn="cn=Uptime,cn=Time,cn=Monitor"} 3351414.0
```