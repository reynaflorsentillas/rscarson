# -*- coding: utf-8 -*-
# Copyright YEAR(S), AUTHOR(S)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models

class CarsonRofGenerateJob(models.TransientModel):
	_name = 'carson.rof.generate.job'
	_description = 'Wizard to generate job order from Requisition Order'

	def _default_rof(self):
		return self.env['carson.rof'].browse(self._context.get('active_id'))

	def _default_rof_items(self):
		rof_id = self.env['carson.rof'].browse(self._context.get('active_id'))
		rof_items = self.env['carson.rof.items'].search([('rof_item_id','=',rof_id.id)])
		return rof_items

	rof_id = fields.Many2one('carson.rof', string='Requisition Order', default=_default_rof)
	item_ids = fields.Many2many('carson.rof.items', string='Items', default=_default_rof_items)
	
	def apply(self):
		lines = []
		for item in self.item_ids:
			lines.append((0, 0, {
				'product_id': item.product_id.id,
			}))
		job_order = self.env['carson.job.order']
		job_order.create({
			'customer_id': self.rof_id.project_id.id,
			'rof_id': self.rof_id.id,
			'line_ids': lines,
		})