# Copyright (c) 2026, Mania and contributors

"""Read only helpers that feed the Purchase Dashboard workspace.

Every method returns plain lists of dicts so the workspace Custom HTML Blocks can
render them inside a shadow DOM without knowing anything about Frappe internals.
The methods that back a *Custom* Number Card return ``{value, fieldtype, route}``
instead, which is the payload ``frappe.desk.doctype.number_card.number_card``
expects for cards of type ``Custom``.

Quantities are always kilograms: every Farm Purchase Intake is recorded in kg, so
the dashboard never converts units of measure and the labels say ``kg`` directly.
"""

import frappe
from frappe.utils import cint, flt, getdate, nowdate

PURCHASE_DOCTYPE = "Farm Purchase Intake"
TRAINING_DOCTYPE = "Training Status"
FARMER_DOCTYPE = "Farmer"
FARM_DOCTYPE = "Farm"
GROUP_DOCTYPE = "Farmer Group"

# Contract and premium data are optional: Farm Trace ships neither on every site,
# so the dashboard shows an explicit empty state instead of inventing numbers.
CONTRACT_DOCTYPE = "Purchase Contract"
PREMIUM_DOCTYPE = "Premium"

CANCELLED = 2
HECTARES_PATTERN = "^[0-9]+([.][0-9]+)?$"

# hectares is a free text field in Farm, only count the values that look numeric
HECTARES_AS_NUMBER = (
	f"case when fm.hectares regexp '{HECTARES_PATTERN}' then cast(fm.hectares as decimal(12, 2)) else 0 end"
)


def _limit(value, default=20, maximum=200) -> int:
	"""Clamp a user supplied row limit so the query can never be abused."""
	return max(1, min(cint(value) or default, maximum))


def _days(value, default=90, maximum=730) -> int:
	"""Clamp a look back window (in days) to a sane range."""
	return max(1, min(cint(value) or default, maximum))


def _exclude_cancelled() -> str:
	return f"ifnull(docstatus, 0) != {CANCELLED}"


def _number_card(value, fieldtype="Int", route=None, precision=None) -> dict:
	"""Payload expected by a *Custom* Number Card."""
	card = {"value": value, "fieldtype": fieldtype}
	if precision is not None:
		card["precision"] = precision
	if route:
		card["route"] = route
	return card


@frappe.whitelist()
def get_market_status(limit=None):
	"""Market centre (= Farmer Group) status, most recent activity first.

	A purchase is "still open" while no Purchase Receipt has been created for it.
	"""
	rows = frappe.db.sql(
		f"""
		select
			fpi.farmer_group,
			fg.district,
			fg.state,
			max(fpi.purchase_date) as last_purchase_date,
			group_concat(
				distinct nullif(fpi.submitted_byuser, '')
				order by fpi.submitted_byuser separator ', '
			) as officers,
			count(*) as purchases,
			round(sum(ifnull(fpi.total_qty, 0)), 2) as quantity,
			round(sum(ifnull(fpi.total_amount, 0)), 2) as amount,
			sum(case when ifnull(fpi.receipt_created, 0) = 0 then 1 else 0 end) as open_purchases,
			round(sum(case when ifnull(fpi.receipt_created, 0) = 0 then ifnull(fpi.total_qty, 0) else 0 end), 2)
				as open_quantity,
			round(sum(case when ifnull(fpi.receipt_created, 0) = 0 then ifnull(fpi.total_amount, 0) else 0 end), 2)
				as open_amount
		from `tab{PURCHASE_DOCTYPE}` fpi
		left join `tab{GROUP_DOCTYPE}` fg on fg.name = fpi.farmer_group
		where ifnull(fpi.farmer_group, '') != '' and ifnull(fpi.docstatus, 0) != {CANCELLED}
		group by fpi.farmer_group, fg.district, fg.state
		order by open_quantity desc, last_purchase_date desc
		limit {_limit(limit, 25)}
		""",
		as_dict=True,
	)

	summary = {
		"markets": len(rows),
		"open_markets": sum(1 for row in rows if cint(row.open_purchases)),
		"purchases": sum(cint(row.purchases) for row in rows),
		"open_purchases": sum(cint(row.open_purchases) for row in rows),
		"quantity": flt(sum(flt(row.quantity) for row in rows), 2),
		"open_quantity": flt(sum(flt(row.open_quantity) for row in rows), 2),
		"open_amount": flt(sum(flt(row.open_amount) for row in rows), 2),
	}

	return {"summary": summary, "rows": rows}


