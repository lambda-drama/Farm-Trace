# Copyright (c) 2026, Mania and Contributors
# See license.txt

# import frappe
from frappe.tests.utils import FrappeTestCase

# Link targets from apps a bare test site does not install. Frappe preloads global
# test records by walking every Link field of the doctype and raises
# DoesNotExistError on the first missing one (CI installs frappe + farmtrace only).
IGNORE_TEST_RECORD_DEPENDENCIES = ["Branch", "Warehouse"]


class TestTrainingStatus(FrappeTestCase):
	pass
