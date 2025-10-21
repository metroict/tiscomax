# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models ,SUPERUSER_ID, _
from odoo.exceptions import ValidationError


class AdvExpReject(models.TransientModel):

    _name = 'adv.exp.request.reject'
    _description = 'Advance Expense Request Reject'

    rejected_reason = fields.Text('Reason', required=True)
    
    def action_reject_reson(self):
        res_ids = self._context.get("active_id")
        reqiest_id = self.env["advance.expense"].browse(res_ids)
        team_approver = self.env.user.has_group('hr_expense.group_hr_expense_team_approver')
        all_approver = self.env.user.has_group('hr_expense.group_hr_expense_user')
        if not all_approver and reqiest_id.expense_approver_id and not self.env.is_superuser():
            if self.env.user.has_group('hr_expense.group_hr_expense_team_approver') and self.env.user.id != reqiest_id.expense_approver_id.id:
                raise ValidationError(_("You can not Reject this expense!"))
        
        today = fields.Date.today()
        vals = {
            'rejected_reason': self.rejected_reason, 
            'rejected_date': today,
            'rejected_by_id': self.env.user.id
        }
        vals.update({'state': 'rejected'})
        reqiest_id.sudo().write(vals)
        #reqiest_id.
        reject_expense_email_tmpl = self.env.ref("hr_expense_advance_omax.reject_expense_mail_template")
        reject_expense_email_tmpl.send_mail(reqiest_id.id, force_send=False)#force_send=True
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
