### import file ###
from odoo import models,fields,api
from dateutil.relativedelta import relativedelta

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    trip_id = fields.Many2one('venus.trip','Route',required=True, domain="[('state', '=', 'started')]")
    sale_type = fields.Selection([('direct','Direct Sale'),('trip','Van Sale')],'Sale Type',default='direct')
    
    @api.onchange('sale_type')
    def onchange_sale_type(self):
        if self.sale_type=='direct':
            self.user_id = False
            self.team_id = False
            self.trip_id = False
    
    @api.onchange('trip_id')
    def onchange_trip_id(self):
        if self.trip_id:
            self.user_id = self.trip_id.user_id.id
            self.team_id = self.trip_id.user_id.team_id.id
            
    def validate_transfer(self):
        for rec in self:
            for stok in rec.picking_ids:
                for line in stok.move_ids_without_package:
                    line.quantity_done = line.product_uom_qty
                stok.button_validate()
                
    def order_create_invoices(self):
        for rec in self:
            rec._create_invoices(final=True)
            for invoice in rec.invoice_ids:
                invoice.sudo().action_post()

    def create_all_delivery_and_invoices(self):
        for rec in self:
            rec.sudo().action_confirm()
            rec.sudo().validate_transfer()
            rec.sudo().order_create_invoices()

class StockRule(models.Model):
    _inherit = "stock.rule"
    
    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        ''' Returns a dictionary of values that will be used to create a stock move from a procurement.
        This function assumes that the given procurement has a rule (action == 'pull' or 'pull_push') set on it.

        :param procurement: browse record
        :rtype: dictionary
        '''
        group_id = False
        if self.group_propagation_option == 'propagate':
            group_id = values.get('group_id', False) and values['group_id'].id
        elif self.group_propagation_option == 'fixed':
            group_id = self.group_id.id

        date_scheduled = fields.Datetime.to_string(
            fields.Datetime.from_string(values['date_planned']) - relativedelta(days=self.delay or 0)
        )
        date_deadline = values.get('date_deadline') and (fields.Datetime.to_datetime(values['date_deadline']) - relativedelta(days=self.delay or 0)) or False
        partner = self.partner_address_id or (values.get('group_id', False) and values['group_id'].partner_id)
        if partner:
            product_id = product_id.with_context(lang=partner.lang or self.env.user.lang)
        picking_description = product_id._get_description(self.picking_type_id)
        if values.get('product_description_variants'):
            picking_description += values['product_description_variants']
        # it is possible that we've already got some move done, so check for the done qty and create
        # a new move with the correct qty
        qty_left = product_qty
        # Location change code
        location_src_id = self.location_src_id.id
        sale_line_id = self.env['sale.order.line'].browse(values['sale_line_id'])
        if sale_line_id.order_id.trip_id:
            location_src_id = sale_line_id.order_id.trip_id.location_id.id
        ################   
        move_dest_ids = []
        if not self.location_id.should_bypass_reservation():
            move_dest_ids = values.get('move_dest_ids', False) and [(4, x.id) for x in values['move_dest_ids']] or []

        move_values = {
            'name': name[:2000],
            'company_id': self.company_id.id or self.location_src_id.company_id.id or self.location_id.company_id.id or company_id.id,
            'product_id': product_id.id,
            'product_uom': product_uom.id,
            'product_uom_qty': qty_left,
            'partner_id': partner.id if partner else False,
            'location_id': location_src_id,
            'location_dest_id': location_id.id,
            'move_dest_ids': move_dest_ids,
            'rule_id': self.id,
            'procure_method': self.procure_method,
            'origin': origin,
            'picking_type_id': self.picking_type_id.id,
            'group_id': group_id,
            'route_ids': [(4, route.id) for route in values.get('route_ids', [])],
            'warehouse_id': self.propagate_warehouse_id.id or self.warehouse_id.id,
            'date': date_scheduled,
            'date_deadline': False if self.group_propagation_option == 'fixed' else date_deadline,
            'propagate_cancel': self.propagate_cancel,
            'description_picking': picking_description,
            'priority': values.get('priority', "0"),
            'orderpoint_id': values.get('orderpoint_id') and values['orderpoint_id'].id,
        }
        for field in self._get_custom_move_fields():
            if field in values:
                move_values[field] = values.get(field)
        return move_values
