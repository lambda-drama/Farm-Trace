# Copyright (c) 2026, Mania and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from farmtrace.farm_trace.api.kobo_sync import (
	_ensure_geography,
	_get_kobo_repeat_group,
	_get_kobo_value,
	_get_or_create_farmer,
	_get_repeat_row_value,
	_post_process_farm_purchase_intake_doc,
	_refresh_linked_farmer_cache,
	_split_field_mappings,
	_sync_linked_farmer_geography,
)


class TestKoboSync(FrappeTestCase):
	def test_get_kobo_value_matches_nested_field_paths(self):
		sub = {
			"crop_procurement/payment_method": "mobile",
			"crop_procurement/mobile_payment/mobile_provider": "yass",
			"crop_procurement/mobile_payment/mobile_number": "0712150091",
			"crop_procurement/mobile_payment/mobile_name": "John Doe",
		}
		self.assertEqual(_get_kobo_value(sub, "payment_method"), "mobile")
		self.assertEqual(_get_kobo_value(sub, "mobile_payment/mobile_provider"), "yass")
		self.assertEqual(_get_kobo_value(sub, "mobile_payment/mobile_number"), "0712150091")
		self.assertEqual(_get_kobo_value(sub, "mobile_payment/mobile_name"), "John Doe")

	def test_split_field_mappings(self):
		mappings = [
			{"kobo_field_name": "farmer", "target_field": "farmer"},
			{
				"kobo_repeat_group": "crop_procurement/bag",
				"target_child_table": "items",
				"kobo_field_name": "barcode",
				"target_field": "barcode",
			},
			{
				"kobo_repeat_group": "crop_procurement/bag",
				"target_child_table": "items",
				"kobo_field_name": "bag_weight",
				"target_field": "quantity",
			},
		]
		parent_map, child_maps = _split_field_mappings(mappings, target_doctype="Farm Purchase Intake")
		self.assertEqual(parent_map, {"farmer": "farmer"})
		self.assertEqual(
			child_maps[("crop_procurement/bag", "items")],
			{"barcode": "barcode", "bag_weight": "quantity"},
		)

	def test_split_field_mappings_infers_items_child_table(self):
		mappings = [
			{
				"kobo_repeat_group": "crop_procurement/bag",
				"kobo_field_name": "barcode",
				"target_field": "barcode",
			},
			{
				"kobo_repeat_group": "crop_procurement/bag",
				"kobo_field_name": "bag_weight",
				"target_field": "quantity",
			},
		]
		_, child_maps = _split_field_mappings(mappings, target_doctype="Farm Purchase Intake")
		self.assertEqual(
			child_maps[("crop_procurement/bag", "items")],
			{"barcode": "barcode", "bag_weight": "quantity"},
		)

	def test_parent_mapping_ignores_stray_target_child_table(self):
		mappings = [
			{
				"kobo_field_name": "_submitted_by",
				"target_field": "submitted_byuser",
				"target_child_table": "items",
			},
		]
		parent_map, child_maps = _split_field_mappings(mappings, target_doctype="Farm Purchase Intake")
		self.assertEqual(parent_map, {"_submitted_by": "submitted_byuser"})
		self.assertEqual(child_maps, {})

	def test_get_kobo_repeat_group_from_array(self):
		sub = {
			"crop_procurement/bag": [
				{
					"crop_procurement/bag/barcode": "111",
					"crop_procurement/bag/bag_weight": "2.5",
				},
				{
					"crop_procurement/bag/barcode": "222",
					"crop_procurement/bag/bag_weight": "3.0",
				},
			]
		}
		rows = _get_kobo_repeat_group(sub, "crop_procurement/bag")
		self.assertEqual(len(rows), 2)
		self.assertEqual(rows[0]["crop_procurement/bag/barcode"], "111")

	def test_get_kobo_repeat_group_from_comma_separated(self):
		sub = {"crop_procurement/bag": "111,222,333"}
		field_map = {"barcode": "barcode"}
		rows = _get_kobo_repeat_group(sub, "crop_procurement/bag", field_map)
		self.assertEqual(len(rows), 3)
		self.assertEqual(rows[0]["barcode"], "111")

	def test_get_repeat_row_value(self):
		row = {
			"crop_procurement/bag/barcode": "1970844076211",
			"crop_procurement/bag/Barcode": "1970844076211",
			"crop_procurement/bag/bag_weight": "0.7",
		}
		self.assertEqual(
			_get_repeat_row_value(row, "barcode", "crop_procurement/bag"),
			"1970844076211",
		)
		self.assertEqual(
			_get_repeat_row_value(row, "bag_weight", "crop_procurement/bag"),
			"0.7",
		)

	def test_get_or_create_farmer_creates_stub(self):
		farmer_ref = "TEST-KOBO-FARMER-001"
		if frappe.db.exists("Farmer", farmer_ref):
			frappe.delete_doc("Farmer", farmer_ref, force=1)

		name = _get_or_create_farmer(farmer_ref)
		self.assertEqual(name, farmer_ref)
		self.assertTrue(frappe.db.exists("Farmer", farmer_ref))

		# Second call should reuse existing farmer
		self.assertEqual(_get_or_create_farmer(farmer_ref), farmer_ref)

	# ─── Linked farmer geography ─────────────────────────────────────────────

	def _make_farmer(self, farmer_id):
		"""A stub Farmer, the way the Kobo sync creates one."""
		return frappe.get_doc(
			{"doctype": "Farmer", "farmer_id": farmer_id, "first_name": "Kobo Geo Test"}
		).insert(ignore_permissions=True)

	def _make_purchase_doc(self, farmer, submission_id):
		"""An unsaved Farm Purchase Intake linked to ``farmer``."""
		doc = frappe.new_doc("Farm Purchase Intake")
		doc.kobo_submission_id = submission_id
		doc.farmer = farmer

		return doc

	def test_ensure_geography_seeds_and_reuses_chain(self):
		sub = {
			"crop_procurement/country": "tanzania",
			"crop_procurement/region": "kobogeotest-region",
			"crop_procurement/district": "kobogeotest-district",
			"crop_procurement/group": "kobogeotest-group",
		}
		geo = _ensure_geography(sub)

		self.assertEqual(geo["country"], "Tanzania")
		self.assertEqual(geo["state"], "Kobogeotest-Region")
		self.assertEqual(geo["district"], "Kobogeotest-District")
		for doctype, name in (
			("State", geo["state"]),
			("District", geo["district"]),
			("Village", geo["village"]),
			("Farmer Group", geo["farmer_group"]),
		):
			self.assertTrue(frappe.db.exists(doctype, name), f"{doctype} '{name}' was not seeded")

		# Named exactly like the Kobo choice, not '{group}-{district}'
		self.assertEqual(geo["farmer_group"], "Kobogeotest-Group")
		self.assertEqual(
			frappe.db.get_value("Farmer Group", geo["farmer_group"], "farmer_group_name"),
			"Kobogeotest-Group",
		)

		# A second submission from the same place reuses the seeded masters
		counts = [frappe.db.count(dt) for dt in ("State", "District", "Village", "Farmer Group")]
		self.assertEqual(_ensure_geography(sub), geo)
		self.assertEqual(
			[frappe.db.count(dt) for dt in ("State", "District", "Village", "Farmer Group")], counts
		)

	def test_ensure_geography_does_not_invent_a_village_without_district(self):
		geo = _ensure_geography(
			{
				"crop_procurement/region": "kobogeonodistrict-region",
				"crop_procurement/group": "kobogeonodistrict-group",
			}
		)

		self.assertEqual(geo["state"], "Kobogeonodistrict-Region")
		self.assertIsNone(geo["district"])
		self.assertIsNone(geo["village"])
		self.assertIsNone(geo["farmer_group"])
		self.assertFalse(frappe.db.exists("Farmer Group", "Kobogeonodistrict-Group"))

	def test_post_process_links_linked_farmer_geography(self):
		sub = {
			"crop_procurement/region": "kobogeolink-region",
			"crop_procurement/district": "kobogeolink-district",
			"crop_procurement/group": "kobogeolink-group",
		}
		farmer = self._make_farmer("KOBO-GEO-FARMER-LINK")
		self.assertFalse(farmer.village)

		doc = self._make_purchase_doc(farmer.name, "KOBO-GEO-LINK-1")
		_post_process_farm_purchase_intake_doc(doc, "Farm Purchase Intake", sub)

		linked = frappe.db.get_value(
			"Farmer",
			farmer.name,
			["village", "farmer_group", "district", "state", "country"],
			as_dict=True,
		)
		self.assertTrue(linked.village)
		self.assertEqual(linked.district, "Kobogeolink-District")
		self.assertEqual(linked.state, "Kobogeolink-Region")

		# the purchase mirrors the linked Farmer (state/district/farmer_group are fetch_from)
		self.assertEqual(doc.farmer_group, linked.farmer_group)
		self.assertEqual(doc.district, linked.district)
		self.assertEqual(doc.state, linked.state)

	def test_link_geography_keeps_an_already_registered_farmer(self):
		farmer = self._make_farmer("KOBO-GEO-FARMER-KEEP")
		registered = {
			"crop_procurement/region": "kobogeokeep-region",
			"crop_procurement/district": "kobogeokeep-district",
			"crop_procurement/group": "kobogeokeep-group",
		}
		other = {
			"crop_procurement/region": "kobogeoother-region",
			"crop_procurement/district": "kobogeoother-district",
			"crop_procurement/group": "kobogeoother-group",
		}
		doc = self._make_purchase_doc(farmer.name, "KOBO-GEO-KEEP-1")

		_sync_linked_farmer_geography(doc, registered)
		before = frappe.db.get_value("Farmer", farmer.name, ["village", "farmer_group"], as_dict=True)

		_sync_linked_farmer_geography(doc, other)

		after = frappe.db.get_value("Farmer", farmer.name, ["village", "farmer_group"], as_dict=True)
		self.assertEqual(after, before)

	def test_refresh_linked_farmer_cache_updates_stored_values(self):
		sub = {
			"crop_procurement/region": "kobogeocache-region",
			"crop_procurement/district": "kobogeocache-district",
			"crop_procurement/group": "kobogeocache-group",
		}
		farmer = self._make_farmer("KOBO-GEO-FARMER-CACHE")

		doc = frappe.new_doc("Farm Purchase Intake")
		doc.name = "KOBO-GEO-CACHE-1"
		doc.kobo_submission_id = doc.name
		doc.farmer = farmer.name
		doc.db_insert()

		_sync_linked_farmer_geography(doc, sub)
		frappe.db.set_value(
			doc.doctype,
			doc.name,
			{"state": None, "district": None, "farmer_group": None},
			update_modified=False,
		)

		_refresh_linked_farmer_cache(doc)

		stored = frappe.db.get_value(
			doc.doctype, doc.name, ["state", "district", "farmer_group"], as_dict=True
		)
		self.assertEqual(stored.state, "Kobogeocache-Region")
		self.assertEqual(stored.district, "Kobogeocache-District")
		self.assertEqual(stored.farmer_group, "Kobogeocache-Group")
