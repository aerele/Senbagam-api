import frappe
from datetime import date, datetime
from json import loads
from frappe.core.doctype.user.user import generate_keys


@frappe.whitelist( allow_guest=True )
def add_image():
	return frappe.request.data

@frappe.whitelist( allow_guest=True )
def login(args):
	try:
		login_manager = frappe.auth.LoginManager()
		login_manager.authenticate(user=args["username"], pwd=args["password"])
		login_manager.post_login()
	except frappe.exceptions.AuthenticationError:
		frappe.clear_messages()
		frappe.local.response["message"] = {
			"key":0,
			"message":"Incorrect Username or Password"
		}
		return
	api_generate = generate_keys(frappe.session.user)
	frappe.db.commit()
	user = frappe.get_doc('User', frappe.session.user)
	cust = frappe.db.get_value("Customer", {"user": user.name}, "name")
	customer = frappe.get_doc("Customer", cust)
	address = frappe.get_doc("Address", customer.customer_primary_address)
	frappe.response["message"] = {
		"key":1,
		"message":"Success",
		#"sid":frappe.session.sid,
		"api_key":user.api_key,
		"api_secret":api_generate["api_secret"],
		"name":user.full_name,
		"dob":user.birth_date,
		"mobile_no":user.mobile_no,
		"email":user.email,
		"address": address.address_line1 or "",
		"city":address.city or "",
		"district": address.district or "",
		"refered_by":customer.refered_by or "",
		"gstin":customer.gstin or "",
		"pincode":address.pincode or "",
		"roles": [i[0] for i in frappe.db.sql("""SELECT DISTINCT a.role FROM `tabHas Role` as a inner join `tabUser` as b on a.parent = b.name  WHERE a.parent = '{0}'""".format(user.name),as_list=1)],
		"welcome": welcome()["content"],
		"store": store()["content"]
	}

@frappe.whitelist()
def logout():
	api_key = frappe.request.headers.get('Authorization').split(' ')[1].split(':')[0]
	user = frappe.db.get_value("User", {"api_key": api_key})

	login_manager = frappe.auth.LoginManager()
	login_manager.logout(user = user)
	generate_keys(user)
	return {"message": "Successfully Logged Out"}

@frappe.whitelist(allow_guest=True)
def send_otp(args):
	mobile_no = args["mobile_no"]
	message = "Not Success"
	if frappe.db.get_value("User", {"mobile_no": mobile_no}):
		message = "Success"
	return {
		"message": message
		}

@frappe.whitelist(allow_guest=True)
def reset_password(args):
	otp = args["otp"]
	new_password = args["new_password"]
	return {
		"message": "Success"
		}


@frappe.whitelist()
def add_referral(args):
	api_key = frappe.request.headers.get('Authorization').split(' ')[1].split(':')[0]
	name = args["name"]
	mobile_no = args["mobile_no"]
	doc = frappe.new_doc("Referral")
	doc.refered_by = frappe.db.get_value("User", {"api_key": api_key})
	doc.person_name = name
	doc.person_mobile = mobile_no
	doc.save(ignore_permissions=True)
	msg = "Hey! Get your discount on every order by installing the app"
	system_msg = frappe.db.get_value("App Settings", "App Settings", "share_message")
	if system_msg:
		msg = system_msg
	return{
		"message": "Success",
		"share": msg
	}


@frappe.whitelist(allow_guest=True)
def get_referrals(args):
	mobile_no = args["mobile_no"]
	referred_by = frappe.db.sql(""" select CONCAT(c.customer_name, '-', u.mobile_no)  from `tabCustomer` as c join `tabReferral` as r on c.user=r.refered_by join `tabUser` as u on c.user=u.name where r.person_mobile='{0}' """.format(mobile_no), as_list=1)
	referred_by = [i[0] for i in referred_by] or ["Senbagam Paints"]
	return {
		"message": "Success",
		"refered_by": referred_by,
		"length": len(referred_by),
		}

