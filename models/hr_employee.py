# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    allowed_advance_retirment = fields.Boolean(string='Allowed Create Advance Even Retirement is Pending')
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
