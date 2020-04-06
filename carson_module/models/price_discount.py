from odoo import models, fields, api, exceptions, _

class PriceDiscount(models.Model):
    _inherit = 'purchase.order.line'

    price_dropdown_notes = fields.Text(string="Notes")#fields.Selection([
        #('U', 'U'),
        #('D', 'D'),
        #('P', 'P'),
        #('N', 'N')], string='Notes')
