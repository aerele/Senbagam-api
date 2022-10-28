import frappe

def cron_create_quotation():
	qt = frappe.db.sql(""" select distinct name from `tabConnector Quotation` where is_synced=0 and retry_limit > 0 order by creation limit 20""", as_dict=True)
	sync_quotation(qt)

def sync_quotation(quot):
	for i in quot:
		try:
			create_quotation(i.name)
		except:
			pass

@frappe.whitelist()
def create_quotation(name):
	doc = frappe.get_doc("Connector Quotation", name)
	if doc.is_synced:
		frappe.throw("Quotation already created")
	doc.retry_limit -= 1
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	new_doc = frappe.new_doc("Quotation")
	new_doc.company = "Senbagam Paints"
	new_doc.quotation_to = "Customer"
	new_doc.party_name = doc.customer
	new_doc.reference_no = doc.name
	for i in doc.items:
		new_doc.append("items", {
					"item_code":validate_item(i.item_code.strip()),
					"qty":i.qty
					})
	new_doc.save(ignore_permissions = True)
	new_doc.submit()
	doc.status = "Synced"
	doc.is_synced = 1
	doc.save(ignore_permissions=True)

def validate_item(item):
	if not frappe.db.get_value("Item", item):
		frappe.throw("Item: {0} not found".format(item))
	return item




def cron_create_bank_account():
	ba = frappe.db.sql(""" select distinct name from `tabConnector Bank Account` where is_synced=0 and retry_limit > 0 order by creation limit 20""", as_dict=True)
	sync_bank_account(ba)

def sync_bank_account(bank_account):
	for i in bank_account:
		try:
			create_bank_account(i.name)
		except:
			pass

@frappe.whitelist()
def create_bank_account(name):
	doc = frappe.get_doc("Connector Bank Account", name)
	if doc.is_synced:
		frappe.throw("Bank Account already created")
	doc.retry_limit -= 1
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	new_doc = frappe.new_doc("Bank Account")
	new_doc.account_name = doc.account_holder_name
	new_doc.bank = get_bank_name(doc.bank_name)
	new_doc.party_type = "Customer"
	new_doc.party = doc.customer
	new_doc.bank_account_no = doc.account_no
	new_doc.branch_code = doc.ifsc_code
	new_doc.save(ignore_permissions=True)
	doc.status = "Synced"
	doc.is_synced = 1
	doc.save(ignore_permissions=True)



def get_bank_name(name):
	bank_name = frappe.db.get_value("Bank", {"bank_name":name})
	if not bank_name:
		doc = frappe.new_doc("Bank")
		doc.bank_name = name
		doc.save(ignore_permissions=True)
		bank_name = doc.name
	return bank_name
