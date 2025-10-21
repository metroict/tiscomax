# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models ,SUPERUSER_ID, _


class MassAdvanceExpense(models.TransientModel):

    _name = 'mass.advance.expense'
    _description = 'Mass Advace Expense Creation'
    
    mass_advance_lines = fields.One2many('mass.advance.expense.lines','mass_wiz_id')
    
    def mass_advance_expense(self):
        mass_env = self.env['advance.expense']
        for line in self.mass_advance_lines:
            vals = {
             'employee_id':line.employee_id.id,
             'product_id':line.product_id.id,
             'requested_amount':line.amount,
             'note':line.note,
             'is_mass_expense':True,
            }
            #advance_expense = mass_env.create(vals)
            advance_expense = mass_env.with_context(is_mass_advance_line=True).create(vals)
        views = [(self.env.ref("hr_expense_advance_omax.advance_expense_request_tree_view").id, "tree"),
                (self.env.ref("hr_expense_advance_omax.advance_expense_request_form_view").id, "form")]
        action = {
            "name": _("Advance Expense Request"),
            "type": "ir.actions.act_window",
            "res_model": "advance.expense",
            "target": "current",
            "views": views,
        }
        return action
    
class MassAdvanceLines(models.TransientModel):

    _name = 'mass.advance.expense.lines'
    _description = 'Mass Advace Expense Lines'
    
    mass_wiz_id = fields.Many2one('mass.advance.expense')
    employee_id = fields.Many2one('hr.employee',string='Employee',required=True)
    product_id = fields.Many2one('product.product',string='Expense',required=True, 
                  domain="[('can_be_expensed', '=', True)]",)
    note = fields.Char('Notes')
    amount = fields.Float('Amount',required=True)
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
