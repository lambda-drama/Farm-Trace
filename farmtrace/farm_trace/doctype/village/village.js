// Copyright (c) 2026, Mania and contributors
// For license information, please see license.txt

frappe.ui.form.on("Village", {
	refresh(frm) {
		// Auto-fetch district, state, and country when ward is selected
		if (frm.doc.ward) {
			frm.trigger("ward");
		}
	},

	ward(frm) {
		if (frm.doc.ward) {
			frappe.db.get_doc("Ward", frm.doc.ward).then((doc) => {
				if (doc.district) {
					frm.set_value("district", doc.district);
				}
				if (doc.state) {
					frm.set_value("state", doc.state);
				}
				if (doc.country) {
					frm.set_value("country", doc.country);
				}
			});
		} else {
			frm.set_value("district", "");
			frm.set_value("state", "");
			frm.set_value("country", "");
		}
	},
});
