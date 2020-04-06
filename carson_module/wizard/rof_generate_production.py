from odoo import fields, models, api, _ 

import logging
_logger = logging.getLogger('models')

class CarsonRofGenerateProduction(models.TransientModel):
	_name = 'carson.rof.generate.production'
	_description = 'Wizard to generate Manufacturing Order from Requisition Order'

	def _default_rof(self):
		return self.env['carson.rof'].browse(self._context.get('active_id'))

	@api.model
	def _get_default_picking_type(self):
		return self.env['stock.picking.type'].search([
			('code', '=', 'mrp_operation'),
			('warehouse_id.company_id', 'in', [self.env.context.get('company_id', self.env.user.company_id.id), False])],
			limit=1)

	@api.model
	def _get_default_location(self):
		rof_id = self.env['carson.rof'].browse(self._context.get('active_id'))
		return rof_id.carson_project_id.location_dest_id.id

	# def _default_rof_items(self):
	# 	rof_id = self.env['carson.rof'].browse(self._context.get('active_id'))
	# 	rof_items = self.env['carson.rof.items'].search([('rof_item_id','=',rof_id.id),('to_manufacture','=',True)])
	# 	items = []
	# 	for item in rof_items:
	# 		items.append(item.id)
	# 	return items

	rof_id = fields.Many2one('carson.rof', string='Requisition Order', default=_default_rof)
	picking_type_id = fields.Many2one('stock.picking.type', 'Operation Type', default=_get_default_picking_type, required=True)
	company_id = fields.Many2one('res.company', 'Company',default=lambda self: self.env['res.company']._company_default_get('mrp.production'),required=True)
	item_id = fields.Many2one('carson.rof.items', string='Product To Manufacture')
	product_id = fields.Many2one(related='item_id.product_id')
	manufacture_qty = fields.Float(related='item_id.manufacture_qty')
	product_uom = fields.Many2one(related='item_id.product_uom')
	bom_id = fields.Many2one('mrp.bom', 'Bill of Material', help="Bill of Materials allow you to define the list of required raw materials to make a finished product.")
	location_dest_id = fields.Many2one('stock.location', string='Finished Products Location', require=True, default=_get_default_location)

	@api.onchange('item_id')
	def set_item_details(self):
		if not self.item_id:
			self.bom_id = False
		else:
			bom = self.env['mrp.bom']._bom_find(product=self.item_id.product_id, picking_type=self.picking_type_id, company_id=self.company_id.id)
			if bom.type == 'normal':
				self.bom_id = bom.id
			else:
				self.bom_id = False

	def apply(self):

		production_order = self.env['mrp.production'].create({
			'product_id': self.product_id.id,
			'product_qty': self.manufacture_qty,
			'product_uom_id': self.product_uom.id,
			'origin': self.item_id.rof_item_id.name,
			'bom_id': self.bom_id.id,
			'carson_project_id': self.item_id.rof_item_id.carson_project_id.id,
			'rof_id': self.item_id.rof_item_id.id,
			'rof_item_id': self.item_id.id,
			'picking_type_id': self.picking_type_id.id,
			'location_dest_id': self.location_dest_id.id,
		})
		return {
			'type': 'ir.actions.act_window',
			'res_model': 'mrp.production',
			'view_mode': 'form',
			'res_id': production_order.id,
			'target': 'current',
			'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}
		}