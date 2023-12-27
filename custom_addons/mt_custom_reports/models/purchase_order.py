### import file ###
from odoo import models,api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    @api.onchange('product_id', 'product_uom')
    def _onchange_product_uom(self):
        if self.product_id.name and self.product_uom.name:
            self.name = self.product_id.name +' '+ self.product_uom.name
        