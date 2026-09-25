import frappe

PURCHASE_DOCTYPE = "Farm Purchase Intake"
FARMER_FIELDS = ("farmer_group", "gender", "state", "district")


def execute():
	"""Backfill the reporting fields on existing Farm Purchase Intake records.

	``farmer_group``, ``gender``, ``state`` and ``district`` are ``fetch_from``
	fields on ``farmer``, so they are only populated for records created or
	saved after the fields were added. Here we copy them over on the existing
	records so the Purchase Dashboard charts have historical data.
	"""
	records = frappe.db.sql(
		"""
		SELECT fpi.name AS intake,
			f.farmer_group, f.gender, f.state, f.district
		FROM `tabFarm Purchase Intake` fpi
		INNER JOIN `tabFarmer` f ON f.name = fpi.farmer
		WHERE IFNULL(fpi.farmer, '') != ''
		""",
		as_dict=True,
	)

	for record in records:
		values = {field: record.get(field) for field in FARMER_FIELDS}
		if not any(values.values()):
			continue

		frappe.db.set_value(PURCHASE_DOCTYPE, record.intake, values, update_modified=False)

	frappe.db.commit()
