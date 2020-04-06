# -*- coding: utf-8 -*-
# Copyright YEAR(S), AUTHOR(S)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models

class CarsonRofGeneratePurchase(models.TransientModel):
	_name = 'carson.rof.generate.purchase'
	_description = 'Wizard to generate purchase from Requisition Order'

	def _default_rof(self):
		return self.env['carson.rof'].browse(self._context.get('active_id'))

	def _default_rof_items(self):
		rof_id = self.env['carson.rof'].browse(self._context.get('active_id'))
		rof_items = self.env['carson.rof.items'].search([('rof_item_id','=',rof_id.id),('state','in',['purchase','partial'])])
		return rof_items

	rof_id = fields.Many2one('carson.rof', string='Requisition Order', default=_default_rof)
	item_ids = fields.Many2many('carson.rof.items', string='Items', default=_default_rof_items)
	partner_id = fields.Many2one('res.partner', string='Vendor', required=True)
	is_cash_transaction = fields.Boolean(string='Cash Transaction')
	
	def apply(self):
		# self.purchase_id.invoice_ids |= self.invoice_ids
		# return False
		rof_id = self.rof_id.id
		if self.is_cash_transaction == True:
			rof_id = False

		lines = []
		for item in self.item_ids:
			lines.append((0, 0, {
				'product_id': item.product_id.id,
				'name': item.product_id.display_name,
				'date_planned': fields.Datetime.now(),
				'product_qty': item.purchase_qty,
				'product_uom': item.product_id.uom_id.id,
				'price_unit': 0,
				'rof_item_id':item.id,
				'rof_id': self.rof_id.id,
			}))
		purchase_order = self.env['purchase.order']
		purchase_order.create({
			'partner_id': self.partner_id.id,
			'date_planned': fields.Datetime.now(),
			'rof_id': rof_id,
			'rof_ids': [(4, self.rof_id.id)],
			'order_line': lines,
			'is_po_paid_by_cash': self.is_cash_transaction,
		})