@frappe.whitelist()
def get_officer_activity(limit=None):
	"""Purchases per field officer (the Kobo submission user)."""
	rows = frappe.db.sql(
		f"""
		select
			ifnull(nullif(submitted_byuser, ''), 'Unassigned') as officer,
			count(*) as purchases,
			round(sum(ifnull(total_qty, 0)), 2) as quantity,
			count(distinct farmer) as farmers,
			count(distinct farmer_group) as markets,
			sum(case when ifnull(receipt_created, 0) = 1 then 1 else 0 end) as receipts,
			max(purchase_date) as last_purchase_date
		from `tab{PURCHASE_DOCTYPE}`
		where {_exclude_cancelled()}
		group by officer
		order by quantity desc, purchases desc
		limit {_limit(limit, 25)}
		""",
		as_dict=True,
	)

	summary = {
		"officers": len(rows),
		"purchases": sum(cint(row.purchases) for row in rows),
		"quantity": flt(sum(flt(row.quantity) for row in rows), 2),
		"receipts": sum(cint(row.receipts) for row in rows),
	}

	return {"summary": summary, "rows": rows}


@frappe.whitelist()
def get_farmer_group_summary(limit=None):
	"""Farmers, farms, declared hectares and purchases per farmer group."""
	rows = frappe.db.sql(
		f"""
		select
			fg.name as farmer_group,
			fg.farmer_group_name,
			fg.state,
			fg.district,
			(
				select count(*) from `tabFarmer` f where f.farmer_group = fg.name
			) as farmers,
			(
				select count(*)
				from `tabFarm` fm
				inner join `tabFarmer` f on f.name = fm.farmer
				where f.farmer_group = fg.name
			) as farms,
			(
				select round(sum({HECTARES_AS_NUMBER}), 2)
				from `tabFarm` fm
				inner join `tabFarmer` f on f.name = fm.farmer
				where f.farmer_group = fg.name
			) as hectares,
			(
				select count(*) from `tab{PURCHASE_DOCTYPE}` fpi
				where fpi.farmer_group = fg.name and ifnull(fpi.docstatus, 0) != {CANCELLED}
			) as purchases,
			(
				select round(sum(ifnull(fpi.total_qty, 0)), 2) from `tab{PURCHASE_DOCTYPE}` fpi
				where fpi.farmer_group = fg.name and ifnull(fpi.docstatus, 0) != {CANCELLED}
			) as quantity,
			(
				select max(fpi.purchase_date) from `tab{PURCHASE_DOCTYPE}` fpi
				where fpi.farmer_group = fg.name and ifnull(fpi.docstatus, 0) != {CANCELLED}
			) as last_purchase_date
		from `tabFarmer Group` fg
		order by quantity desc, farmer_group asc
		limit {_limit(limit, 50)}
		""",
		as_dict=True,
	)

	summary = {
		"groups": len(rows),
		"farmers": sum(cint(row.farmers) for row in rows),
		"farms": sum(cint(row.farms) for row in rows),
		"hectares": flt(sum(flt(row.hectares) for row in rows), 2),
		"purchases": sum(cint(row.purchases) for row in rows),
		"quantity": flt(sum(flt(row.quantity) for row in rows), 2),
	}

	return {"summary": summary, "rows": rows}


@frappe.whitelist()
def get_latest_purchases(limit=None):
	"""Most recent Farm Purchase Intake rows with a human readable status."""
	rows = frappe.db.sql(
		f"""
		select
			name,
			purchase_date,
			farmer,
			farmer_name,
			farmer_group,
			season,
			submitted_byuser,
			docstatus,
			ifnull(receipt_created, 0) as receipt_created,
			round(ifnull(total_qty, 0), 2) as quantity,
			round(ifnull(total_amount, 0), 2) as amount
		from `tab{PURCHASE_DOCTYPE}`
		where {_exclude_cancelled()}
		order by purchase_date desc, modified desc
		limit {_limit(limit, 12)}
		""",
		as_dict=True,
	)

	for row in rows:
		row["status"] = _status(row.docstatus, row.receipt_created)

	return {"rows": rows}


