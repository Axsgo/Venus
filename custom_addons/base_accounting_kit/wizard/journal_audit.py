# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2019-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from odoo import fields, models
from odoo.tools.misc import get_lang


class AccountPrintJournal(models.TransientModel):
    _inherit = "account.common.journal.report"
    _name = "account.print.journal"
    _description = "Account Print Journal"

    sort_selection = fields.Selection(
        [('date', 'Date'), ('move_name', 'Journal Entry Number')],
        'Entries Sorted by', required=True, default='move_name')
    journal_ids = fields.Many2many('account.journal', string='Journals',
                                   required=True,
                                   default=lambda self: self.env[
                                       'account.journal'].search(
                                       [('type', 'in', ['sale', 'purchase'])]))
    is_direct_jv = fields.Boolean('Direct Journals Alone')

    def _build_contexts(self, data):
        result = {}
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        result['date_from'] = data['form']['date_from'] or False
        result['date_to'] = data['form']['date_to'] or False
        result['strict_range'] = True if result['date_from'] else False
        result['company_id'] = data['form']['company_id'][0] or False
        result['is_manual_entry'] = data['form']['is_direct_jv']
        return result

    def check_report(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'company_id','is_direct_jv'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=get_lang(self.env).code)
        return self.with_context(discard_logo_check=True)._print_report(data)

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'sort_selection': self.sort_selection})
        return self.env.ref(
            'base_accounting_kit.action_report_journal').with_context(
            landscape=True).report_action(self, data=data)
