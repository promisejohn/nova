# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Tests for nova websocketproxy."""


import mock

from nova.console import websocketproxy
from nova import exception
from nova import test
from oslo_config import cfg

CONF = cfg.CONF


class NovaProxyRequestHandlerBaseTestCase(test.NoDBTestCase):

    def setUp(self):
        super(NovaProxyRequestHandlerBaseTestCase, self).setUp()

        self.wh = websocketproxy.NovaProxyRequestHandlerBase()
        self.wh.socket = mock.MagicMock()
        self.wh.msg = mock.MagicMock()
        self.wh.do_proxy = mock.MagicMock()
        self.wh.headers = mock.MagicMock()
        CONF.set_override('novncproxy_base_url',
                          'https://example.net:6080/vnc_auto.html')
        CONF.set_override('html5proxy_base_url',
                          'https://example.net:6080/vnc_auto.html',
                          'spice')
        CONF.set_override('base_url',
                          'ws://example.net:6080',
                          'serial_console')

    def _fake_getheader(self, header):
        if header == 'cookie':
            return 'token="123-456-789"'
        elif header == 'Origin':
            return 'https://example.net:6080'
        elif header == 'Host':
            return 'example.net:6080'
        else:
            return

    def _fake_getheader_bad_token(self, header):
        if header == 'cookie':
            return 'token="XXX"'
        elif header == 'Origin':
            return 'https://example.net:6080'
        elif header == 'Host':
            return 'example.net:6080'
        else:
            return

    def _fake_getheader_bad_origin(self, header):
        if header == 'cookie':
            return 'token="123-456-789"'
        elif header == 'Origin':
            return 'https://bad-origin-example.net:6080'
        elif header == 'Host':
            return 'example.net:6080'
        else:
            return

    def _fake_getheader_blank_origin(self, header):
        if header == 'cookie':
            return 'token="123-456-789"'
        elif header == 'Origin':
            return ''
        elif header == 'Host':
            return 'example.net:6080'
        else:
            return

    def _fake_getheader_no_origin(self, header):
        if header == 'cookie':
            return 'token="123-456-789"'
        elif header == 'Origin':
            return None
        elif header == 'Host':
            return 'any-example.net:6080'
        else:
            return

    def _fake_getheader_http(self, header):
        if header == 'cookie':
            return 'token="123-456-789"'
        elif header == 'Origin':
            return 'http://example.net:6080'
        elif header == 'Host':
            return 'example.net:6080'
        else:
            return

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client(self, check_token):
        check_token.return_value = {
            'host': 'node1',
            'port': '10000',
            'console_type': 'novnc'
        }
        self.wh.socket.return_value = '<socket>'
        self.wh.path = "http://127.0.0.1/?token=123-456-789"
        self.wh.headers.getheader = self._fake_getheader

        self.wh.new_websocket_client()

        check_token.assert_called_with(mock.ANY, token="123-456-789")
        self.wh.socket.assert_called_with('node1', 10000, connect=True)
        self.wh.do_proxy.assert_called_with('<socket>')

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_token_invalid(self, check_token):
        check_token.return_value = False

        self.wh.path = "http://127.0.0.1/?token=XXX"
        self.wh.headers.getheader = self._fake_getheader_bad_token

        self.assertRaises(exception.InvalidToken,
                          self.wh.new_websocket_client)
        check_token.assert_called_with(mock.ANY, token="XXX")

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_novnc(self, check_token):
        check_token.return_value = {
            'host': 'node1',
            'port': '10000',
            'console_type': 'novnc'
        }
        self.wh.socket.return_value = '<socket>'
        self.wh.path = "http://127.0.0.1/"
        self.wh.headers.getheader = self._fake_getheader

        self.wh.new_websocket_client()

        check_token.assert_called_with(mock.ANY, token="123-456-789")
        self.wh.socket.assert_called_with('node1', 10000, connect=True)
        self.wh.do_proxy.assert_called_with('<socket>')

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_serial(self, check_token):
        check_token.return_value = {
            'host': 'node1',
            'port': '10000',
            'console_type': 'serial'
        }
        self.wh.socket.return_value = '<socket>'
        self.wh.path = "http://127.0.0.1/"
        self.wh.headers.getheader = self._fake_getheader_http

        self.wh.new_websocket_client()

        check_token.assert_called_with(mock.ANY, token="123-456-789")
        self.wh.socket.assert_called_with('node1', 10000, connect=True)
        self.wh.do_proxy.assert_called_with('<socket>')

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_novnc_token_invalid(self, check_token):
        check_token.return_value = False

        self.wh.path = "http://127.0.0.1/"
        self.wh.headers.getheader = self._fake_getheader_bad_token

        self.assertRaises(exception.InvalidToken,
                          self.wh.new_websocket_client)
        check_token.assert_called_with(mock.ANY, token="XXX")

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_internal_access_path(self, check_token):
        check_token.return_value = {
            'host': 'node1',
            'port': '10000',
            'internal_access_path': 'vmid',
            'console_type': 'novnc'
        }

        tsock = mock.MagicMock()
        tsock.recv.return_value = "HTTP/1.1 200 OK\r\n\r\n"

        self.wh.socket.return_value = tsock
        self.wh.path = "http://127.0.0.1/?token=123-456-789"
        self.wh.headers.getheader = self._fake_getheader

        self.wh.new_websocket_client()

        check_token.assert_called_with(mock.ANY, token="123-456-789")
        self.wh.socket.assert_called_with('node1', 10000, connect=True)
        self.wh.do_proxy.assert_called_with(tsock)

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_internal_access_path_err(self, check_token):
        check_token.return_value = {
            'host': 'node1',
            'port': '10000',
            'internal_access_path': 'xxx',
            'console_type': 'novnc'
        }

        tsock = mock.MagicMock()
        tsock.recv.return_value = "HTTP/1.1 500 Internal Server Error\r\n\r\n"

        self.wh.socket.return_value = tsock
        self.wh.path = "http://127.0.0.1/?token=123-456-789"
        self.wh.headers.getheader = self._fake_getheader

        self.assertRaises(exception.InvalidConnectionInfo,
                          self.wh.new_websocket_client)
        check_token.assert_called_with(mock.ANY, token="123-456-789")

    @mock.patch('sys.version_info')
    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_py273_good_scheme(
            self, check_token, version_info):
        version_info.return_value = (2, 7, 3)
        check_token.return_value = {
            'host': 'node1',
            'port': '10000',
            'console_type': 'novnc'
        }
        self.wh.socket.return_value = '<socket>'
        self.wh.path = "http://127.0.0.1/?token=123-456-789"
        self.wh.headers.getheader = self._fake_getheader

        self.wh.new_websocket_client()

        check_token.assert_called_with(mock.ANY, token="123-456-789")
        self.wh.socket.assert_called_with('node1', 10000, connect=True)
        self.wh.do_proxy.assert_called_with('<socket>')

    @mock.patch('sys.version_info')
    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_py273_special_scheme(
            self, check_token, version_info):
        version_info.return_value = (2, 7, 3)
        check_token.return_value = {
            'host': 'node1',
            'port': '10000',
            'console_type': 'novnc'
        }
        self.wh.socket.return_value = '<socket>'
        self.wh.path = "ws://127.0.0.1/?token=123-456-789"
        self.wh.headers.getheader = self._fake_getheader

        self.assertRaises(exception.NovaException,
                          self.wh.new_websocket_client)

    @mock.patch('socket.getfqdn')
    def test_address_string_doesnt_do_reverse_dns_lookup(self, getfqdn):
        request_mock = mock.MagicMock()
        request_mock.makefile().readline.side_effect = [
            'GET /vnc.html?token=123-456-789 HTTP/1.1\r\n',
            ''
        ]
        server_mock = mock.MagicMock()
        client_address = ('8.8.8.8', 54321)

        handler = websocketproxy.NovaProxyRequestHandler(
            request_mock, client_address, server_mock)
        handler.log_message('log message using client address context info')

        self.assertFalse(getfqdn.called)  # no reverse dns look up
        self.assertEqual(handler.address_string(), '8.8.8.8')  # plain address

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_novnc_bad_origin_header(self, check_token):
        check_token.return_value = {
            'host': 'node1',
            'port': '10000',
            'console_type': 'novnc'
        }

        self.wh.path = "http://127.0.0.1/"
        self.wh.headers.getheader = self._fake_getheader_bad_origin

        self.assertRaises(exception.ValidationError,
                          self.wh.new_websocket_client)

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_novnc_blank_origin_header(self, check_token):
        check_token.return_value = {
            'host': 'node1',
            'port': '10000',
            'console_type': 'novnc'
        }

        self.wh.path = "http://127.0.0.1/"
        self.wh.headers.getheader = self._fake_getheader_blank_origin

        self.assertRaises(exception.ValidationError,
                          self.wh.new_websocket_client)

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_novnc_no_origin_header(self, check_token):
        check_token.return_value = {
            'host': 'node1',
            'port': '10000',
            'console_type': 'novnc'
        }
        self.wh.socket.return_value = '<socket>'
        self.wh.path = "http://127.0.0.1/"
        self.wh.headers.getheader = self._fake_getheader_no_origin

        self.wh.new_websocket_client()

        check_token.assert_called_with(mock.ANY, token="123-456-789")
        self.wh.socket.assert_called_with('node1', 10000, connect=True)
        self.wh.do_proxy.assert_called_with('<socket>')

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_novnc_bad_origin_proto_vnc(self,
                                                             check_token):
        check_token.return_value = {
            'host': 'node1',
            'port': '10000',
            'console_type': 'novnc'
        }

        self.wh.path = "http://127.0.0.1/"
        self.wh.headers.getheader = self._fake_getheader_http

        self.assertRaises(exception.ValidationError,
                          self.wh.new_websocket_client)

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_novnc_bad_origin_proto_spice(self,
                                                               check_token):
        check_token.return_value = {
            'host': 'node1',
            'port': '10000',
            'console_type': 'spice-html5'
        }

        self.wh.path = "http://127.0.0.1/"
        self.wh.headers.getheader = self._fake_getheader_http

        self.assertRaises(exception.ValidationError,
                          self.wh.new_websocket_client)

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_novnc_https_origin_proto_serial(self,
                                                                  check_token):
        check_token.return_value = {
            'host': 'node1',
            'port': '10000',
            'console_type': 'serial'
        }

        self.wh.path = "https://127.0.0.1/"
        self.wh.headers.getheader = self._fake_getheader

        self.assertRaises(exception.ValidationError,
                          self.wh.new_websocket_client)

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_novnc_bad_console_type(self, check_token):
        check_token.return_value = {
            'host': 'node1',
            'port': '10000',
            'console_type': 'bad-console-type'
        }

        self.wh.path = "http://127.0.0.1/"
        self.wh.headers.getheader = self._fake_getheader

        self.assertRaises(exception.ValidationError,
                          self.wh.new_websocket_client)
