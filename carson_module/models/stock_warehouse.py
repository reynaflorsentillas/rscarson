# -*- coding: utf-8 -*-
# Copyright YEAR(S), AUTHOR(S)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, api

import logging
_logger = logging.getLogger('models')

class StockWarehouse(models.Model):
	_inherit = "stock.warehouse"

	carson_project_ids = fields.Many2many('carson.projects', compute="_get_projects", store=True)
	project_users = fields.Many2many('carson.projects.users', string='Authorized Users', compute="_get_projects", store=True)
	warehouse_type = fields.Selection([('main','Main'),('site','Site'),], string='Type', required=True, default='main')

	@api.multi
	def _get_projects(self):
		for record in self:
			project_ids = self.env['carson.projects'].search([('site_warehouse_id','=',record.id)])
			project_users = False
			if project_ids:
				project_users = project_ids.mapped('project_users')
			record.carson_project_ids = project_ids
			record.project_users = project_users

class StockLocation(models.Model):
	_inherit = "stock.location"

	warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', compute='compute_warehouse', store=True)

	@api.multi
	@api.depends('location_id','parent_left','parent_right')
	def compute_warehouse(self):
		for record in self:
			warehouse_id = self.env['stock.warehouse'].search([
				('view_location_id.parent_left', '<=', record.parent_left),
				('view_location_id.parent_right', '>=', record.parent_left)], limit=1)
			record.warehouse_id = warehouse_id

	def button_compute_warehouse(self):
		self.compute_warehouse()