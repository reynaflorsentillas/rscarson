# -*- coding: utf-8 -*-
# Copyright YEAR(S), AUTHOR(S)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, api

import logging
_logger = logging.getLogger('models')

class CarsonRofGenerateMTF(models.TransientModel):
	_name = 'carson.rof.generate.mtf'
	_description = 'Wizard to generate MTF from Requisition Order'

	def _default_rof(self):
		return self.env['carson.rof'].browse(self._context.get('active_id'))

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
	location_id = fields.Many2one('stock.location', string='Source Location', required=True, default=_default_location_id)
	location_dest_id = fields.Many2one('stock.location', string='Destination Location', required=True)

	item_ids = fields.Many2many('carson.rof.items', string='Items', default=_default_rof_items)

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
		# Create procurement group
		procurement_group = self.env['procurement.group'].create({'name': self.rof_id.name})

		for x in self.item_ids:
			product_uom_qty = 0
			if x.state == 'partial':
				product_uom_qty = x.available_qty
			else:
				product_uom_qty = x.ordered_qty
				if x.reserved_qty != 0:
					product_uom_qty = x.ordered_qty - x.reserved_qty

			move_lines.append((0, 0,
				{
					'name':x.name,
					'product_id':x.product_id.id,
					'product_uom_qty':product_uom_qty,
					'product_uom':x.product_uom.id,
					'note':x.note,
					'picking_type_id': self.rof_id.warehouse_id.int_type_id.id,
					'group_id': procurement_group.id,
					'rof_item_id':x.id,
					'rof_id': self.rof_id.id,
				}
			))


		stock_picking = self.env['stock.picking'].with_context(planned_picking=True).create({
			'partner_id': self.rof_id.project_id.id,
			'scheduled_date': fields.Datetime.now(),
			'picking_type_id': self.rof_id.warehouse_id.int_type_id.id,
			'location_id': self.location_id.id,
			'location_dest_id': self.location_dest_id.id,
			'carson_project_id': self.rof_id.carson_project_id.id,
			'rof_ids': [(4, self.rof_id.id)],
			'origin': self.rof_id.name,
			'move_lines': move_lines,

		})
		# Confirm and reserve stock
		stock_picking.sudo().action_assign()
		self.rof_id.action_check_availability()
		self.rof_id.sudo().generate_mtf_notes()


