### import file ###
from odoo import api,models,fields
from odoo.exceptions import UserError
import time

class VenusDriver(models.Model):
	_name = "venus.driver"
	_description = "Driver master"
	_order = "id desc"

	name = fields.Char("Name")
	dob = fields.Date("DOB")
	phone = fields.Char("Phone")
	licence = fields.Char("Licence")
	licence_expiry = fields.Date("Licence Expiry Date")
	vehicle_id = fields.Many2one('venus.vehicle','Vehicle')
	crt_date = fields.Datetime('Creation Date',readonly = True,default = lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'))
	user_id = fields.Many2one('res.users','Created By',readonly = True,default = lambda self: self.env.user.id)
	ap_rej_date = fields.Datetime('Approved Date', readonly = True)
	ap_rej_user_id = fields.Many2one('res.users', 'Approved By', readonly = True)
	cancel_date = fields.Datetime('Approved Date', readonly = True)
	cancel_user_id = fields.Many2one('res.users', 'Cancelled By', readonly = True)
	update_date = fields.Datetime('Last Update On',readonly = True,default = lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'))
	update_user_id = fields.Many2one('res.users','Last Update By',readonly = True,default = lambda self: self.env.user.id)
	notes = fields.Text("Notes")
	company_id = fields.Many2one('res.company','Company',default = lambda self: self.env.company.id)
	state = fields.Selection([('draft','Draft'),('approved','Approved'),('cancel','Cancelled')],'Status',default='draft')

	@api.model
	def create(self, vals):
		self.env.cr.execute(""" select * from venus_driver where vehicle_id  = '%s'""" %(vals.get('vehicle_id')))
		data = self.env.cr.dictfetchall()
		if data:
			raise UserError("Warning!!, This vehicle is already assigned another driver!!")
		return super(VenusDriver, self).create(vals)
	
	def write(self, vals):
		vals.update({'update_date': time.strftime('%Y-%m-%d %H:%M:%S'),'update_user_id': self.env.user.id})
		return super(VenusDriver, self).write(vals)
	
	def entry_draft(self):
		self.write({'state': 'draft'})

	def entry_approve(self):
		if self.state == 'draft':
			self.write({'state': 'approved',
                        'ap_rej_user_id': self.env.user.id,
                        'ap_rej_date': time.strftime('%Y-%m-%d %H:%M:%S')})

	def entry_cancel(self):
		self.write({'state': 'cancel',
                        'cancel_user_id': self.env.user.id,
                        'cancel_date': time.strftime('%Y-%m-%d %H:%M:%S')})

	def _entry_licence_expiry(self):
		from datetime import datetime
		driver_ids = self.env['venus.driver'].search([])
		if driver_ids:
			admin_id = self.env['res.users'].search([('is_admin','=',True)])
			for line in driver_ids:
				template = self.env['ir.model.data'].get_object('mt_venus_masters', 'email_template_venus_licence_mail')
				if line.licence_expiry > datetime.now().date() and (datetime.now().date() - line.licence_expiry).days in [7,3,1]:
					context = {
								'expiry_date': line.licence_expiry.strftime('%d/%m/%Y'),
								'email_to': admin_id.email,
								'emp_name': admin_id.name,
								'lang': admin_id.lang,
								'status':'Going to Expire',
							  }
					self.env['mail.template'].browse(template.id).with_context(context).send_mail(line.id,force_send=True)
				elif line.licence_expiry < datetime.now().date() or datetime.now().date() == line.licence_expiry:
					context = {
								'expiry_date': line.licence_expiry.strftime('%d/%m/%Y'),
								'email_to': admin_id.email,
								'emp_name': admin_id.name,
								'lang': admin_id.lang,
								'status':'Expired',
							  }
					self.env['mail.template'].browse(template.id).with_context(context).send_mail(line.id,force_send=True)
