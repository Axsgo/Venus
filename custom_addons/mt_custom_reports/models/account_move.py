### import file ###
from odoo import api,models,fields,tools,_
from num2words import num2words

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    @api.onchange('product_id', 'product_uom_id')
    def _onchange_product_uom(self):
        if self.product_id.name and self.product_uom_id.name:
            self.name = self.product_id.name +' '+ self.product_uom_id.name	
            
class AccountMove(models.Model):
    _inherit = 'account.move'
    
    amt_pay_type = fields.Selection([('Credit','Credit'),('Cash','Cash'),('Bank','Bank')],string='Payment Type',default='Credit')
    
    def amount_in_en(self,amount):
        return self.currency_id.amount_to_text(amount)
        
    def amount_in_ar(self,amount):
        formatted = "%.{0}f".format(self.currency_id.decimal_places) % amount
        parts = formatted.partition('.')
        integer_value = int(parts[0])
        fractional_value = int(parts[2] or 0)
        amount_words = tools.ustr('{amt_value} {amt_word}').format(amt_value=num2words(integer_value, lang='ar'), amt_word='درهم',)
        if not self.currency_id.is_zero(amount - integer_value):
            amount_words += ' ' + _('و') + tools.ustr(' {amt_value} {amt_word}').format(amt_value=num2words(fractional_value, lang='ar'), amt_word='فلس',)
        return amount_words
    