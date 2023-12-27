### import file ###
from odoo import models,api,fields

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id', 'product_uom')
    def _onchange_product_uom(self):
        if self.product_id.name and self.product_uom.name:
            self.name = self.product_id.name +' '+ self.product_uom.name   

# class ProductTemplate(models.Model):
#     _inherit = "product.template"
#
#     type = fields.Selection([
#         ('consu', 'Consumable'),
#         ('service', 'Service')], string='Product Type', default='service', required=True, 
#         help='A storable product is a product for which you manage stock. The Inventory app has to be installed.\n'
#              'A consumable product is a product for which stock is not managed.\n'
#              'A service is a non-material product you provide.')