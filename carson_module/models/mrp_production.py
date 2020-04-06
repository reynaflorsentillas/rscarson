from odoo import models, fields, api, _ 

import logging
_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
	_inherit = 'mrp.production'

	rof_id = fields.Many2one('carson.rof', string='Requisition Order', readonly=True, states={'confirmed': [('readonly', False)]})
	rof_item_id = fields.Many2one('carson.rof.items', string='Requisition Order Item', readonly=True, states={'confirmed': [('readonly', False)]})
	carson_project_id =  fields.Many2one('carson.projects', string='Project')

	# OVERRIDE GENERATION OF MOVES OF FINISHED PRODUCT TO SET ROF AND ROF ITEM
	def _generate_finished_moves(self):
		move = self.env['stock.move'].create({
			'name': self.name,
			'date': self.date_planned_start,
			'date_expected': self.date_planned_start,
			'product_id': self.product_id.id,
			'product_uom': self.product_uom_id.id,
			'product_uom_qty': self.product_qty,
			'location_id': self.product_id.property_stock_production.id,
			'location_dest_id': self.location_dest_id.id,
			'company_id': self.company_id.id,
			'production_id': self.id,
			'origin': self.name,
			'group_id': self.procurement_group_id.id,
			'propagate': self.propagate,
			'move_dest_ids': [(4, x.id) for x in self.move_dest_ids],
			'rof_id': self.rof_id.id,
			'rof_item_id': self.rof_item_id.id,
		})
		move._action_confirm()
		return move

	@api.multi
	def _generate_moves(self):
		result = super(MrpProduction, self)._generate_moves()
		for production in self:
			production._update_rof_delivery()
		return result

	def _update_rof_delivery(self):
		move_ids = self.env['stock.move'].search([('rof_item_id','=',self.rof_item_id.id)])
		for move in move_ids:
			if move.picking_id:
				rof_items = self.env['carson.rof.items'].sudo().browse(self.rof_item_id.id)
				for item in rof_items:
					item.rof_item_id.write({'mtf_items': [(4, move.picking_id.id)]})

class MrpBom(models.Model):
	_inherit = 'mrp.bom'

	carson_project_id =  fields.Many2one('carson.projects', string='Project')
	area_id = fields.Many2one('carson.rof.area', string='Area')
	zone_id = fields.Many2one('carson.rof.zone', string='Zone')

	# @api.multi
	# def name_get(self):
	# 	for bom in self:
	# 		location = ''
	# 		if bom.carson_project_id or bom.area_id or bom.zone_id:
	# 			location += '('
	# 		if location:
	# 			if bom.carson_project_id:
	# 				location += bom.carson_project_id.name
	# 			if bom.area_id:
	# 				location += bom.area_id.name
	# 			if bom.zone_id:
	# 				location += bom.zone_id.name
	# 			location += ')'
	# 		name = [(bom.id, '%s%s%s' % (bom.code and '%s: ' % bom.code or '', bom.product_tmpl_id.display_name, location))]
	# 		return name