# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models ,SUPERUSER_ID, _
import time
from datetime import datetime,timedelta
import xlrd
import tempfile
import io
import base64
import binascii
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError ,ValidationError
import xlwt

class DownloadAdvExpReport(models.TransientModel):

    _name = 'download.adv.exp.report'
    _description = 'Download Advanced Expense Report'

    excel_file = fields.Binary('Excel Report')
    file_name = fields.Char('Report File Name', readonly=True)

class AdvExpenseReportWizard(models.TransientModel):

    _name = 'adv.expense.report.wizard'
    _description = 'Advanced Expense Report Wizard'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    payment_mode = fields.Selection([('Cash', 'Cash'),('Bank', 'Bank')], string="Payment Mode")
    state = fields.Selection([('draft', 'Draft'),('submitted', 'Submitted'),('approved', 'Approved'),('paid', 'Paid'),('rejected', 'Rejected')], string="Status")
    department_id = fields.Many2one('hr.department', string="Department")
    job_id = fields.Many2one('hr.job', string="Job Position")
    employee_ids = fields.Many2many(comodel_name='hr.employee',string="Employee")
    product_ids = fields.Many2many(comodel_name='product.product',string="Expenses")
    retired = fields.Boolean('Retired')

    def action_download_excel_report(self):
        workbook = xlwt.Workbook()
        style = xlwt.XFStyle()

        style_center = xlwt.easyxf('align:vertical center; font:bold on;')
        style_title = xlwt.easyxf('font:height 300, bold on; align:horizontal center, vertical center; pattern: pattern solid, fore_color white; border: top thin, bottom thin, right thin, left thin; ')

        font = xlwt.Font()
        font.name = 'Times New Roman'
        font.bold = True
        font.height = 250
        style.font = font
        worksheet = workbook.add_sheet('Advanced Expense Report',cell_overwrite_ok = True)
        date_start = str(self.start_date.day) +'-'+ str(self.start_date.month) +'-'+ str(self.start_date.year)
        date_end = str(self.end_date.day) +'-'+ str(self.end_date.month) +'-'+ str(self.end_date.year)
        title = 'Advanced Expense Report From ' + str(date_start) +' To ' + str(date_end) 
        worksheet.write_merge(0,1,0,7,title,style_title)

        domain = []
        domain.append(('requested_date', '>=', self.start_date))
        domain.append(('requested_date', '<=', self.end_date))

        worksheet.col(0).width = 5000
        worksheet.col(1).width = 5000
        worksheet.write(2, 0, 'Department')
        if self.department_id:
            worksheet.write(2, 1, self.department_id.name)
            domain.append(('department_id', '=', self.department_id.id))
        else:
            worksheet.write(2, 1, 'All')
        worksheet.write(3, 0, 'Job Position')
        if self.job_id:
            worksheet.write(3, 1, self.job_id.name)
            domain.append(('job_id', '=', self.job_id.id))
        else:
            worksheet.write(3, 1, 'All')

        worksheet.write(2, 4, 'Status')
        if self.state:
            worksheet.write(2, 5, self.state)
            domain.append(('state', '=', self.state))
        else:
            worksheet.write(2, 5, 'All')

        emp_ids_list = []
        for employee_id in self.employee_ids:
            emp_ids_list.append(employee_id.id)

        product_ids_list = []
        for product_id in self.product_ids:
            product_ids_list.append(product_id.id)

        if self.employee_ids:
            domain.append(('employee_id', 'in', emp_ids_list))
        if self.product_ids:
            domain.append(('product_id', 'in', product_ids_list))

        worksheet.write(5, 0, 'Ref#', style_center)
        worksheet.write(5, 1, 'Employee', style_center)
        worksheet.write(5, 2, 'Department', style_center)
        worksheet.col(2).width = 5000
        worksheet.write(5, 3, 'Job Position', style_center)
        worksheet.col(3).width = 5000
        worksheet.write(5, 4, 'Requested Date', style_center)
        worksheet.col(4).width = 5000
        worksheet.write(5, 5, 'Requested User', style_center)
        worksheet.col(5).width = 5000
        worksheet.write(5, 6, 'Expense', style_center)
        worksheet.col(6).width = 5000
        worksheet.write(5, 7, 'Amount', style_center)
        worksheet.col(7).width = 4000
        worksheet.write(5, 8, 'Submitted Date', style_center)
        worksheet.col(8).width = 6500
        worksheet.write(5, 9, 'Submitted By', style_center)
        worksheet.col(9).width = 6500
        worksheet.write(5, 10, 'Approved Date', style_center)
        worksheet.col(10).width = 6500
        worksheet.write(5, 11, 'Approved By', style_center)
        worksheet.col(11).width = 6500
        worksheet.write(5, 12, 'Paid Date', style_center)
        worksheet.write(5, 13, 'Paid By', style_center)
        worksheet.col(13).width = 6500
        worksheet.write(5, 14, 'Status', style_center)
        worksheet.write(5, 15, 'Company', style_center)
        worksheet.col(15).width = 6500

        adv_exp_ids = self.env['advance.expense'].sudo().search(domain)
        if self.retired:
            adv_exp_ids = adv_exp_ids.filtered(lambda a: a.retired)
        row = 6
        for adv in adv_exp_ids:
            worksheet.write(row, 0, adv.name)
            worksheet.write(row, 1, adv.employee_id.name)
            worksheet.write(row, 2, adv.department_id.name)
            worksheet.write(row, 3, adv.job_id.name)
            worksheet.write(row, 4, str(adv.requested_date))
            worksheet.write(row, 5, adv.user_id.name)
            worksheet.write(row, 6, adv.product_id.name)
            worksheet.write(row, 7, adv.requested_amount)
            if adv.submitted_by_id:
                worksheet.write(row, 8, str(adv.submitted_date))
                worksheet.write(row, 9, adv.submitted_by_id.name)
            if adv.approved_by_id:
                worksheet.write(row, 10, str(adv.approved_date))
                worksheet.write(row, 11, adv.approved_by_id.name)
            if adv.paid_by_id:
                worksheet.write(row, 12, str(adv.paid_date))
                worksheet.write(row, 13, adv.paid_by_id.name)
            worksheet.write(row, 14, adv.state)
            worksheet.write(row, 15, adv.company_id.name)
            row += 1

        download_filename = 'Advanced Expense Report'+'.xls'
        filename = download_filename
        workbook.save('/tmp/'+filename)
        file = open('/tmp/'+filename, "rb")
        file_data = file.read()
        #out = base64.encodestring(file_data)
        out = base64.encodebytes(file_data)#python3.8 support
        export_id = self.env['download.adv.exp.report'].sudo().create({'excel_file': out, 'file_name': filename})
        res = {
            'name': 'Download Advanced Expense Report',
            'view_mode': 'form', 
            'res_id': export_id.id, 
            'res_model': 'download.adv.exp.report',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self._context, 
            'target': 'new',
        }
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
