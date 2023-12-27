from odoo import models,fields
from odoo.exceptions import UserError

class AccCompany(models.Model):
	_inherit = "res.company"

	erp_email = fields.Char("ERP Email")
	war_street = fields.Char("Street")
	war_street2 = fields.Char("Street 2")
	war_city = fields.Char("City")
	war_state_id = fields.Many2one('res.country.state','State')
	war_zip = fields.Char("Zipcode")
	war_country_id = fields.Many2one('res.country','Country')
	war_phone = fields.Char("Warehouse Phone")
	war_email = fields.Char("Warehouse Email")
	company_seal = fields.Binary("Company Seal")
	brand_footer = fields.Binary("Brand Footer")
	fax = fields.Char("Fax")

	def name_get(self):
		res = []
		for field in self:
			if field.state_id:
				res.append((field.id, '%s - %s' %(field.name,field.state_id.name)))
			else:
				res.append((field.id, '%s' %(field.name)))
		return res

class AccManualCurrencyUpdate(models.TransientModel):
	_name = "acc.currency.update.wizard"
	_description = "Currency Update Wizard"

	type = fields.Selection([('create','Create'),('update','Update')],string='Type',default='create')
	date = fields.Date("Date",default=fields.Date.today)
	rate = fields.Float("Rate",digits=(12,6))
	currency_id = fields.Many2one("res.currency","Currency")
	company_id = fields.Many2one("res.company",default=lambda self:self.env.company.id)

	def entry_update(self):
		if self.date and self.currency_id:
			if self.rate > 0:
				rate_id = self.env['res.currency.rate'].search([('currency_id','=',self.currency_id.id),('company_id','=',self.company_id.id),
					('name','=',self.date)],order='id desc',limit=1)
				if self.type == 'create':
					if rate_id:
						raise UserError("Warning!!, Already exchange rate was created for this date (%s)\n" 
							"so, if you need to change the exchange rate kindly select Type as Update."%(rate_id.rate))
					else:
						self.env['res.currency.rate'].create({
							'name':self.date,
							'currency_id':self.currency_id.id,
							'rate':self.rate,
							'company_id':self.company_id.id,
						})
						return {
							'type': 'ir.actions.client',
							'tag': 'display_notification',
							'params': {
								'title': ('Success'),
								'type':'success',
								'message': 'New Exchange Rate Created for %s - %s - %s'%(self.currency_id.name,self.date,self.rate),
								'sticky': False,
								"next": {"type": "ir.actions.act_window_close"},
							}
						}
				else:
					if rate_id:
						rate_id.rate = self.rate
						return {
							'type': 'ir.actions.client',
							'tag': 'display_notification',
							'params': {
								'title': ('Success'),
								'type':'success',
								'message': 'Exchange Rate updated for %s - %s -%s'%(self.currency_id.name,self.date,self.rate),
								'sticky': False,
								"next": {"type": "ir.actions.act_window_close"},
							}
						}
					else:
						raise UserError("Warning!!, Exchange Rate not found for this date, kindly select Create to create new entry.")
			else:
				raise UserError("Warning!!, Rate should be greater than 0.")