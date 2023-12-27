### import file ###
from odoo import api,models,fields
from odoo.exceptions import UserError
import time

class AccCountries(models.Model):
	_inherit = "res.country"

	code = fields.Char(
        string='Country Code', size=10,
        help='The ISO country code in two chars. \nYou can use this field for quick search.')

class AccCities(models.Model):
	_inherit = "res.city"

	code = fields.Char("Code")

# class AccState(models.Model):
# 	_inherit = "res.country.state"

	# is_emirates = fields.Boolean("Is ")
	# c_code = fields.Integer('Customer Code')
	# s_code = fields.Integer("Supplier Code")

class AccPartner(models.Model):
	_inherit = "res.partner"
	
	currency_dummy_id = fields.Many2one('res.currency','Currency')

	@api.model
	def create(self, vals):
		if vals['customer_rank'] > 0 and vals['supplier_rank'] == 0:
			vals['partner_no'] = self.env['ir.sequence'].next_by_code('res.customer')
		elif vals['customer_rank'] == 0 and vals['supplier_rank'] > 0:
			vals['partner_no'] = self.env['ir.sequence'].next_by_code('res.supplier')
		else:
			vals['partner_no'] = self.env['ir.sequence'].next_by_code('res.partner')
		return super(AccPartner, self).create(vals)

	def name_get(self):
		res = []
		for field in self:
			if field.partner_no:
				res.append((field.id, '%s - %s' %(field.partner_no,field.name)))
			else:
				res.append((field.id, '%s' %(field.name)))
		return res

	@api.model
	def name_search(self, name, args=None, operator='ilike', limit=100):
		if args is None:
			args = []
		context = self.env.context
		domain = []
		if name:
			domain = ['|','|',('name', operator, name),('partner_no', operator, name),('parent_id',operator,name)]
		recs = self.search(domain + args, limit=limit)
		return recs.name_get()

	# @api.model
	# def _get_customer_type(self):
	# 	params = self.env['ir.config_parameter'].sudo()
	# 	enable_temp_partner = params.get_param('enable_temp_partner')
	# 	if enable_temp_partner:
	# 		return [('trader','Reseller / Trader'),('enduser','Enduser (Direct Sale)'),('temporary','Walk-in Customer')]
	# 	else:
	# 		return [('trader','Reseller / Trader'),('enduser','Enduser (Direct Sale)')]

	# partner_type = fields.Selection([('local','Local (U.A.E)'),('gcc','Local Exports (within GCC)'),('export','Local Exports (outside GCC)'),('overseas','Direct Exports')],string="Sales Type")
	partner_no = fields.Char('No.')
	# customer_type = fields.Selection([('trader','Reseller / Trader'),('enduser','Enduser (Direct Sale)')],string='Customer Type')
	# product_categ_id = fields.Many2one("product.category",'Commodity Code')
	fax = fields.Char("Fax")
	vat_document = fields.Binary("VAT Document")
	# partner_acc_no = fields.Char("Old Acc No")
	vat_document_filename = fields.Char("VAT Document Filename")
	customer_payment_term_id = fields.Many2one('account.payment.term','Customer Payment Term',related='property_payment_term_id',store=True)
	supplier_payment_term_id = fields.Many2one('account.payment.term','Supplier Payment Term',related='property_supplier_payment_term_id',store=True)
	property_payment_due_days = fields.Integer("Payment Due Days")
	# settlement_due_days = fields.Float("Settlement Due Days",digits=(12,1))
	property_supplier_payment_due_days = fields.Integer("Payment Due Days")
	# supplier_settlement_due_days = fields.Float("Settlement Due Days",digits=(12,1))
	# email1 = fields.Char("Email 2")
	# email2 = fields.Char("Email 3")
	attachment_ids = fields.Many2many('ir.attachment','res_partner_attachment_rel','partner_id','attachment_id','Attachments')
	is_temp_partner = fields.Boolean("Walk-in Customer",default=False)
	# direct_sale_margin = fields.Float("Direct Export Sales Margin",digits=(12,2),default=30)
	company_id = fields.Many2one('res.company', 'Company', index=True, default=lambda self:self.env.company.id)
	# duns_no = fields.Char("DUNS No.")
	tax_code = fields.Char("Tax Code")
	pending_credit_invoice_ids = fields.Many2many('account.move','acc_partner_pending_credit_move_rel','move_id','partner_id','On Account Credits',compute='_get_pending_credits')
	total_pending_credit_invoices = fields.Monetary("On Accout Credits Balance",currency_field='currency_id',compute='_get_pending_credits')
	pending_payment_ids = fields.Many2many('account.payment','acc_partner_pending_payment_rel','payment_id','partner_id','On Account Payments',compute='_get_pending_payments')
	total_pending_payments = fields.Monetary("On Accout Payments Balance",currency_field='currency_id',compute='_get_pending_payments')
	pending_credit_invoice_count = fields.Integer("On Account Credits",compute='_get_pending_credit_invoice_count')
	pending_payment_count = fields.Integer("On Account Payments",compute='_get_pending_payment_count')
	user_id = fields.Many2one('res.users', string='Salesperson',help='The internal user in charge of this contact.')
	crt_date = fields.Datetime(
	'Creation Date',
	readonly = True,
	default = lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'))
	# trader_name = fields.Char("Trader Name")

	# @api.depends('customer_type')
	# def _get_temp_partner(self):
	# 	for rec in self:
	# 		if rec.customer_type == 'temporary':
	# 			rec.is_temp_partner = True
	# 		else:
	# 			rec.is_temp_partner = False

	def entry_move_permanent(self):
		for rec in self:
			if not rec.customer_type:
				raise UserError("Warning!!, Select Customer Type before Move to Permanent.")
			if not rec.partner_type:
				raise UserError("Warning!!, Select Sales Type before Move to Permanent.")
			if not rec.country_id:
				raise UserError("Warning!!, Select Country before Move to Permanent.")
			elif rec.country_id and rec.country_id.name == 'United Arab Emirates' and not rec.state_id:
				raise UserError("Warning!!, Select Emirates / States before Move to Permanent.")
			rec.is_temp_partner = False
			rec.partner_no = ''
			self._get_partner_no()

	@api.onchange('currency_dummy_id')
	def update_pricelist(self):
		if self.currency_dummy_id:
			self.property_product_pricelist = self.env['product.pricelist'].search([('currency_id','=',self.currency_dummy_id.id)],limit=1).id or False

	def _get_company_currency(self):
		for partner in self:
			if partner.currency_dummy_id:
				partner.currency_id = partner.currency_dummy_id.id
			elif partner.company_id:
				partner.currency_id = partner.sudo().company_id.currency_id
			else:
				partner.currency_id = self.env.company.currency_id

	@api.constrains('name')
	def partner_duplicate_constrain(self):
		for rec in self:
			if rec.name and rec.company_id:
				name=rec.name.upper()  
				name=name.replace("'", "")
				self.env.cr.execute(""" select upper(name) from res_partner where upper(name)  = '%s' and id != '%s' and company_id = '%s' and is_temp_partner = 'f'""" %(name,rec.id,rec.company_id.id))
				data = self.env.cr.dictfetchall()
				if data:
					raise UserError("Warning!!, You are not able to create multiple record in same Name !! - %s"%(data[0]['upper']))

	def _get_pending_credits(self):
		for rec in self:
			if rec.id:
				move_ids = self.env['account.move'].search([('state','=','posted'),('move_type','in',('out_refund','in_refund')),('partner_id','=',rec.id),
					('payment_state','in',('not_paid','partial','in_payment'))])
				if move_ids:
					rec.pending_credit_invoice_ids = [(6,0,move_ids.mapped('id'))]
					rec.total_pending_credit_invoices = sum([x.amount_residual for x in move_ids])
				else:
					rec.pending_credit_invoice_ids = False
					rec.total_pending_credit_invoices = 0
			else:
				rec.pending_credit_invoice_ids = False
				rec.total_pending_credit_invoices = 0

	@api.depends('pending_credit_invoice_ids')
	def _get_pending_credit_invoice_count(self):
		for rec in self:
			if rec.pending_credit_invoice_ids:
				rec.pending_credit_invoice_count = len(rec.pending_credit_invoice_ids)
			else:
				rec.pending_credit_invoice_count = 0

	def _get_pending_payments(self):
		for rec in self:
			if rec.id:
				move_line_ids = self.env['account.move.line'].search([('full_reconcile_id','=',False),('balance','!=',0),('move_id.move_type','=','entry'),
				('account_id.reconcile','=',True),('partner_id','=',rec.id),('parent_state','=','posted'),('amount_residual_currency','!=',0)])
				if move_line_ids:
					payment_ids = self.env['account.payment'].search([('move_id','in',move_line_ids.move_id.mapped('id'))])
					if payment_ids:
						rec.pending_payment_ids = [(6,0,payment_ids.mapped('id'))]
						rec.total_pending_payments = sum([abs(x.amount_residual_currency) for x in move_line_ids])
					else:
						rec.pending_payment_ids = False
						rec.total_pending_payments = 0
				else:
					rec.pending_payment_ids = False
					rec.total_pending_payments = 0
			else:
				rec.pending_payment_ids = False
				rec.total_pending_payments = 0

	@api.depends('pending_payment_ids')
	def _get_pending_payment_count(self):
		for rec in self:
			if rec.pending_payment_ids:
				rec.pending_payment_count = len(rec.pending_payment_ids)
			else:
				rec.pending_payment_count = 0

	def action_view_pending_credit_invoices(self):
		if self.pending_credit_invoice_ids:
			if len(self.pending_credit_invoice_ids) == 1:
				view = self.env.ref('account.view_move_form')
				return {
					'name': 'On Account Credit Invoices',
					'type': 'ir.actions.act_window',
					'view_mode': 'form',
					'res_model': 'account.move',
					'views': [(view.id, 'form')],
					'view_id': view.id,
					'target': 'current',
					'res_id': self.pending_credit_invoice_ids.id,
				}
			else:
				tree_id = self.env.ref('account.view_in_invoice_tree')
				form_id = self.env.ref('account.view_move_form')
				return {
					'name': 'On Account Credit Invoices',
					'type': 'ir.actions.act_window',
					'view_mode': 'tree',
					'res_model': 'account.move',
					'views': [(tree_id.id, 'tree'),(form_id.id, 'form')],
					'view_id': tree_id.id,
					'target': 'current',
					'domain': [('id','in',self.pending_credit_invoice_ids.ids)],
				}

	def action_view_pending_payments(self):
		if self.pending_payment_ids:
			if len(self.pending_payment_ids) == 1:
				view = self.env.ref('account.view_account_payment_form')
				return {
					'name': 'On Account Credit Invoices',
					'type': 'ir.actions.act_window',
					'view_mode': 'form',
					'res_model': 'account.payment',
					'views': [(view.id, 'form')],
					'view_id': view.id,
					'target': 'current',
					'res_id': self.pending_payment_ids.id,
				}
			else:
				tree_id = self.env.ref('account.view_account_payment_tree')
				form_id = self.env.ref('account.view_account_payment_form')
				return {
					'name': 'On Account Credit Invoices',
					'type': 'ir.actions.act_window',
					'view_mode': 'tree',
					'res_model': 'account.payment',
					'views': [(tree_id.id, 'tree'),(form_id.id, 'form')],
					'view_id': tree_id.id,
					'target': 'current',
					'domain': [('id','in',self.pending_payment_ids.ids)],
				}