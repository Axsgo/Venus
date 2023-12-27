from odoo import fields,api,models
from calendar import monthrange
import calendar,time
from datetime import datetime,date
from odoo.exceptions import UserError,ValidationError

class AxWarehouseRent(models.Model):
    _name = "ax.warehouse.rent"
    _order = "crt_date desc"

    @api.model
    def create(self, vals):
        vals['code'] = self.env['ir.sequence'].next_by_code('ax.warehouse.rent')
        return super(AxWarehouseRent, self).create(vals)

    def write(self, vals):
        vals.update({'update_date': time.strftime('%Y-%m-%d %H:%M:%S'),'update_user_id': self.env.user.id})
        return super(AxWarehouseRent, self).write(vals)

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company.id)
    name = fields.Char('Description',store=True)

    sq_feet_from = fields.Integer('Square Feet- From',store=True)
    sq_feet_to = fields.Integer('Square Feet- To',store=True)

    amount = fields.Float('Amount',store=True)
    partner_ids = fields.Many2many('res.partner', column1='user_id', column2='partner_id', string='Partners')
    code = fields.Char('Code',store=True)
    state = fields.Selection([('draft','Draft'),('approved','Approved'),('cancel','Cancelled')],default='draft',string="Status")
    crt_date = fields.Datetime(
    'Creation Date',
    readonly = True,
    default = lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'))
    user_id = fields.Many2one(
    'res.users',
    'Created By',
    readonly = True,
    default = lambda self: self.env.user.id)
    update_date = fields.Datetime(
    'Last Update On',
    readonly = True,
    default = lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'))
    update_user_id = fields.Many2one(
    'res.users',
    'Last Update By',
    readonly = True,
    default = lambda self: self.env.user.id)
    ap_rej_date = fields.Datetime(
    'Approved On',
    readonly = True)
    ap_rej_user_id = fields.Many2one(
    'res.users',
    'Approved By',
    readonly = True)
    cancel_date = fields.Datetime(
    'Cancelled On',
    readonly = True)
    cancel_user_id = fields.Many2one(
    'res.users',
    'Cancelled By',
    readonly = True)

    def unlink(self):
        """ Unlink """
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Warning!, You can not delete this entry !!')
            else:
                return super(AxWarehouseRent, self).unlink()

    def set_to_draft(self):
        self.write({'state': 'draft',
                    })

    def entry_approve(self):
        self.write({'state': 'approved',
                    'ap_rej_user_id': self.env.user.id,
                    'ap_rej_date': time.strftime('%Y-%m-%d %H:%M:%S')})

    def entry_cancel(self):
        self.write({'state': 'cancel',
                        'cancel_user_id': self.env.user.id,
                        'cancel_date': time.strftime('%Y-%m-%d %H:%M:%S')})

      
