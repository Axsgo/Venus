### import file ###
from odoo import api,models,fields

class AccPartnerSettings(models.TransientModel):
	_inherit = "res.config.settings"

	group_temp_partner = fields.Boolean("Enable Temporary Customer",implied_group='acc_users.group_temp_partner')
	enable_temp_partner = fields.Boolean("Enable Temp Customer")

	@api.onchange('group_temp_partner')
	def update_temp_partner(self):
		if self.group_temp_partner:
			self.enable_temp_partner = True
		else:
			self.enable_temp_partner = False

	@api.model
	def get_values(self):
		res = super(AccPartnerSettings, self).get_values()
		params = self.env['ir.config_parameter'].sudo()
		enable_temp_partner = params.get_param('enable_temp_partner',default=False)
		res.update(enable_temp_partner=enable_temp_partner)
		return res

	def set_values(self):
		super(AccPartnerSettings, self).set_values()
		self.env['ir.config_parameter'].sudo().set_param("enable_temp_partner",self.enable_temp_partner)