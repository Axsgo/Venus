from odoo import models,fields,api

class AccBankAccount(models.Model):
	_inherit = "res.partner.bank"

	is_company_account = fields.Boolean("Is Company Account?")
	branch = fields.Char("Branch")
	iban_no = fields.Char("IBAN No")
	swift_code = fields.Char("Swift Code")

	def name_get(self):
		res = []
		for field in self:
			if field.bank_id and field.currency_id:
				res.append((field.id, '%s(%s) - %s' %(field.bank_id.name,field.currency_id.name,field.acc_number)))
			elif field.bank_id:
				res.append((field.id, '%s - %s' %(field.bank_id.name,field.acc_number)))
			else:
				res.append((field.id, '%s' %(field.acc_number)))
		return res

	@api.model
	def name_search(self, name, args=None, operator='ilike', limit=100):
		if args is None:
			args = []
		context = self.env.context
		domain = []
		if name:
			domain = ['|','|','|',('acc_number', operator, name),('bank_id', operator, name),('partner_id', operator, name),('acc_holder_name',operator,name)]
		recs = self.search(domain + args, limit=limit)
		return recs.name_get()