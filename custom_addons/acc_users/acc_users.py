### import file ###
from odoo import api,models,fields

class AccUsers(models.Model):
	_inherit = "res.users"

	is_admin = fields.Boolean("Admin User?")
	is_manager = fields.Boolean("Manager User?")
	sign = fields.Binary("Signature")
	is_approver = fields.Boolean("Approver")
	is_warehouse_user = fields.Boolean("Warehouse User")
	is_driver = fields.Boolean("Driver")
	short_name = fields.Char("Short Name",size=10)
	# petty_account_id = fields.Many2one("account.account","User Petty Cash")
	allowed_journal_ids = fields.Many2many("account.journal",'acc_res_users_journal_rel','journal_id','user_id',"Allowed Bank/Cash Journals")
	min_sale_limit = fields.Float("Sale Minimum Limit")