# Copyright (c) 2026, Mania and Contributors
# See license.txt

# import frappe
from frappe.tests.utils import FrappeTestCase

# Reachable from training_status.farmer_training, so this module's own pruning is
# what keeps the preloader out of Branch (see the note in test_crop.py).
IGNORE_TEST_RECORD_DEPENDENCIES = ["Branch"]


class TestFarmerTraining(FrappeTestCase):
	pass
