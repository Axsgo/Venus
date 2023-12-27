### import file ###
from odoo import api,models,fields
import time
from odoo.exceptions import UserError

class AxSaleOrder(models.Model):
    _name = "sale.order"
    _inherit = "sale.order"
    _description = "Axsgo Sale Order"

    order_type = fields.Selection([('1PL','1PL'),('2PL','2PL'),('3PL','3PL'),('4PL','4PL'),('5PL','5PL')],string="Type")

class AxSaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    sq_feet = fields.Integer(string="Square Feet")
    sq_feet_amt = fields.Float(string="Amount")

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id','sq_feet_amt')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups('account.group_account_manager'):
                line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])
            line.update({
                'price_subtotal': taxes['total_excluded'] + line.sq_feet_amt,
            })


    @api.onchange('product_id')
    def product_id_change_unit_price(self):
        if self.product_id:
            self.price_unit = self.product_id.standard_price
        else:
            self.price_unit = 0

    @api.onchange('sq_feet')
    def sq_feet_change_unit_price(self):
        rent_id = []
        rent_new_ids=''
        if self.sq_feet:
            rent_ids = self.env['ax.warehouse.rent'].search([('partner_ids','in',self.order_id.partner_id.id),('state','=','approved')])
            for rec in rent_ids:
                if self.sq_feet >= rec.sq_feet_from and self.sq_feet <= rec.sq_feet_to:
                    rent_id.append(rec.id)
            if rent_id:
                rent_new_ids = self.env['ax.warehouse.rent'].search([('id','in',rent_id)],order='id desc',limit=1)
                if rent_new_ids:
                    self.sq_feet_amt = rent_new_ids.amount
                else:
                    self.sq_feet_amt = 0
            else:
                self.sq_feet_amt = 0
        else:
            self.sq_feet_amt = 0

