# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError

class ROFCLASS(models.TransientModel):
    _name= "carson.rof_wizard_purchase_order"
    carson_project_id = fields.Many2one('carson.projects', string='Project')
    rofclasslines = fields.One2many('carson.rof_wizard_lines', 'rof_id', string='Requests')


class RofClassLines(models.TransientModel):
    _name= "carson.rof_wizard_lines"
    rof_id = fields.Many2one('carson.rof_wizard_purchase_order', string='ROF Wiz')  
    product_id = fields.Many2one('product.product', string='Item')
    quantity_requested = fields.Float(string='Quantity')
    uom_id = fields.Many2one('product.uom', string='UOM')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.uom_id = self.product_id.uom_id.id