def _status(docstatus, receipt_created) -> str:
	if cint(receipt_created):
		return "Closed"
	if cint(docstatus) == CANCELLED:
		return "Cancelled"
	if cint(docstatus) == 1:
		return "Submitted"
	return "Draft"


@frappe.whitelist()
def get_hectares(filters=None):
	"""Total declared hectares, for the *Hectares* custom number card.

	``Farm.hectares`` is free text, so only values that parse as a number are
	counted (``"2.5"`` counts, ``"about 2 acres"`` does not).
	"""
	measured_farms, total = frappe.db.sql(
		f"""
		select
			sum(case when fm.hectares regexp '{HECTARES_PATTERN}' then 1 else 0 end),
			round(sum({HECTARES_AS_NUMBER}), 2)
		from `tab{FARM_DOCTYPE}` fm
		"""
	)[0]

	return _number_card(
		flt(total, 2),
		fieldtype="Float",
		precision=2,
		route=["List", FARM_DOCTYPE, {"hectares": ["is", "set"] if measured_farms else ["is", "not set"]}],
	)


@frappe.whitelist()
def get_open_markets(filters=None):
	"""Farmer groups (= market centres) with at least one purchase awaiting a receipt."""
	count = frappe.db.sql(
		f"""
		select count(distinct farmer_group)
		from `tab{PURCHASE_DOCTYPE}`
		where ifnull(farmer_group, '') != ''
			and ifnull(receipt_created, 0) = 0
			and {_exclude_cancelled()}
		"""
	)

	return _number_card(cint(count[0][0] if count else 0), route=["List", GROUP_DOCTYPE])


@frappe.whitelist()
def get_field_activity(days=None, limit=None):
	"""Training / field activity for the last ``days`` days (default 90)."""
	days = _days(days)
	rows = frappe.db.sql(
		f"""
		select
			ts.name,
			ts.training_code,
			ts.training_date,
			ts.farmer_training,
			ts.farmer_id,
			ts.name_of_trainer,
			ts.village,
			ifnull(ts.farmer_attended, 0) as attended,
			ifnull(ts.farmer_champion, 0) as champion
		from `tab{TRAINING_DOCTYPE}` ts
		where ts.training_date >= date_sub(curdate(), interval {days} day)
		order by ts.training_date desc
		limit {_limit(limit, 8)}
		""",
		as_dict=True,
	)

	metrics = frappe.db.sql(
		f"""
		select
			count(*) as sessions,
			count(distinct ts.farmer_id) as farmers_reached,
			sum(case when ifnull(ts.farmer_attended, 0) = 1 then 1 else 0 end) as attendances,
			count(distinct case when ifnull(ts.farmer_champion, 0) = 1 then ts.farmer_id end) as champions
		from `tab{TRAINING_DOCTYPE}` ts
		where ts.training_date >= date_sub(curdate(), interval {days} day)
		""",
		as_dict=True,
	)[0]

	new_farmers = cint(
		frappe.db.sql(
			f"select count(*) from `tab{FARMER_DOCTYPE}` where creation >= date_sub(curdate(), interval 30 day)"
		)[0][0]
	)
	farms_verified = cint(
		frappe.db.sql(
			f"""
			select count(*) from `tab{FARM_DOCTYPE}`
			where ifnull(is_verified, 0) = 1
				and ifnull(verified_date, creation) >= date_sub(curdate(), interval {days} day)
			"""
		)[0][0]
	)

	summary = {
		"days": days,
		"sessions": cint(metrics.sessions),
		"farmers_reached": cint(metrics.farmers_reached),
		"attendances": cint(metrics.attendances),
		"champions": cint(metrics.champions),
		"new_farmers_30_days": new_farmers,
		"farms_verified": farms_verified,
	}

	for row in rows:
		row["attended"] = cint(row.attended)
		row["champion"] = cint(row.champion)

	return {"summary": summary, "rows": rows}


