# -*- mode: python; coding: utf-8 -*-

# Copyright © 2017 by Jeffrey C. Ollie <jeff@ocjtech.us>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see
# <http://www.gnu.org/licenses/>.

import argparse
import sys
import yaml

from ldaptor.protocols.ldap.ldapclient import LDAPClient
from ldaptor.protocols.ldap.ldapsyntax import LDAPEntry

from twisted.internet import reactor
from twisted.internet.endpoints import clientFromString
from twisted.internet.endpoints import serverFromString
from twisted.internet.protocol import Factory
from twisted.logger import Logger
from twisted.logger import globalLogBeginner
from twisted.logger import textFileLogObserver
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET
from twisted.web.server import Site

class QuietSite(Site):
   noisy = False

class LDAPFactory(Factory):
   noisy = False

   def buildProtocol(self, address):
      return LDAPClient()

class Metrics(object):
   log = Logger()

   basedn = 'cn=Monitor'
   query = '(|(objectClass=monitorCounterObject)(objectClass=monitoredObject))'

   def __init__(self, request, config):
      self.request = request
      self.config = config
      factory = LDAPFactory()
      endpoint = clientFromString(reactor, self.config['client'])
      d = endpoint.connect(factory)
      d.addCallback(self.gotConnection)

   def gotConnection(self, client):
      self.client = client
      if 'binddn' in self.config:
         d = self.client.bind(self.config['binddn'], self.config['bindpw'])
      else:
         d = self.client.bind()
      d.addCallback(self.isAuthenticated)

   def isAuthenticated(self, result):
      base = LDAPEntry(self.client, self.basedn)
      d = base.search(filterText = self.query, attributes = ('*', '+'))
      d.addCallback(self.gotResults)

   def gotResults(self, results):
      self.request.setHeader(b'Content-Type', b'text/plain; charset=utf-8; version=0.0.4')

      self.request.write('openldap_up 1\n'.encode('utf-8'))

      for entry in results:
         if 'monitorCounterObject' in entry['objectClass']:
            if 'monitorCounter' in entry and len(entry['monitorCounter']) == 1:
               try:
                  labels = 'dn="{}"'.format(entry.dn)
                  value = float(entry['monitorCounter'].pop())
                  self.request.write('openldap_monitor_counter_object{{{}}} {}\n'.format(labels, value).encode('utf-8'))
               except ValueError:
                  pass

      for entry in results:
         if 'monitoredObject' in entry['objectClass']:
            if 'monitoredInfo' in entry and len(entry['monitoredInfo']) == 1:
               try:
                  labels = 'dn="{}"'.format(entry.dn)
                  value = float(entry['monitoredInfo'].pop())
                  self.request.write('openldap_monitored_object{{{}}} {}\n'.format(labels, value).encode('utf-8'))
               except ValueError:
                  pass

      self.request.finish()
      self.client.unbind()
      self.client.transport.loseConnection()

class MetricsPage(Resource):
   log = Logger()
   isLeaf = True

   def __init__(self, config):
      self.config = config
      Resource.__init__(self)

   def render_GET(self, request):
      Metrics(request, config)
      return NOT_DONE_YET

class RootPage(Resource):
   isLeaf = False

   def render_GET(self, request):
      request.setHeader(b'Content-Type', b'text/plain; charset=utf-8')
      return 'OK\n'.encode('utf-8')

parser = argparse.ArgumentParser(prog = 'openldap_exporter',
                                 description = 'Prometheus OpenLDAP exporter')
parser.add_argument('--config',
                    type = argparse.FileType('r'),
                    help = 'configuration file',
                    required = True)
arguments = parser.parse_args()

config = yaml.load(arguments.config)
arguments.config.close()

output = textFileLogObserver(sys.stderr, timeFormat='')
globalLogBeginner.beginLoggingTo([output])

metrics = MetricsPage(config)
root = RootPage()
root.putChild(b'metrics', metrics)
site = QuietSite(root)
endpoint = serverFromString(reactor, config['server'])
endpoint.listen(site)

reactor.run()