@frappe.whitelist(allow_guest=True)
def signup(args):
	data = {"message":""}
	if not args["name"]:
		data["message"] = "Name cannot be null"
		return data

	if not args["mobile_no"]:
		data["message"] = "Mobile No cannot be null"
		return data

	if not args["email"]:
		data["message"] = "Email cannot be null"
		return data

	if not args["password"]:
		data["message"] = "Password cannot be null"
		return data

	if frappe.db.get_value("User", args["email"]):
		data["message"] = "Email Id Already Exists"
		return data

	if frappe.db.get_value("User", {"mobile_no": args["mobile_no"]}):
		data["message"] = "Mobile No Already Exists"
		return data

	user = frappe.new_doc("User")
	user.email = args["email"]
	user.first_name = args["name"]
	user.send_welcome_email = 0
	user.user_type = 'System User'
	user.mobile_no = args["mobile_no"]
	if args["dob"]:
		user.birth_date = args["dob"]
	user.save(ignore_permissions=True)
	user.new_password = args["password"]
	user.save(ignore_permissions = True)
	user.add_roles('System Manager')

	customer = frappe.new_doc("Customer")
	customer.customer_name = args["name"]
	customer.customer_type = "Individual"
	customer.customer_group = "Individual"
	customer.territory = "India"
	if args["gstin"]:
		customer.gstin = args["gstin"]
	if args["refered_by"]:
		customer.refered_by = args["refered_by"]
	customer.user = user.name
	customer.save(ignore_permissions = True)

	address = frappe.new_doc("Address")
	address.address_title = args["name"]
	address.address_line1 = args["address"]
	address.city = args["city"]
	address.district = args["district"]
	address.pincode = args["pincode"]
	address.append('links', {
				"link_doctype": "Customer",
				"link_name": customer.name
				})
	address.save(ignore_permissions = True)

	customer.customer_primary_address = address.name
	customer.save(ignore_permissions = True)

	ref = frappe.new_doc("Referral Tree")
	ref.customer = customer.name
	ref.is_group = 1
	ref_no = args["refered_by"] if args["refered_by"] == "Senbagam Paints" else None
	if not ref_no:
		mob_no = args["refered_by"].split("-")[1]
		usr = frappe.db.get_value("User", {"mobile_no":mob_no})
		ref_no = frappe.db.get_value("Customer", {"user": usr})
	ref.parent_referral_tree = ref_no
	ref.save(ignore_permissions=True)
	data["message"] = "Account Created, Please Login"
	return data


@frappe.whitelist()
def welcome():
	data = {}
	today= date.today()
	raw = frappe.db.sql("select concat('http://', '{1}', image) as image, content, description from `tabWelcome` where is_active=1 and from_date <= '{0}' and to_date >= '{0}'".format(today, frappe.local.request.host), as_dict=True)
	data["message"] = "Success"
	data["content"] = raw
	return data


@frappe.whitelist()
def store():
        data = {}
        raw = frappe.db.sql("select concat('http://', '{0}', image) as image, address, description from `tabStore` where is_active=1 ".format(frappe.local.request.host), as_dict=True)
        data["message"] = "Success"
        data["content"] = raw
        return data


@frappe.whitelist()
def add_quotation(args):
#	args = loads(args)
	now = datetime.now()
	current_time = now.strftime("%H:%M:%S")

	api_key = frappe.request.headers.get('Authorization').split(' ')[1].split(':')[0]
	user = frappe.db.get_value("User", {"api_key": api_key})
	customer = frappe.db.get_value("Customer", {"user": user})
	doc = frappe.new_doc("Connector Quotation")
	doc.customer = customer
	doc.date = date.today()
	doc.time = current_time
	doc.status = "Pending"
	doc.is_synced = 0
	doc.retry_limit = 3
	for i in args:
		doc.append("items", {
					"item_code": i.strip(),
					"qty": args[i]
					})
	doc.save(ignore_permissions=True)
	return {"message": "Quotation Request Added", "args":args}


