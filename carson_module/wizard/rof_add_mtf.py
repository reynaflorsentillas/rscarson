# -*- coding: utf-8 -*-
# Copyright YEAR(S), AUTHOR(S)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, api

import logging
_logger = logging.getLogger('models')

class CarsonRofAddMTF(models.TransientModel):
	_name = 'carson.rof.add.mtf'
	_description = 'Wizard to add Requisition Order items to exiting MTF'

	def _default_rof(self):
		return self.env['carson.rof'].browse(self._context.get('active_id'))

	def _default_project(self):
		rof_id = self.env['carson.rof'].browse(self._context.get('active_id'))
		return rof_id.carson_project_id

	def _default_location_id(self):
		rof_id = self.env['carson.rof'].browse(self._context.get('active_id'))
		return rof_id.location_id

	def _default_rof_items(self):
		rof_id = self.env['carson.rof'].browse(self._context.get('active_id'))
		rof_items = self.env['carson.rof.items'].search([('rof_item_id','=',rof_id.id),('location_id','=',rof_id.location_id.id),('state','in',['available','partial'])])
		items = []
		for item in rof_items:
			if not item.ordered_qty == item.reserved_qty and not item.reserved_qty > item.ordered_qty:
				items.append(item.id)
		return items

	rof_id = fields.Many2one('carson.rof', string='Requisition Order', default=_default_rof)
	carson_project_id =  fields.Many2one('carson.projects',string='Project', default=_default_project)
	item_ids = fields.Many2many('carson.rof.items', string='Items', default=_default_rof_items)

	location_id = fields.Many2one('stock.location', string='Source Location', required=True, default=_default_location_id)
	location_dest_id = fields.Many2one('stock.location', string='Destination Location', required=True)

	mtf_id = fields.Many2one('stock.picking', string='Material Transmittal', required=True)

	@api.onchange('location_id')
	def _get_rof_items(self):
		rof_items = self.env['carson.rof.items'].search([('rof_item_id','=',self.rof_id.id),('location_id','=',self.location_id.id),('state','in',['available','partial'])])
		items = []
		for item in rof_items:
			if not item.ordered_qty == item.reserved_qty and not item.reserved_qty > item.ordered_qty:
				items.append(item.id)
		self.item_ids = items

	def apply(self):
		move_lines = []
		for x in self.item_ids:
			product_uom_qty = 0
			if x.state == 'partial':
				product_uom_qty = x.available_qty
			else:
				product_uom_qty = x.ordered_qty
				if x.reserved_qty != 0:
					product_uom_qty = x.ordered_qty - x.reserved_qty

			stock_move = self.env['stock.move'].create({
				'name':x.name,
				'product_id':x.product_id.id,
				'product_uom_qty':product_uom_qty,
				'product_uom':x.product_uom.id,
				'note':x.note,
				'picking_type_id': self.rof_id.warehouse_id.int_type_id.id,
				'location_id': self.location_id.id,
				'location_dest_id': self.location_dest_id.id,
				'rof_item_id':x.id,
				'rof_id': self.rof_id
			})

			stock_move._action_confirm()
			stock_move._action_assign() 
			move_lines.append(stock_move.id)
			
		stock_picking = self.mtf_id.write({
			'move_lines': [(4, move_lines)],
			# 'rof_ids': [(4, self.rof_id.id)]
		})

		self.rof_id.sudo().action_check_availability()
		self.rof_id.sudo().generate_mtf_notes()
