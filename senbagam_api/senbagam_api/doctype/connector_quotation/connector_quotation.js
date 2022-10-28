// Copyright (c) 2022, Aerele Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('Connector Quotation', {
	refresh: function(frm) {
		frm.add_custom_button(__("Create Quotation"), function(){
			frappe.call({
				method: "senbagam_api.cron.create_quotation",
				args:{
					"name": frm.doc.name
				}
			})
		})
	}
});
