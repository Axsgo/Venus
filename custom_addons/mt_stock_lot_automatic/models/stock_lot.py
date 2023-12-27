### import file ###
from odoo import api,models,fields
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def _get_default_auto_lot(self):
        params = self.env['ir.config_parameter'].sudo()
        enable_auto_lot = params.get_param('enable_auto_lot',default=False)
        if enable_auto_lot == 'True':
            return True
        else:
            return False

    enable_auto_lot = fields.Boolean("Enable Automatic Serial No", default=lambda self: self._get_default_auto_lot())

    @api.onchange('tracking')
    def update_auto_lot(self):
        if self.tracking in ('serial','lot'):
            params = self.env['ir.config_parameter'].sudo()
            enable_auto_lot = params.get_param('enable_auto_lot',default=False)
            if enable_auto_lot == 'True':
                self.enable_auto_lot = True
            else:
                self.enable_auto_lot = False
        else:
            self.enable_auto_lot = False
            
    @api.constrains('default_code')
    def duplicate_default_code_contrains(self):
        for rec in self:
            if rec.default_code:
                code=rec.default_code.upper()  
                code=code.replace("'", "")
                self.env.cr.execute(""" select upper(default_code) from product_template where upper(default_code)  = '%s' and id != '%s'""" %(code,rec.id))
                data = self.env.cr.dictfetchall()
                if data:
                    raise UserError(("Warning!!, Product Code - %s should not be unique !")%(rec.default_code))


class ProductProduct(models.Model):
    _inherit = "product.product"

    enable_auto_lot = fields.Boolean("Enable Automatic Serial No",related='product_tmpl_id.enable_auto_lot',store=True)

    @api.constrains('default_code')
    def duplicate_default_code_contrains(self):
        if self.default_code:
            name=self.default_code.upper()  
            name=name.replace("'", "")
            self.env.cr.execute(""" select upper(default_code) from product_product where upper(default_code)  = '%s' and id != '%s'""" %(name,self.id))
            data = self.env.cr.dictfetchall()
            if data:
                raise UserError(("Warning!!, Product Code - %s should not be unique !")%(self.default_code))


