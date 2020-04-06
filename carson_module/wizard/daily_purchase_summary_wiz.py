# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError

class dailyPurchaseSummary(models.TransientModel):
    _name = 'daily.purchase.summary'
    _description = 'Daily Purchase Summary'

    compute_at_date = fields.Selection([
        (0, 'Current Date'),
        (1, 'At a Specific Date Range')
    ], string="Compute", help="Choose to analyze the current inventory or from a specific date in the past.")
    datefrom = fields.Date('Date From', default=fields.Date.today())
    dateto = fields.Date('Date to', default=fields.Date.today())

    def open_table(self):
        
        self.ensure_one()


        if self.dateto < self.datefrom:
            raise UserError(_('Date To is less than Date From.'))
        
        carson_rof_model = self.env['carson.rof']
        caron_rof_items_model = self.env['carson.rof.items']
        item_ids = []
        

        if self.compute_at_date == 0:
            carson_rof_obj = carson_rof_model.sudo().search([('requested_date', '=', fields.Date.today()),('rof_state','=', 'inprogress')])
        else:
            carson_rof_obj = carson_rof_model.sudo().search([('requested_date', '>=', self.datefrom),('requested_date', '<=', self.dateto),('rof_state','=', 'inprogress')])
        
        if carson_rof_obj:            
            caron_rof_items_obj = caron_rof_items_model.search([('rof_item_id','in', carson_rof_obj.ids),('state','=', 'purchase')])
            if caron_rof_items_obj:
                item_ids = caron_rof_items_obj.ids



        if len(item_ids) > 0:
            tree_view_id = self.env.ref('carson_module.view_tree_rof_items_dps').id
            action = {
                'type': 'ir.actions.act_window',
                'views': [(tree_view_id, 'tree'), (False, 'form')],
                'view_mode': 'tree',
                'view_type': 'form',
                'name': _('Daily Purchase Summary'),
                'res_model': 'carson.rof.items',
                'domain': [('id', 'in', item_ids)],
                'context': {},
            }
            return action
        else:
            raise UserError(_('No Record/s Found.'))