@frappe.whitelist()
def get_compliance_summary(limit=None):
	"""Farms enrolled per certification standard (``Farm.certification``)."""
	rows = frappe.db.sql(
		f"""
		select
			fm.certification as standard,
			count(*) as farms,
			sum(case when ifnull(fm.is_verified, 0) = 1 then 1 else 0 end) as verified,
			round(sum({HECTARES_AS_NUMBER}), 2) as hectares
		from `tab{FARM_DOCTYPE}` fm
		where ifnull(fm.certification, '') != ''
		group by fm.certification
		order by farms desc
		limit {_limit(limit, 17)}
		""",
		as_dict=True,
	)

	summary = {
		"standards": len(rows),
		"farms": sum(cint(row.farms) for row in rows),
		"verified": sum(cint(row.verified) for row in rows),
		"hectares": flt(sum(flt(row.hectares) for row in rows), 2),
	}
	summary["available"] = bool(rows)

	return {"summary": summary, "rows": rows}


@frappe.whitelist()
def get_premium_summary(limit=None):
	"""Premium due to farmers.

	Farm Trace does not ship a premium master, so unless this site defines a
	``Premium`` doctype the block reports that nothing is tracked yet.
	"""
	if not frappe.db.exists("DocType", PREMIUM_DOCTYPE):
		return {
			"available": False,
			"reason": "No premium has fallen due yet - this site has no Premium records.",
			"summary": {"due_now": 0, "overpaid": 0, "farmers": 0, "records": 0},
			"rows": [],
		}

	records = frappe.get_all(
		PREMIUM_DOCTYPE,
		fields=["name"],
		limit_page_length=_limit(limit, 10),
		order_by="modified desc",
	)
	rows = [{"name": record.name} for record in records]

	return {
		"available": bool(rows),
		"summary": {"due_now": 0, "overpaid": 0, "farmers": 0, "records": len(rows)},
		"rows": rows,
	}


@frappe.whitelist()
def get_contract_status(limit=None):
	"""Contract volumes against what has actually been bought.

	Farm Trace has no contract master, so the block shows an empty state until a
	``Purchase Contract`` doctype exists on the site. When one is added, the
	block expects the fields ``buyer``, ``season`` and ``contract_qty`` on it.
	"""
	if not frappe.db.exists("DocType", CONTRACT_DOCTYPE):
		return {
			"available": False,
			"reason": ("No contracts recorded yet - contract tracking needs a Purchase Contract doctype."),
			"summary": {
				"contracts": 0,
				"contract_quantity": 0,
				"bought_quantity": 0,
				"left_to_buy": 0,
				"fulfilment": 0,
			},
			"rows": [],
		}

	rows = frappe.db.sql(
		f"""
		select
			pc.name as contract,
			pc.buyer,
			pc.season,
			round(ifnull(pc.contract_qty, 0), 2) as contract_quantity,
			round(ifnull(bought.quantity, 0), 2) as bought_quantity
		from `tab{CONTRACT_DOCTYPE}` pc
		left join (
			select season, round(sum(ifnull(total_qty, 0)), 2) as quantity
			from `tab{PURCHASE_DOCTYPE}`
			where {_exclude_cancelled()}
			group by season
		) bought on bought.season = pc.season
		order by pc.name
		limit {_limit(limit, 25)}
		""",
		as_dict=True,
	)

	for row in rows:
		row["left_to_buy"] = flt(flt(row.contract_quantity) - flt(row.bought_quantity), 2)
		row["fulfilment"] = (
			flt(flt(row.bought_quantity) / flt(row.contract_quantity) * 100, 2)
			if flt(row.contract_quantity)
			else 0
		)

	summary = {
		"contracts": len(rows),
		"contract_quantity": flt(sum(flt(row.contract_quantity) for row in rows), 2),
		"bought_quantity": flt(sum(flt(row.bought_quantity) for row in rows), 2),
		"left_to_buy": flt(sum(flt(row.left_to_buy) for row in rows), 2),
	}
	summary["fulfilment"] = (
		flt(summary["bought_quantity"] / summary["contract_quantity"] * 100, 2)
		if summary["contract_quantity"]
		else 0
	)
	summary["available"] = bool(rows)

	return {"summary": summary, "rows": rows}
