"""Bounded dependency failure uses real local sockets; no shared service changes."""
import unittest
from unittest.mock import patch
from openai_engine_adapter.dependency_failure_invoice import lookup_invoice


class DependencyFailureTests(unittest.TestCase):
    def test_out_of_scope_never_opens_socket(self):
        with patch('openai_engine_adapter.dependency_failure_invoice.socket.socket') as socket:
            with self.assertRaises(PermissionError):
                lookup_invoice('customer-invoice')
            socket.assert_not_called()

    def test_unavailable_dependency_releases_no_invoice(self):
        with self.assertRaisesRegex(ConnectionError, 'Synthetic invoice dependency unavailable'):
            lookup_invoice('demo-service-unavailable')
