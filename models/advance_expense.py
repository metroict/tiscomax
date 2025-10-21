# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError,UserError


class AdvanceExpense(models.Model):
    _name = 'advance.expense'
    _description = "Advance Expense Request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Advance Expense Request', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
        ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
    employee_id = fields.Many2one('hr.employee', string="Employee", tracking=True, required=True, default=lambda self: self.env.user.employee_id, domain=lambda self: [('id', '=', self.env.user.employee_id.id)])
    department_id = fields.Many2one('hr.department', string="Department", related="employee_id.department_id", readonly=True)
    job_id = fields.Many2one('hr.job', string="Job Position", related="employee_id.job_id", readonly=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.company.currency_id)
    
    requested_date = fields.Date(string="Requested Date",required=True, default=lambda self: fields.Date.context_today(self))
    product_id = fields.Many2one('product.product', string='Expense', domain="[('can_be_expensed', '=', True),'|', ('company_id', '=', False), ('company_id', '=', company_id)]",required=True)
    requested_amount = fields.Monetary('Requested Amount', currency_field='currency_id', tracking=True)
    user_id = fields.Many2one('res.users', copy=False, tracking=True, required=True, string='Requested User',default=lambda self: self.env.user)
    
    submitted_date = fields.Date(string="Submitted Date", readonly=True)
    approved_date = fields.Date(string="Approved Date", readonly=True)
    paid_date = fields.Date(string="Paid Date", readonly=True)
    rejected_date = fields.Date(string="Rejected On", readonly=True)
    rejected_reason = fields.Text("Rejected Reason", readonly=True)
    
    submitted_by_id = fields.Many2one('res.users', copy=False, tracking=True, readonly=True, string='Submitted By')
    approved_by_id = fields.Many2one('res.users', copy=False, tracking=True, readonly=True, string='Approved By')
    paid_by_id = fields.Many2one('res.users', copy=False, tracking=True, readonly=True, string='Paid By')
    rejected_by_id = fields.Many2one('res.users', copy=False, tracking=True, readonly=True, string='Rejected By')
    
    employee_account_id = fields.Many2one('account.account', string='Employee Account', domain="[('company_id', '=', company_id)]", help="An Employee Account")
    cash_bank_account_id = fields.Many2one('account.account', string='Cash/Bank Account', domain="[('company_id', '=', company_id)]", help="A Cash/Bank Account")
    account_move_id = fields.Many2one('account.move', string='Journal Entry', ondelete='restrict', copy=False, readonly=True)
    account_journal_id = fields.Many2one('account.journal', string='Journal', domain="[('company_id', '=', company_id)]")
    remarks = fields.Text(string="Remarks")
    expense_approver_id = fields.Many2one('res.users', copy=False, tracking=True, readonly=True, string='Expense Approver', related='employee_id.expense_manager_id')
    expense_id = fields.Many2one('hr.expense', copy=False, string= 'Expense Ref', readonly=True)
    expsense_state = fields.Selection(related='expense_id.state',string='Expense Status')
    due_date = fields.Date('Due date',copy=False,help='Before this date the expense must be submitted agianst this advance')
    retired = fields.Boolean('Retired', compute="_cal_retired")
    note = fields.Text('Notes')
    is_mass_expense = fields.Boolean('Mass Expense', readonly=True)
    
    @api.depends('expsense_state')
    def _cal_retired(self):
        for obj in self:
            if obj.expsense_state == 'done':
                obj.retired = True
            else:
                obj.retired = False

    @api.model
    def default_get(self, fields):
        employee = self.env['hr.employee'].search([('user_id','=',self.env.user.id), ('allowed_advance_retirment','=',False)], limit=1)
        bypass_validation = False
        if 'is_mass_advance_line' in list(self._context.keys()):
            if self._context.get('is_mass_advance_line'):
                bypass_validation = True
        if employee and not bypass_validation:
            existing_ids = self.search([('employee_id','=',employee.id)])
            for prev_rec in existing_ids:
                expense = self.env["hr.expense"].search([('advance_expense_id','=',prev_rec.id), ('state','=','done')])
                if not expense:
                    raise ValidationError("You can't submit new record untill you submit expense against [ %s ] "%(prev_rec.name))
        return super(AdvanceExpense, self).default_get(fields)
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('advance.expense') or _('New')
        res = super(AdvanceExpense, self).create(vals)
        return res
        
    @api.onchange('product_id')
    def _onchange_product_id(self):
        standard_price = 0
        if self.product_id:
            standard_price = self.product_id.standard_price
        self.requested_amount = standard_price
        
    def action_submit(self):
        today = fields.Date.today()
        self.write({'state': 'submitted', 'submitted_date': today, 'submitted_by_id': self.env.user.id})
        hof_email_template = self.env.ref("hr_expense_advance_omax.submit_adv_expense_to_approver_mail_template")
        hof_email_template.send_mail(self.id, force_send=False)#force_send=True
        return True
        
    def action_approve(self):
        today = fields.Date.today()
        team_approver = self.env.user.has_group('hr_expense.group_hr_expense_team_approver')
        all_approver = self.env.user.has_group('hr_expense.group_hr_expense_user')
        if not all_approver and self.expense_approver_id and not self.env.is_superuser():
            if self.env.user.has_group('hr_expense.group_hr_expense_team_approver') and self.env.user.id != self.expense_approver_id.id:
                raise ValidationError(_("You can not Reject this expense!"))
                
        self.write({'state': 'approved', 'approved_date': today, 'approved_by_id': self.env.user.id})
        expn_manager_email_template = self.env.ref("hr_expense_advance_omax.expense_manager_get_approve_adv_expn_mail_template")
        expn_manager_email_template.send_mail(self.id, force_send=False)#force_send=True
        return True
    
    def action_reset_draft(self):
        self.write({'state': 'draft'})
        return True
        
    def action_pay(self):
        if not self.employee_account_id:
            raise ValidationError(_("Kidnly configure the Employee Account!"))
        if not self.cash_bank_account_id:
            raise ValidationError(_("Kidnly configure the Cash/Bank Account!"))
        if not self.account_journal_id:
            raise ValidationError(_("Kidnly configure the Journal!"))

        today = fields.Date.today()
        self.write({'state': 'paid', 'paid_date': today, 'paid_by_id': self.env.user.id})
        debit_line ={
            'name': str(self.name)+' - Debit',
            'account_id': self.employee_account_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.employee_id.user_id.partner_id.id,
            'debit': self.requested_amount,
            'credit': 0,
        }
        credit_line ={
            'name': str(self.name)+' - Credit',
            'account_id': self.cash_bank_account_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.employee_id.user_id.partner_id.id,
            'debit': 0,
            'credit': self.requested_amount > 0 and self.company_id.currency_id.round(self.requested_amount) or 0,
        }
        account_move = self.env['account.move'].create({
            'currency_id': self.currency_id.id,
            'date': today,
            'journal_id': self.account_journal_id.id,
            'move_type': 'entry',
            'advance_expense_id' : self.id,
            'partner_id': self.employee_id.user_id.partner_id.id,
            'ref': str(self.name),
            'line_ids': [
                (0, 0, debit_line),
                (0, 0, credit_line),
            ],
        })
        if account_move:
            account_move.action_post()
            self.account_move_id = account_move.id
        return True

    def action_create_view_hr_expense(self):
        if self.submitted_by_id.id != self.env.user.id:
            raise ValidationError(_("Only '%s' can submit expense !!!")% (self.submitted_by_id.name))
        today = fields.Date.today()
        ctx = dict(self.env.context)
        hr_expenses = self.env["hr.expense"].search([('advance_expense_id','=',self.id)])
        if hr_expenses:
            ctx.update({'create':False,})
            action = self.env["ir.actions.actions"]._for_xml_id("hr_expense.hr_expense_actions_my_all")
            action['domain'] = [('id', 'in', hr_expenses.ids)]
            action['context'] = ctx
        else:
            ctx.update({
                'default_product_id': self.product_id.id,
                'default_name': self.product_id.name,
                'default_quantity': 1,
                'default_employee_id': self.employee_id.id,
                'default_date': today,
                'default_advance_expense_id' : self.id,
                'default_reference' : self.name,
                'default_total_amount_currency' : self.requested_amount,
                'default_product_uom_id' : self.product_id.uom_id.id,
            })
            form_view = [(self.env.ref("hr_expense.hr_expense_view_form").id, "form")]
            action = {
                "name": _("Policies"),
                "type": "ir.actions.act_window",
                "res_model": "hr.expense",
                "target": "current",
                "context": ctx,
            }
            action["views"] = form_view
        return action

    ###email template fun() below
    def get_advance_expense_approver_email(self):
        email_to = ''
        if self.expense_approver_id:
            if self.expense_approver_id.partner_id.email:
                email_to = self.expense_approver_id.partner_id.email
        else:
            Group = self.env.ref('hr_expense.group_hr_expense_team_approver')
            email_to_list = []
            if Group:
                for user in Group.users:
                    if user.partner_id.email and user.partner_id.email not in email_to_list:
                        email_to_list.append(user.partner_id.email)
            for email in email_to_list:
                email_to += email +','
        return email_to

    def get_portal_url(self):
        self._cr.execute('select value from ir_config_parameter where key=%s',('web.base.url',))
        server = str(self._cr.fetchone()[0])
        url = server+'/web#id=%s&view_type=%s&model=%s'%(self.id,'form','advance.expense')
        return url

    def get_expense_manager_email(self):
        Group = self.env.ref('hr_expense.group_hr_expense_manager')
        email_to_list = []
        if Group:
            for user in Group.users:
                if user.partner_id.email and user.partner_id.email not in email_to_list:
                    email_to_list.append(user.partner_id.email)
        email_to = ''
        for email in email_to_list:
            email_to += email +','
        return email_to

    def get_rejected_reason(self):
        reason = ''
        rec = self.env["adv.exp.request.reject"].search([], limit=1, order='id desc')
        if rec:
            reason = rec.rejected_reason
        return reason

    #schedular method
    def due_payment_reminder_mail_send(self):
        reminder_days = self.env['ir.config_parameter'].sudo().get_param('reminder_days')
        if int(reminder_days):
            not_paid_adv_expense = self.env["advance.expense"].search([('expsense_state','!=','done'), ('due_date','!=',False)])
            today = fields.Date.today()
            for adv_expense in not_paid_adv_expense:
                diff_days = today - adv_expense.due_date
                if diff_days.days > 0 and diff_days.days == int(reminder_days):
                    #for employee
                    due_date_payment_to_employee_tmpl_id = self.env.ref("hr_expense_advance_omax.due_date_adv_payment_to_employee_mail_template")
                    due_date_payment_to_employee_tmpl_id.send_mail(adv_expense.id, force_send=False)#force_send=True
                    #for approver
                    due_date_payment_to_approver_tmpl_id = self.env.ref("hr_expense_advance_omax.due_date_adv_payment_to_approver_mail_template")
                    due_date_payment_to_approver_tmpl_id.send_mail(adv_expense.id, force_send=False)#force_send=True
        return True

    def get_job_id(self, user_id):
        if user_id:
            employee = self.env["hr.employee"].search([('user_id','=',user_id.id)], limit=1)
            if employee:
                if employee.job_id:
                    return employee.job_id.name
        return False
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
