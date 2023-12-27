import time
from odoo import api, models, fields, _
from odoo.exceptions import UserError


class AccountCode(models.Model):
    _name = "account.code"

    def write(self, vals):
        """ Write """
        vals.update({'update_date': time.strftime(
        '%Y-%m-%d %H:%M:%S'), 'update_user_id': self.env.user.id})                            
        return super(AccountCode, self).write(vals)

    def name_get(self):
        res = []
        for account in self:
            name = ''
            if account.user_type_id and account.internal_group:
                inter_val = account.internal_group
                name = account.user_type_id.name + ' - ' + inter_val.capitalize()
            res.append((account.id, name))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        context = self.env.context
        domain = []
        if name:
            domain = ['|','|',('name', operator, name),('user_type_id', operator, name),('code', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()

    name = fields.Char("Name")
    user_type_id = fields.Many2one('account.account.type', string='Account Type', required=True,
        help="Account Type is used for information purpose, to generate country-specific legal reports, and set the rules to close a fiscal year and generate opening entries.")
    internal_group = fields.Selection(related='user_type_id.internal_group', string="Account Category", store=True, readonly=True)
    code = fields.Char("Starting Sequence",store=True)
    notes = fields.Text("Account Description")
    company_id = fields.Many2one("res.company",'Company',default=lambda self: self.env.company.id)
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

    @api.onchange('user_type_id')
    def _onchange_user_type_id(self):
        seq_val = ''
        if self.user_type_id:
            if self.user_type_id.internal_group == 'asset':
                if self.user_type_id.id == 1:
                    seq_val = '100101'
                if self.user_type_id.id == 3:
                    seq_val = '100201'
                if self.user_type_id.id == 5:
                    seq_val = '100301'
                if self.user_type_id.id == 6:
                    seq_val = '100401'
                if self.user_type_id.id == 7:
                    seq_val = '100501'
                if self.user_type_id.id == 8:
                    seq_val = '100601'
            if self.user_type_id.internal_group == 'liability':
                if self.user_type_id.id == 2:
                    seq_val = '110101'
                if self.user_type_id.id == 4:
                    seq_val = '110201'
                if self.user_type_id.id == 9:
                    seq_val = '110301'
                if self.user_type_id.id == 10:
                    seq_val = '110401'
            if self.user_type_id.internal_group == 'equity':
                if self.user_type_id.id == 11:
                    seq_val = '120101'
                if self.user_type_id.id == 12:
                    seq_val = '120201'
            if self.user_type_id.internal_group == 'income':
                if self.user_type_id.id == 13:
                    seq_val = '200101'
                if self.user_type_id.id == 14:
                    seq_val = '200201'
            if self.user_type_id.internal_group == 'expense':
                if self.user_type_id.id == 15:
                    seq_val = '210101'
                if self.user_type_id.id == 16:
                    seq_val = '210201'
                if self.user_type_id.id == 17:
                    seq_val = '210301'
            if self.user_type_id.internal_group == 'off_balance':
                if self.user_type_id.id == 18:
                    seq_val = '300101'

            if seq_val:
                self.code = seq_val
        else:
            self.code = ''


class AccountAccount(models.Model):
    _inherit = "account.account"

    account_code_id = fields.Many2one('account.code', string='Account Type')
    account_code = fields.Char("Code",related='code')
    sequence_number = fields.Integer("Sequence No")
    category_type = fields.Selection([('sales_income','Revenue - Sales'),('cost_of_sales','Cost of Sales'),('receipts','Revenue - Others'),
        ('overheads','Overheads'),('overheadsgroup','Overheads Group'),('fixed_assets','Fixed Assets'),('current_assets','Current Assets'),
        ('current_liability','Current Liabilities'),
        ('long_term_liability','Long Term Liabilities'),('capital_reserves','Capital & Reserves')],'Report Type')

    @api.onchange('account_code_id')
    def _onchange_account_code_id(self):
        list_code = []
        if self.account_code_id:
            self.user_type_id = self.account_code_id.user_type_id.id
            account_account_ids = self.env['account.account'].search([('account_code_id', '=', self.account_code_id.id),('id', '!=', self._origin.id)])
            if account_account_ids:
                for accounts in account_account_ids:
                    list_code.append(int(accounts.code))
                val = int(max(list_code)) + int(1)
                self.code = str(val)
            else:
                self.code = self.account_code_id.code
            

