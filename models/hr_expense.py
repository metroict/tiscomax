# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError,UserError

class HrExpense(models.Model):
    _inherit = "hr.expense"
    
    repaying_options = fields.Selection([
        ('repaying_in_cash', 'Repaying the excess through cash'),
        ('repaying_in_salary', 'Repaying by deducting from salary'),
        ], string='Repaying Options')#default='employee',
    advance_expense_id = fields.Many2one('advance.expense', copy=False, readonly=True, string='Advance Expense')
    repaying_journal_entry = fields.Many2one('account.move', string='Repaying Journal Entry', domain="[('company_id', '=', company_id)]", copy=False, readonly=True,)

    def action_submit_expenses(self):
        for rec in self:
            if rec.advance_expense_id:
                if rec.total_amount_currency < rec.advance_expense_id.requested_amount and not rec.repaying_options:
                    raise ValidationError(_("Kidnly configure the Repaying Options!"))
        return super(HrExpense, self).action_submit_expenses()
    
    @api.model_create_multi
    def create(self, vals):
        adv_exp_id = self._context.get('default_advance_expense_id')
        res = super(HrExpense,self).create(vals)
        if adv_exp_id:
            self._cr.execute("update advance_expense set expense_id=%s where id=%s",(res.id,adv_exp_id))
            self._cr.commit()
        return res


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def action_sheet_move_create(self):
        custom_code = False
        if any(line.advance_expense_id for line in self.expense_line_ids):
            custom_code = True
        if not custom_code:
            return super(HrExpenseSheet, self).action_sheet_move_create()
        
        today = fields.Date.today()
        submisson_accounting_lines = []
        if custom_code:
            for line in self.expense_line_ids:
                #Create submission or accounting JE lines
                ##expense a/c warning
                if not line.product_id.property_account_expense_id:
                    raise ValidationError(_("Kindly configure Expense Account in product !!!"))
                advance_expense_id = line.advance_expense_id#adv expense

                if advance_expense_id:
                    credit_account = advance_expense_id.employee_account_id.id
                    debit_account = line.product_id.property_account_expense_id.id
                else:
                    if not line.account_id:
                        raise ValidationError(_("Kindly configure Cash/Bank Account in Expense !!!"))
                    credit_account = line.account_id.id
                    debit_account = line.product_id.property_account_expense_id.id
                
                credit_line ={
                    'name': str(self.name)+' - Credit',
                    'account_id': credit_account,
                    'currency_id': line.currency_id.id,
                    'partner_id': line.employee_id.user_id.partner_id.id,
                    'debit': 0,
                    'credit': line.total_amount or 0,
                    'balance': -line.total_amount,
                }
                debit_line ={
                    'name': str(self.name)+' - Debit',
                    'account_id': debit_account,
                    'currency_id': line.currency_id.id,
                    'partner_id': line.employee_id.user_id.partner_id.id,
                    'debit': line.total_amount or 0,
                    'credit': 0,
                    'balance': line.total_amount,
                }
                submisson_accounting_lines.append((0, 0, debit_line))
                submisson_accounting_lines.append((0, 0, credit_line))

            #Create submission or accounting JE
            if submisson_accounting_lines:
                account_move = self.env['account.move'].create({
                    'currency_id': self.currency_id.id,
                    'date': today,
                    'journal_id': self.journal_id.id,
                    'move_type': 'entry',
                    'partner_id': self.employee_id.user_id.partner_id.id,
                    'ref': self.name,
                    'line_ids': submisson_accounting_lines,
                })

                if account_move:
                    account_move.action_post()
                    account_move.payment_state = 'paid'
                    self.account_move_ids = [(6,0,[account_move.id])]#account_move.id
                self.expense_line_ids.write({'state': 'done'})#expn done

        #repaying JE lines
        expense_lines = self.expense_line_ids.filtered(lambda x: x.repaying_options=='repaying_in_cash' and x.advance_expense_id)#hr expense records
        if expense_lines and custom_code:
            repaying_lines = []
            repaying_expn_ids = []
            for expense_line in expense_lines:
                advance_expense_id = expense_line.advance_expense_id#adv expense
                adv_expense_amount = advance_expense_id.requested_amount #adv exp amt
                ##expense a/c warning
                if not expense_line.product_id.property_account_expense_id:
                    raise ValidationError(_("Kindly configure Expense Account in product !!!"))
                if expense_line.total_amount < adv_expense_amount:
                    remaining_amt = adv_expense_amount - expense_line.total_amount
                    #Create Repaying JE
                    credit_line ={
                        'name': str(advance_expense_id.name)+' - Credit',
                        'account_id': advance_expense_id.employee_account_id.id,
                        'currency_id': advance_expense_id.currency_id.id,
                        'partner_id': advance_expense_id.employee_id.user_id.partner_id.id,
                        'debit': 0,
                        'credit': remaining_amt > 0 and advance_expense_id.company_id.currency_id.round(remaining_amt) or 0,
                    }
                    debit_line ={
                        'name': str(advance_expense_id.name)+' - Debit',
                        'account_id': advance_expense_id.cash_bank_account_id.id,
                        'currency_id': advance_expense_id.currency_id.id,
                        'partner_id': advance_expense_id.employee_id.user_id.partner_id.id,
                        'debit': remaining_amt,
                        'credit': 0,
                    }
                    repaying_lines.append((0, 0, debit_line))
                    repaying_lines.append((0, 0, credit_line))
                    repaying_expn_ids.append(expense_line)

            #repaying JE lines
            if repaying_lines:
                account_move = self.env['account.move'].create({
                    'currency_id': advance_expense_id.currency_id.id,
                    'date': today,
                    'journal_id': advance_expense_id.account_journal_id.id,
                    'move_type': 'entry',
                    'advance_expense_id' : advance_expense_id.id,
                    'partner_id': advance_expense_id.employee_id.user_id.partner_id.id,
                    'ref': 'Repaying '+ str(advance_expense_id.name),
                    'line_ids': repaying_lines,
                })
                if account_move:
                    account_move.action_post()
                    for expn_id in repaying_expn_ids:
                        expn_id.repaying_journal_entry = account_move.id

        if custom_code:
            self.set_to_paid()#expn sheet done

    def set_to_paid(self):
        self.write({'state': 'done'})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
