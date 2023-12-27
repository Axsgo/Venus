### import file ###
from odoo import api,models,fields
import time
from datetime import date
from odoo.exceptions import UserError

class VenusTrip(models.Model):
	_name = "venus.trip"
	_description = "Trip master"
	_order = "id desc"

	name = fields.Char("Name",readonly=True,copy=False)
	driver_id = fields.Many2one('venus.driver','Driver')
	vehicle_id = fields.Many2one('venus.vehicle','Vehicle')
	trip_location_id = fields.Many2many('venus.trip.location', string='Route Location')
	location_id = fields.Many2one('stock.location','Stock Location')
	user_id = fields.Many2one('res.users','Sales person')
	company_id = fields.Many2one('res.company','Company',default = lambda self: self.env.company.id)
	start_km = fields.Float("KM at the start")
	end_km = fields.Float("KM at the end")
	crt_date = fields.Datetime('Creation Date',readonly = True,default = lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'))
	crt_user_id = fields.Many2one('res.users','Created By',readonly = True,default = lambda self: self.env.user.id)
	start_date = fields.Datetime('Started Date', readonly = True)
	start_user_id = fields.Many2one('res.users', 'Started By', readonly = True)
	end_date = fields.Datetime('Ended Date', readonly = True)
	end_user_id = fields.Many2one('res.users', 'Ended By', readonly = True)
	cancel_date = fields.Datetime('Cancel Date', readonly = True)
	cancel_user_id = fields.Many2one('res.users', 'Cancelled By', readonly = True)
	update_date = fields.Datetime('Last Update On',readonly = True,default = lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'))
	update_user_id = fields.Many2one('res.users','Last Update By',readonly = True,default = lambda self: self.env.user.id)
	notes = fields.Text("Notes")
	state = fields.Selection([('draft','Draft'),('started','Open'),('ended','Close'),('cancel','Cancel')],'Status',default='draft')
	
	def name_get(self):
		res = []
		for trip in self:
			name = trip.name
			if trip.vehicle_id:
				name = '[' + trip.vehicle_id.name + '] ' + name
			res.append((trip.id, name))
		return res
	
	@api.constrains('driver_id')
	def _check_duplicate_contrains(self):
		if self.name:
			self.env.cr.execute(""" select * from venus_trip where driver_id  = '%s' and id != '%s' and state = 'started'""" %(self.driver_id.id,self.id))
			data = self.env.cr.dictfetchall()
			if data:
				raise UserError("Warning!!, This Driver already assigned another Route!!")
			
	@api.onchange('driver_id')
	def update_driver_id(self):
		if self.driver_id:
			self.vehicle_id = self.driver_id.vehicle_id.id
	
	@api.model
	def create(self, vals):
		vals['name'] = self.env['ir.sequence'].next_by_code('venus.trip')
		return super(VenusTrip, self).create(vals)		
	
	def write(self, vals):
		vals.update({'update_date': time.strftime('%Y-%m-%d %H:%M:%S'),'update_user_id': self.env.user.id})
		return super(VenusTrip, self).write(vals)
	
	def entry_draft(self):
		self.write({'state': 'draft'})

	def entry_start(self):
		if self.name:
			self.env.cr.execute(""" select * from venus_trip where driver_id  = '%s' and id != '%s' and state = 'started'""" %(self.driver_id.id,self.id))
			data = self.env.cr.dictfetchall()
			if data:
				raise UserError("Warning!!, This Driver already assigned another Route!!")
		if self.state == 'draft':
			self.write({'state': 'started','start_user_id': self.env.user.id,'start_date': time.strftime('%Y-%m-%d %H:%M:%S')})
	
	def entry_end(self):
		if self.state == 'started':
			self.write({'state': 'ended','end_user_id': self.env.user.id,'end_date': time.strftime('%Y-%m-%d %H:%M:%S')})
		if self.end_km > self.start_km:
			self.vehicle_id.write({'kms_driven':self.end_km,'kms_as_on':date.today()})
			self.env['venus.trip.log'].create({'trip_id':self.id,'vehicle_id':self.vehicle_id.id,
											'start_km':self.start_km,'end_km':self.end_km})
		else:
			raise UserError("Warning!!, Kindly enter the correct End KM!!")
			
	def entry_cancel(self):
		self.write({'state': 'cancel','cancel_user_id': self.env.user.id,'cancel_date': time.strftime('%Y-%m-%d %H:%M:%S')})

class VenusTripLocation(models.Model):
	_name = "venus.trip.location"
	_description = "Trip Location master"
	_order = "id desc"

	name = fields.Char("Name",required=True)
	code = fields.Char("Code",required=True,copy=False)
