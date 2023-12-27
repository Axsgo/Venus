### import file ###
from odoo import api,models,fields
from odoo.exceptions import UserError
from datetime import datetime
import time

class VenusVehicle(models.Model):
	_name = "venus.vehicle"
	_description = "Vehicle master"
	_order = "id desc"

	name = fields.Char("No")
	model = fields.Char("Model")
	vehicle_name = fields.Char("Name")
	manufacturer = fields.Char("Manufacturer")
	year = fields.Date("Year of Manufacture")
	kms_driven = fields.Float("Total Driven Kms",digits=(12,2))
	kms_as_on = fields.Date("Total Driven Kms As On")
	ins_no = fields.Char("Insurance No")
	ins_expiry = fields.Date("Insurance Expiry Date")
	reg_expiry = fields.Date("Registration Expiry Date")
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
	line_ids = fields.One2many('venus.trip.log','id',string='Route Log')
	
	def write(self, vals):
		vals.update({'update_date': time.strftime('%Y-%m-%d %H:%M:%S'),'update_user_id': self.env.user.id})
		return super(VenusVehicle, self).write(vals)
	
	@api.constrains('name')
	def _check_duplicate_contrains(self):
		if self.name:
			name=self.name.upper()  
			name=name.replace("'", "")
			self.env.cr.execute(""" select upper(name) from venus_vehicle where upper(name)  = '%s' and id != '%s'""" %(name,self.id))
			data = self.env.cr.dictfetchall()
			if data:
				raise UserError("Warning!!, You are not able to create multiple record in same Name !!")
			
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
		
	def _entry_vehicle_expiry(self):
		vehicle_ids = self.env['venus.vehicle'].search([])
		admin_id = self.env['res.users'].search([('is_admin','=',True)])
		for line in vehicle_ids:
			template = self.env['ir.model.data'].get_object('mt_venus_masters', 'email_template_venus_vehcile_ins_mail')
			template1 = self.env['ir.model.data'].get_object('mt_venus_masters', 'email_template_venus_vehcile_reg_mail')
			if line.ins_expiry > datetime.now().date() and (datetime.now().date() - line.ins_expiry).days in [7,3,1]:
				context = {
							'expiry_date': line.ins_expiry.strftime('%d/%m/%Y'),
							'email_to': admin_id.email,
							'emp_name': admin_id.name,
							'status':'Going to Expire',
						  }
				self.env['mail.template'].browse(template.id).with_context(context).send_mail(line.id,force_send=True)
			elif line.ins_expiry < datetime.now().date() or datetime.now().date() == line.ins_expiry:
				context = {
							'expiry_date': line.ins_expiry.strftime('%d/%m/%Y'),
							'email_to': admin_id.email,
							'emp_name': admin_id.name,
							'status':'Expired',
						  }
				self.env['mail.template'].browse(template.id).with_context(context).send_mail(line.id,force_send=True)
			if line.reg_expiry > datetime.now().date() and (datetime.now().date() - line.reg_expiry).days in [7,3,1]:
				context = {
							'expiry_date': line.reg_expiry.strftime('%d/%m/%Y'),
							'email_to': admin_id.email,
							'emp_name': admin_id.name,
							'status':'Going to Expire',
						  }
				self.env['mail.template'].browse(template1.id).with_context(context).send_mail(line.id,force_send=True)
			elif line.reg_expiry < datetime.now().date() or datetime.now().date() == line.reg_expiry:
				context = {
							'expiry_date': line.reg_expiry.strftime('%d/%m/%Y'),
							'email_to': admin_id.email,
							'emp_name': admin_id.name,
							'status':'Expired',
						  }
				self.env['mail.template'].browse(template1.id).with_context(context).send_mail(line.id,force_send=True)
				
class VenusTripLog(models.Model):
	_name = "venus.trip.log"
	_description = "Trip master"
	_order = "id desc"

	trip_id = fields.Many2one('venus.trip','Route')
	vehicle_id = fields.Many2one('venus.vehicle','Vehicle')
	start_km = fields.Float("KM at the start")
	end_km = fields.Float("KM at the end")
	