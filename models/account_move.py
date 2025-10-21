# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _

class AccountMove(models.Model):
    _inherit = "account.move"
    
    advance_expense_id = fields.Many2one('advance.expense', string='Advance Expense', domain="[('company_id', '=', company_id)]", ondelete='restrict')

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends('balance', 'move_id.is_storno')
    def _compute_debit_credit(self):
        for line in self:
            ##manage credit/debit via advance_expense_id because
            ##not use default JE 
            advance_expense_id = False
            credit = line.credit
            debit = line.debit
            if line.balance == 0 and credit or debit:
                advance_expense_id = True
            if credit == 0 and debit == 0 and line.balance == 0:
                advance_expense_id = False
            if advance_expense_id:
                line.credit = credit
                line.debit = debit
            else:
                if not line.is_storno:
                    line.debit = line.balance if line.balance > 0.0 else 0.0
                    line.credit = -line.balance if line.balance < 0.0 else 0.0
                else:
                    line.debit = line.balance if line.balance < 0.0 else 0.0
                    line.credit = -line.balance if line.balance > 0.0 else 0.0

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
