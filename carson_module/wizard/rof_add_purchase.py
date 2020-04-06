# -*- coding: utf-8 -*-
# Copyright YEAR(S), AUTHOR(S)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, api

import logging
_logger = logging.getLogger('models')

class CarsonRofAddPurchase(models.TransientModel):
	_name = 'carson.rof.add.purchase'
	_description = 'Wizard to add Requisition Order items to exiting Purchase Order'

	def _default_rof(self):
		return self.env['carson.rof'].browse(self._context.get('active_id'))

	def _default_project(self):
		rof_id = self.env['carson.rof'].browse(self._context.get('active_id'))
		return rof_id.carson_project_id

	def _default_rof_items(self):
		rof_id = self.env['carson.rof'].browse(self._context.get('active_id'))
		rof_items = self.env['carson.rof.items'].search([('rof_item_id','=',rof_id.id),('state','in',['purchase','partial'])])
		items = []
		for item in rof_items:
			if not item.ordered_qty == item.reserved_qty and not item.reserved_qty > item.ordered_qty:
				items.append(item.id)
		return items

	rof_id = fields.Many2one('carson.rof', string='Requisition Order', default=_default_rof)
	carson_project_id =  fields.Many2one('carson.projects',string='Project', default=_default_project)
	item_ids = fields.Many2many('carson.rof.items', string='Items', default=_default_rof_items)

	is_cash_transaction= fields.Boolean(string='Cash Transaction')
	purchase_id = fields.Many2one('purchase.order', string='Purchase Order')
	purchase_cash_id = fields.Many2one('purchase.order', string='Purchase Order')

	def apply(self):
		order_lines = []

		purchase_id = self.purchase_id
		if not purchase_id:
			purchase_id = self.purchase_cash_id

		for item in self.item_ids:
			product_uom_qty = 0
			if item.state == 'partial':
				product_uom_qty = item.purchase_qty
			else:
				product_uom_qty = item.ordered_qty
				if item.reserved_qty != 0:
					product_uom_qty = item.ordered_qty - item.reserved_qty

			purchase_line = self.env['purchase.order.line'].create({
				'product_id': item.product_id.id,
				'name': item.product_id.display_name,
				'product_qty': product_uom_qty,
				'product_uom': item.product_uom.id,
				'date_planned': fields.Datetime.now(),
				'price_unit': item.product_id.lst_price,
				'rof_item_id': item.id,
				'rof_id': self.rof_id.id,
				'order_id': purchase_id.id,
			})
 
			order_lines.append(purchase_line.id)
			
		purchase_order = purchase_id.write({
			'rof_ids': [(4, self.rof_id.id)]
		})

		self.rof_id.sudo().action_check_availability()