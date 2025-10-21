# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    
    reminder_days = fields.Integer('Reminder for retirement',default=10)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            reminder_days = self.env['ir.config_parameter'].sudo().get_param('reminder_days'),
        )
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('reminder_days', self.reminder_days)

    def action_view_due_date_adv_payment_to_employee_mail_tmpl(self):
        action = self.env["ir.actions.actions"]._for_xml_id("mail.action_email_template_tree_all")
        tmpl_id = self.env.ref('hr_expense_advance_omax.due_date_adv_payment_to_employee_mail_template')
        if tmpl_id:
            form_view = [(self.env.ref('mail.email_template_form').id, 'form')]
            action['views'] = form_view
            action['res_id'] = tmpl_id.id
            return action
        return False

    def action_view_due_date_adv_payment_to_approver_mail_tmpl(self):
        action = self.env["ir.actions.actions"]._for_xml_id("mail.action_email_template_tree_all")
        tmpl_id = self.env.ref('hr_expense_advance_omax.due_date_adv_payment_to_approver_mail_template')
        if tmpl_id:
            form_view = [(self.env.ref('mail.email_template_form').id, 'form')]
            action['views'] = form_view
            action['res_id'] = tmpl_id.id
            return action
        return False

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