class ProductSettings(models.TransientModel):
    _inherit = "res.config.settings"

    enable_auto_lot = fields.Boolean("Enable Automatic Serial No")

    @api.onchange('enable_auto_lot')
    def create_lot_seq(self):
        if self.enable_auto_lot == True:
            product_ids = self.env['product.template'].search([('tracking','=','serial')])
            for line in product_ids:
                line.enable_auto_lot = True
        else:
            product_ids = self.env['product.template'].search([('tracking','=','serial')])
            for line in product_ids:
                line.enable_auto_lot = False

    @api.model
    def get_values(self):
        res = super(ProductSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        enable_auto_lot = params.get_param('enable_auto_lot',default=False)
        res.update(enable_auto_lot=enable_auto_lot)
        return res

    def set_values(self):
        super(ProductSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param("enable_auto_lot",self.enable_auto_lot)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _set_auto_lot(self):
        """
        Allows to be called either by button or through code
        """
        pickings = self.filtered(lambda p: p.picking_type_id.code == 'incoming')
        lines = pickings.mapped("move_line_ids").filtered(
            lambda x: (
            not x.lot_id
            and not x.lot_name
            and x.product_id.tracking in ("serial",'lot')
            and x.product_id.enable_auto_lot
            and x.qty_done != 0
            )
        )
        lines.set_lot_auto()

    def _replace_batch(self):
        pickings = self.filtered(lambda p: p.picking_type_id.code == 'outgoing')
        lines = pickings.mapped("move_line_ids").filtered(
            lambda x: (
            x.lot_id
            and x.product_id.tracking in ("serial",'lot')
            and x.product_id.enable_auto_lot
            and x.serial_no != False
            )
        )
        for l in lines:
            l.lot_id.name = l.serial_no

    def _action_done(self):
        self._set_auto_lot()
        return super()._action_done()

    def button_validate(self):
        self._set_auto_lot()
        self._replace_batch()
        return super().button_validate()


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.depends(
        "has_tracking",
        "product_id.enable_auto_lot",
        "picking_type_id.use_existing_lots",
        "state",
    )
    def _compute_display_assign_serial(self):
        super()._compute_display_assign_serial()
        moves_not_display = self.filtered(
            lambda m: m.product_id.enable_auto_lot
        )
        for move in moves_not_display:
            move.display_assign_serial = False

    enable_auto_lot = fields.Boolean("Enable Automatic Serial No",compute="_get_product_auto_lot")
    show_lots_text = fields.Boolean("Show Lot",related='picking_id.show_lots_text')
    tracking = fields.Selection([('none','No Batch/Serial No Required'),('lot','Lot/Batch No Required'),('serial','Serial No Required')],
        'Product Tracking',related='product_id.tracking')
    
    def _set_product_qty(self):
        """ The meaning of product_qty field changed lately and is now a functional field computing the quantity
        in the default product UoM. This code has been added to raise an error if a write is made given a value
        for `product_qty`, where the same write should set the `product_uom_qty` field instead, in order to
        detect errors. """
        # raise UserError(_('The requested operation cannot be processed because of a programming error setting the `product_qty` field instead of the `product_uom_qty`.'))
        return True
    
    @api.depends("product_id")
    def _get_product_auto_lot(self):
        for rec in self:
            if rec.product_id and rec.product_id.enable_auto_lot == True:
                rec.enable_auto_lot = True
            else:
                rec.enable_auto_lot = False

    def action_update_move_quantity(self):
        if self.next_serial_count <= 0:
            raise UserError("Warning!!, Number of Qty should be greater than Zero.")
        move_lines_commands = self._generate_serial_move_line_commands()
        self.write({'move_line_ids': move_lines_commands})
        return self.action_show_details()

    def _generate_serial_move_line_commands(self, lot_names=None, origin_move_line=None):
        self.ensure_one()
        # Select the right move lines depending of the picking type configuration.
        move_lines = self.env['stock.move.line']
        if self.picking_type_id.show_reserved:
            move_lines = self.move_line_ids.filtered(lambda ml: not ml.lot_id and not ml.lot_name)
        else:
            move_lines = self.move_line_nosuggest_ids.filtered(lambda ml: not ml.lot_id and not ml.lot_name)

        if origin_move_line:
            location_dest = origin_move_line.location_dest_id
        else:
            location_dest = self.location_dest_id._get_putaway_strategy(self.product_id)
        move_line_vals = {
            'picking_id': self.picking_id.id,
            'location_dest_id': location_dest.id or self.location_dest_id.id,
            'location_id': self.location_id.id,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_id.uom_id.id,
            'qty_done': 1 if self.product_id.tracking == 'serial' else self.next_serial_count,
        }
        if origin_move_line:
            # `owner_id` and `package_id` are taken only in the case we create
            # new move lines from an existing move line. Also, updates the
            # `qty_done` because it could be usefull for products tracked by lot.
            move_line_vals.update({
                'owner_id': origin_move_line.owner_id.id,
                'package_id': origin_move_line.package_id.id,
                'qty_done': origin_move_line.qty_done or 1,
            })

        move_lines_commands = []
        if self.enable_auto_lot == True:
            if self.product_id.tracking == 'serial':
                for i in range(0,self.next_serial_count):
                    if move_lines:
                        move_lines_commands.append((1, move_lines[0].id, {
                            'qty_done': 1,
                            # 'expiration_date':self.expiration_date,
                        }))
                        move_lines = move_lines[1:]
                    # ... or create a new move line with the serial name.
                    else:
                        # product_id = self.env['product.product'].browse(move_line_vals['product_id'])
                        # if product_id.use_expiration_date == True:
                        #     move_line_vals['expiration_date'] = fields.Datetime.today() + timedelta(days=product_id.expiration_time)
                        move_line_cmd = dict(move_line_vals)
                        move_lines_commands.append((0, 0, move_line_cmd))
            elif self.product_id.tracking == 'lot':
                if move_lines:
                    move_lines_commands.append((1, move_lines[0].id, {
                        'qty_done': self.next_serial_count,
                        # 'expiration_date':self.expiration_date,
                    }))
                    move_lines = move_lines[1:]
                # ... or create a new move line with the serial name.
                else:
                    # product_id = self.env['product.product'].browse(move_line_vals['product_id'])
                    # if product_id.use_expiration_date == True:
                    #     move_line_vals['expiration_date'] = fields.Datetime.today() + timedelta(days=product_id.expiration_time)
                    move_line_cmd = dict(move_line_vals)
                    move_lines_commands.append((0, 0, move_line_cmd))
        else:
            for lot_name in lot_names:
                # We write the lot name on an existing move line (if we have still one)...
                if move_lines:
                    move_lines_commands.append((1, move_lines[0].id, {
                        'lot_name': lot_name,
                        'qty_done': 1,
                    }))
                    move_lines = move_lines[1:]
                # ... or create a new move line with the serial name.
                else:
                    move_line_cmd = dict(move_line_vals, lot_name=lot_name)
                    move_lines_commands.append((0, 0, move_line_cmd))
        return move_lines_commands


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    serial_no = fields.Char("Supplier Serial No")
    enable_auto_lot = fields.Boolean("Enable Automatic Serial No",compute="_get_product_auto_lot")

    @api.depends("product_id")
    def _get_product_auto_lot(self):
        for rec in self:
            if rec.product_id and rec.product_id.enable_auto_lot == True:
                rec.enable_auto_lot = True
            else:
                rec.enable_auto_lot = False

    def _prepare_auto_lot_values(self):
        """
        Prepare multi valued lots per line to use multi creation.
        """
        self.ensure_one()
        return {"product_id": self.product_id.id, "company_id": self.company_id.id}

    def set_lot_auto(self):
        from odoo.fields import first
        """
        Create lots using create_multi to avoid too much queries
        As move lines were created by product or by tracked 'serial'
        products, we apply the lot with both different approaches.
        """
        values = []
        production_lot_obj = self.env["stock.production.lot"]
        lots_by_product = dict()
        for line in self:
            values.append(line._prepare_auto_lot_values())
        lots = production_lot_obj.create(values)
        for lot in lots:
            if lot.product_id.id not in lots_by_product:
                lots_by_product[lot.product_id.id] = lot
            else:
                lots_by_product[lot.product_id.id] += lot
        for line in self:
            lot = first(lots_by_product[line.product_id.id])
            line.lot_id = lot
            if lot.product_id.tracking in ("serial",'lot'):
                lots_by_product[line.product_id.id] -= lot
                

class AccStockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    qty_available = fields.Float('qty_available',related='product_qty',store=True)