@frappe.whitelist()
def get_wallet():
	data = {}
	data["balance"] = 0.0

	api_key = frappe.request.headers.get('Authorization').split(' ')[1].split(':')[0]
	user = frappe.db.get_value("User", {"api_key": api_key})
	customer = frappe.db.get_value("Customer", {"user": user})

	si = frappe.db.sql(""" select name, posting_date as date, CAST(rounded_total as varchar(10)) as amount, CAST(rounded_total * 5 /100 as varchar(10)) as saving  from `tabSales Invoice` where docstatus=1 and customer='{0}' order by creation desc""".format(customer), as_dict=True)
	qt = []
	for i in frappe.db.sql(""" select name from `tabQuotation` where docstatus=1 and party_name='{0}' order by creation desc""".format(customer), as_dict=True):
		doc = frappe.get_doc("Quotation", i.name)
		qt.append({
			"date": doc.transaction_date,
			"name": i.name,
			"amount": str(doc.rounded_total),
			"item": ", ".join([j.item_code for j in doc.items])
				})

	ledger = [
		{
			"date": "YYYY-MM-DD",
			"voucher_no":"Voucher 1",
			"amount": "150",
			"amount_earned": "15",
			"credited_amount": "7",
			"balance": "8"
		},
		{
			"date": "YYYY-MM-DD",
			"voucher_no":"Voucher 2",
			"amount": "300",
			"amount_earned": "30",
			"credited_amount": "20",
			"balance": "10"
		},
		{
			"date": "YYYY-MM-DD",
			"voucher_no": "Voucher 3",
			"amount": "1000",
			"amount_earned": "50",
			"credited_amount": "0",
			"balance": "50"
		},
		{
			"date": "YYYY-MM-DD",
			"voucher_no": "Voucher 4",
			"amount": "5000",
			"amount_earned": "250",
			"credited_amount": "50",
			"balance": "200"
		}
	]

	data["sales_invoice"] = si
	data["quotation"] = qt
	data["ledger"] = ledger
	data["message"] = "Success"
	return data

@frappe.whitelist()
def get_referral_tree():
	api_key = frappe.request.headers.get('Authorization').split(' ')[1].split(':')[0]
	user = frappe.db.get_value("User", {"api_key": api_key})
	customer = frappe.db.get_value("Customer", {"user": user})
#	customer = "Senbagam Paints"
	tree = get_tree(customer, 1)
	return tree

def get_tree(customer, level):
	if not level <= 2:
		return []
	data = [i.name for i in frappe.db.get_list("Referral Tree", {"parent_referral_tree": customer})]
	ret = {}
	ch = {}
	if level == 1:
		ret["parent"] = [customer]
	ret[customer] = data
	for i in data:
		if i and level != 2:
			ch[i] = get_tree(i, level+1)
			ret = {**ret, **ch[i]}

	return ret

@frappe.whitelist()
def add_bank(args):
	api_key = frappe.request.headers.get('Authorization').split(' ')[1].split(':')[0]
	user = frappe.db.get_value("User", {"api_key": api_key})
	customer = frappe.db.get_value("Customer", {"user": user})

	doc = frappe.new_doc("Connector Bank Account")
	doc.bank_name = args["bank_name"]
	doc.account_holder_name = args["account_holder_name"]
	doc.account_no = args["account_no"]
	doc.ifsc_code = args["ifsc_code"]
	doc.customer = customer
	doc.status = "Pending"
	doc.retry_limit = 3
	doc.is_synced = 0
	doc.save(ignore_permissions=True)
	return {"message": "Success"}

@frappe.whitelist()
def get_bank_details():
	api_key = frappe.request.headers.get('Authorization').split(' ')[1].split(':')[0]
	user = frappe.db.get_value("User", {"api_key": api_key})
	customer = frappe.db.get_value("Customer", {"user": user})
	data = frappe.db.sql(""" select bank, account_name as account_holder_name, bank_account_no as account_no, branch_code as ifsc_code from `tabBank Account` where party='{0}' """.format(customer), as_dict=True)
	return {"message": "Success", "data":data}


def get_customer(api_key):
	user = frappe.db.get_value("User", {"api_key": api_key})
	customer = frappe.db.get_value("Customer", {"user": user})
	return customer

