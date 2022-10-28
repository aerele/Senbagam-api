import frappe
__version__ = '0.0.1'

def after_install():
	frappe.db.set_value("System Settings", "System Settings", "allow_login_using_mobile_number", 1)
