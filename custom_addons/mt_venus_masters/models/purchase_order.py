### import file ###
from odoo import models,fields,api
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    trip_id = fields.Many2one('venus.trip','Route', required=True, domain="[('state', '=', 'started')]")
    free_line_ids = fields.One2many('purchase.order.free','order_id',string='Free product Avg')
    free_price_unit = fields.Float(string='Price Unit', digits='Product Price', required=True)
    free_avg_price_unit = fields.Float(string='Average Price', digits='Product Price', compute='_compute_free_purchase_qty')
    purchase_type = fields.Selection([('direct','Direct Purchase'),('trip','Van Purchase')],'Purchase Type',default='direct')
    
    @api.onchange('purchase_type')
    def onchange_purchase_type(self):
        if self.purchase_type=='direct':
            self.user_id = False
            self.trip_id = False
            
    @api.depends('free_price_unit','free_line_ids.purchase_qty','free_line_ids.product_qty')
    def _compute_free_purchase_qty(self):
        purchase_qty = product_qty = 0
        for record in self.free_line_ids:
            purchase_qty += record.purchase_qty
            product_qty += record.product_qty
        if product_qty > 0:
            self.free_avg_price_unit = (purchase_qty*self.free_price_unit)/ product_qty
        else:
            self.free_avg_price_unit = 0
            
    def update_po_line(self):       
        for record in self.free_line_ids:
            self.env['purchase.order.line'].sudo().create({
                'name': '[%s] %s' % (record.product_id.default_code, record.product_id.name) if record.product_id.default_code else record.product_id.name,
                'product_qty': record.product_qty,
                'purchase_qty': record.purchase_qty,
                'free_qty': record.free_qty,
                'product_id': record.product_id.id,
                'product_uom': record.product_uom.id,
                'price_unit': self.free_avg_price_unit,
                'taxes_id': [(6, 0, record.product_id.supplier_taxes_id.ids)],
                'order_id': self.id,
            })
            
    def clear_list(self):  
        self.free_line_ids.unlink()
        self.free_price_unit = 0
    
    def _prepare_picking(self):
        if not self.group_id:
            self.group_id = self.group_id.create({
                'name': self.name,
                'partner_id': self.partner_id.id
            })
        if not self.partner_id.property_stock_supplier.id:
            raise UserError(_("You must set a Vendor Location for this partner %s", self.partner_id.name))
        # Location change code
        location_dest_id = self._get_destination_location()
        if self.trip_id:
            location_dest_id = self.trip_id.location_id.id
        ##################
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'user_id': False,
            'date': self.date_order,
            'origin': self.name,
            'location_dest_id': location_dest_id,
            'location_id': self.partner_id.property_stock_supplier.id,
            'company_id': self.company_id.id,
        }
        
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    purchase_qty = fields.Float(string='Purchase Qty', digits='Product Unit of Measure', required=True, default=1)
    free_qty = fields.Float(string='Free Qty', digits='Product Unit of Measure')
    
    @api.onchange('purchase_qty', 'free_qty')
    def _onchange_purchase_free_qty(self):
        self.product_qty = self.purchase_qty + self.free_qty
        
    # def _prepare_compute_all_values(self):
    #     # Hook method to returns the different argument values for the
    #     # compute_all method, due to the fact that discounts mechanism
    #     # is not implemented yet on the purchase orders.
    #     # This method should disappear as soon as this feature is
    #     # also introduced like in the sales module.
    #     self.ensure_one()
    #     return {
    #         'price_unit': self.price_unit,
    #         'currency_id': self.order_id.currency_id,
    #         'product_qty': self.purchase_qty,
    #         'product': self.product_id,
    #         'partner': self.order_id.partner_id,
    #     }
        
    # @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity', 'qty_received', 'product_uom_qty', 'order_id.state')
    # def _compute_qty_invoiced(self):
    #     for line in self:
    #         # compute qty_invoiced
    #         qty = 0.0
    #         for inv_line in line.invoice_lines:
    #             if inv_line.move_id.state not in ['cancel']:
    #                 if inv_line.move_id.move_type == 'in_invoice':
    #                     qty += inv_line.product_uom_id._compute_quantity(inv_line.quantity, line.product_uom)
    #                 elif inv_line.move_id.move_type == 'in_refund':
    #                     qty -= inv_line.product_uom_id._compute_quantity(inv_line.quantity, line.product_uom)
    #         line.qty_invoiced = qty
    #
    #         # compute qty_to_invoice
    #         if line.order_id.state in ['purchase', 'done']:
    #             if line.product_id.purchase_method == 'purchase':
    #                 line.qty_to_invoice = line.purchase_qty - line.qty_invoiced
    #             else:
    #                 if line.free_qty > 0:
    #                     line.qty_to_invoice = line.purchase_qty - line.qty_invoiced
    #                 else:
    #                     line.qty_to_invoice = line.qty_received - line.qty_invoiced
    #         else:
    #             line.qty_to_invoice = 0
        
class PurchaseOrderFree(models.Model):
    _name = "purchase.order.free"
    _description = "Free product Avg"
    _order = "id desc"

    order_id = fields.Many2one('purchase.order','Purchase Order')
    product_id = fields.Many2one('product.product','Product', required=True)
    purchase_qty = fields.Float(string='Purchase Qty', digits='Product Unit of Measure', required=True, default=1)
    free_qty = fields.Float(string='Free Qty', digits='Product Unit of Measure')
    product_qty = fields.Float(string='Total Qty', digits='Product Unit of Measure', required=True)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', required=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    
    @api.onchange('purchase_qty', 'free_qty')
    def _onchange_purchase_free_qty(self):
        self.product_qty = self.purchase_qty + self.free_qty
        
    @api.onchange('product_id')
    def _onchange_product(self):
        if not self.product_id:
            return
        else:
            self.product_uom = self.product_id.uom_po_id.id
            self.product_qty = 1.0
    