@frappe.whitelist()
def add_feedback(args):
	api_key = frappe.request.headers.get('Authorization').split(' ')[1].split(':')[0]
	customer = get_customer(api_key)

	doc= frappe.new_doc("Customer Feedback")
	doc.customer = customer
	doc.feedback = args["feedback"]
	doc.save(ignore_permissions = True)
	return {"message": "Feedback Added Successfully"}

@frappe.whitelist()
def add_qr(args):
	api_key = frappe.request.headers.get('Authorization').split(' ')[1].split(':')[0]
	customer = get_customer(api_key)

	doc= frappe.new_doc("Scanned QR")
	doc.customer = customer
	doc.qr_code = args["qr_code"]
	doc.save(ignore_permissions = True)
	return {"message": "Reward Claimed"}

@frappe.whitelist()
def get_item():
	data = frappe.db.sql(""" select name as section_name, description from `tabProduct Type` """, as_dict=True)
	items = []
	for i in range(len(data)):
		item = frappe.db.sql(""" select it.name as item_code, it.item_name as item_name, it.image as image, it.show_price as show_price, IFNULL(ip.price_list_rate, 0) as price, false as selected from `tabItem` as it left join `tabItem Price` as ip on it.name=ip.item_code where it.disabled=0 and it.product_type=%s """, (data[i].section_name), as_dict=1)
		items.append(item)
	return {"section": data, "items":items}

@frappe.whitelist()
def update_profile(args):
	api_key = frappe.request.headers.get('Authorization').split(' ')[1].split(':')[0]
	user = frappe.db.get_value("User", {"api_key": api_key})

	user = frappe.get_doc("User", user)
	if user.first_name != args["name"]:
		user.first_name = args["name"]
	if user.birth_date != args["dob"]:
		user.birth_date = args["dob"]
	if user.mobile_no != args["mobile_no"]:
		user.mobile_no = args["mobile_no"]
	user.save(ignore_permissions=True)

	customer = frappe.db.get_value("Customer", {"user": user.name})
	customer = frappe.get_doc("Customer", customer)
	if customer.customer_name != args["name"]:
		customer.customer_name = args["name"]
	if customer.gstin != args["gstin"]:
		customer.gstin = args["gstin"]
	customer.save(ignore_permissions=True)

	address = frappe.get_doc("Address", customer.customer_primary_address)
	if address.address_line1 != args["address"]:
		address.address_line1 = args["address"]
	if address.city != args["city"]:
		address.city = args["city"]
	if address.district != args["district"]:
		address.district = args["district"]
	if address.pincode != args["pincode"]:
		address.pincode = args["pincode"]
	address.save(ignore_permissions=True)
	return {"message": "Profile Updated!"}


@frappe.whitelist()
def get_profile():
	api_key = frappe.request.headers.get('Authorization').split(' ')[1].split(':')[0]
	user = frappe.db.get_value("User", {"api_key": api_key})
	user = frappe.get_doc("User", user)
	cust = frappe.db.get_value("Customer", {"user": user.name}, "name")
	customer = frappe.get_doc("Customer", cust)
	address = frappe.get_doc("Address", customer.customer_primary_address)
	frappe.response["message"] = {
		"message":"Success",
		"name":user.full_name,
		"dob":user.birth_date,
		"mobile_no":user.mobile_no,
		"email":user.email,
		"address": address.address_line1 or "",
		"city":address.city or "",
		"district": address.district or "",
		"refered_by":customer.refered_by or "",
		"gstin":customer.gstin or "",
		"pincode":address.pincode or "",
		"roles": [i[0] for i in frappe.db.sql("""SELECT DISTINCT a.role FROM `tabHas Role` as a inner join `tabUser` as b on a.parent = b.name  WHERE a.parent = '{0}'""".format(user.name),as_list=1)]
	}


@frappe.whitelist()
def get_about():
	return {"company":frappe.db.get_value("App Settings", "App Settings", "company_name"), "about": frappe.db.get_value("App Settings", "App Settings", "about_us")}
