from odoo import api,models,fields
import time

class AccTempPartner(models.TransientModel):
	_name = "acc.temp.partner"

	name = fields.Char("Name")
	phone = fields.Char("Phone")
	email = fields.Char("Email")
	street = fields.Char("Street")
	street2 = fields.Char("Street 2")
	city_id = fields.Many2one("res.city","City")
	zip = fields.Char("P.O BOX")
	state_id = fields.Many2one("res.country.state",'State')
	country_id = fields.Many2one("res.country",'Country')

	def createandupdate_partner(self):
		customer_id = self.env['res.partner'].create({
					'name':self.name,
					'phone':self.phone,
					'email':self.email,
					'customer_type':'temporary',
					'customer_rank':1,
					'street':self.street,
					'street2':self.street2,
					'city_id':self.city_id.id,
					'zip':self.zip,
					'state_id':self.state_id.id,
					'country_id':self.country_id.id
				})
		if customer_id:
			active_id =  self.env.context.get('active_id')
			active_id.partner_id = customer_id.id