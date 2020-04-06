from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime

import logging
_logger = logging.getLogger(__name__)

class StockMove(models.Model):
	_inherit = "stock.move"

	rof_id = fields.Many2one('carson.rof', string='Requistion Order', copy=True)
	rof_item_id = fields.Many2one('carson.rof.items', 'Requistion Order Item', copy=True)

	@api.model
	def create(self, values):
		product_id = values.get('product_id')
		product_uom_qty = values.get('product_uom_qty')
		picking_id = values.get('picking_id')
		name = values.get('name')
		item_id = values.get('rof_item_id')
		if values.get('rof_id') and not values.get('rof_item_id'):
			rof_id = self.env['carson.rof'].browse(values.get('rof_id'))
			if rof_id:
				items = rof_id.mapped('rof_items')
				if not any(item.product_id.id == product_id for item in items):
					raise ValidationError(_("Item %s does not exist in the selected Requistion Order %s.") % (name,rof_id.name))
				for item in items:
					if item.product_id.id == product_id:
						item_id = item.id

		if item_id:
			values['rof_item_id'] = item_id
			if picking_id:
				self.env['carson.rof.items'].sudo().browse(item_id).write({'mtf_items': [(4, picking_id)]})
				# item.rof_item_id.sudo().write({'mtf_items': [(4, picking_id)]})

		result = super(StockMove, self).create(values)

		return result

	@api.multi
	def write(self, values):
		for record in self:
			product_id = values.get('product_id')
			product_uom_qty = values.get('product_uom_qty')
			picking_id = record.picking_id.id
			name = values.get('name')

			item_id = False

			rof_id = values.get('rof_id') 
			if not rof_id:
				rof_id = record.rof_id.id
			
			if product_id and rof_id:
				rof = self.env['carson.rof'].browse(rof_id)
				if rof:
					items = rof.mapped('rof_items')
					if not any(item.product_id.id == product_id for item in items):
						raise ValidationError(_("Item %s does not exist in the selected Requistion Order %s.") % (name,rof.name))
					for item in items:
						if item.product_id.id == product_id:
							item_id = item

			if item_id:
				values['rof_item_id'] = item_id.id
				if picking_id:
					item.rof_item_id.sudo().write({'mtf_items': [(4, picking_id)]})

		result = super(StockMove, self).write(values)
		return result

	# @api.multi
	# def unlink(self):
	# 	for record in self:
	# 		if record.picking_id:
	# 			picking_id = record.picking_id
	# 			if picking_id and picking_id.state not in ['draft','waiting	','confirmed','assigned','done','cancel']:
	# 				message = 'Removed an item from MTF: <ul class="o_mail_thread_message_tracking"> <li>Product: %s</li> </ul>' % (record.name)
	# 				picking_id.message_post(body=message)

	# 	result = super(StockMove, self).unlink()
	# 	return result

class StockMoveLine(models.Model):
	_inherit = "stock.move.line"

	available_qty = fields.Float(string="Available", compute="get_inventory", help="Available quantity for source location if operation is delivery. Available quantity for destination location if operation is receipts.")
	# is_outgoing = fields.Boolean(compute='_get_picking_type')

	@api.depends('product_id','location_id','location_dest_id','picking_id')
	def get_inventory(self):
		for line in self:
			stock_ids = []
			if line.picking_id.picking_type_id.code == 'incoming':
				stock_quant = self.env['stock.quant'].search([('product_id','=',line.product_id.id),('location_id','=',line.location_dest_id.id)])
				stock_ids = stock_quant
			else:
				stock_quant = self.env['stock.quant'].search([('product_id','=',line.product_id.id),('location_id','=',line.location_id.id)])
				stock_ids = stock_quant


			inv_qty = 0
			if stock_ids:
				for stock in stock_quant:
					inv_qty += stock.quantity

				line.available_qty = inv_qty


class StockPicking(models.Model):
	_inherit = "stock.picking"

	carson_project_id = fields.Many2one('carson.projects',string='Project', copy=True)
	related_site_project_id = fields.Many2one('carson.projects',string='For Site Project', help='Central to Central Transfer: Select Project to fulfill for this transfer')
	rof_ids = fields.Many2many('carson.rof', string='Requistion Orders')
	rof_id = fields.Many2one('carson.rof', string='Requistion Order', copy=True)
	
	state = fields.Selection([
		('draft', 'Draft'),
		('waiting', 'Waiting Another Operation'),
		('confirmed', 'Waiting'),
		('assigned', 'Ready'),
		('picapproved', 'PIC Approved'),
		('psapproved', 'PS Approved'),
		('pmapproved', 'PM Approved'),
		('whchecked', 'WH Checked'),
		('lhapproved', 'LH Approved'),
		('done', 'Done'),
		('cancel', 'Cancelled'),
	], string='Status', compute='_compute_state',
		copy=False, index=True, readonly=True, store=True, track_visibility='onchange',
		help=" * Draft: not confirmed yet and will not be scheduled until confirmed.\n"
			 " * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows).\n"
			 " * Waiting: if it is not ready to be sent because the required products could not be reserved.\n"
			 " * Ready: products are reserved and ready to be sent. If the shipping policy is 'As soon as possible' this happens as soon as anything is reserved.\n"
			 " * Done: has been processed, can't be modified or cancelled anymore.\n"
			 " * Cancelled: has been cancelled, can't be confirmed anymore.")

	is_return = fields.Boolean(copy=False)
	is_receive = fields.Boolean(compute='_compute_transit', store=True, copy=False)
	is_transit = fields.Boolean(compute='_compute_transit', store=True, copy=False)
	is_transit_main = fields.Boolean(compute='_compute_transit', store=True, string='Transit From Main To Site', copy=False)
	is_transit_site = fields.Boolean(compute='_compute_transit', store=True, string='Transit From Site To Site', copy=False)
	is_consume = fields.Boolean(compute='_compute_transit', store=True, copy=False)
	is_allow_validate = fields.Boolean(compute='_compute_validate')

	e_signature = fields.One2many('carson.esignature','picking_id', string='E-Signature', copy=False)

	is_picapproved = fields.Boolean(copy=False)
	is_psapproved = fields.Boolean(copy=False)
	is_pmapproved = fields.Boolean(copy=False)
	is_whchecked = fields.Boolean(copy=False)
	is_lhapproved = fields.Boolean(copy=False)

	@api.onchange('rof_id')
	def _set_item_location(self):
		for move in self.move_lines:
			move.rof_id = self.rof_id

	def signature_creator(self):
		self.env['carson.esignature'].create({
			'picking_id':self.id,
			'user_id':self.env.user.id,
			'sign_state':self.state
		})

	@api.multi
	def _compute_validate(self):
		for record in self:
			is_allow_validate = False
			if self.env.user.has_group('carson_module.group_site_warehouseman'):
				if record.is_return and record.state == 'assigned':
					is_allow_validate = False
				if record.is_receive and record.state == 'assigned':
					is_allow_validate = True

			# Main to Site
			if self.env.user.has_group('carson_module.group_warehouse_supervisor'):
				if not record.is_return and record.is_transit and record.state == 'assigned':
					is_allow_validate = True

			if self.env.user.has_group('carson_module.group_logistics_head'):
				if record.state == 'whchecked':
					is_allow_validate = True

			if self.env.user.has_group('carson_module.group_purchasing_boq'):
				if record.state == 'lhapproved':
					is_allow_validate = True

			if self.env.user.has_group('carson_module.group_purchasing_qs'):
				if record.state == 'lhapproved':
					is_allow_validate = True

			if self.env.user.has_group('carson_module.group_op_manager'):
				if record.state == 'pmapproved':
					is_allow_validate = True

			if self.env.user.has_group('carson_module.group_poc'):
				if not record.is_return and not record.is_transit and record.state == 'assigned':
					is_allow_validate = True

			# Main to Site delivery by production
			if self.env.user.has_group('carson_module.group_production_user') or self.env.user.has_group('carson_module.group_production_manager'):
				if record.state == 'assigned':
					is_allow_validate = True

			# Site to Satellite Transfer
			if self.env.user.has_group('carson_module.group_satellite_warehouseman'):
				if not record.is_return and not record.is_receive and record.state == 'pmapproved':
					is_allow_validate = True

			if self.env.user.has_group('carson_module.group_project_manager'):
				if record.state == 'picapproved':
					is_allow_validate = True

			# Satellite to Production
			if self.env.user.has_group('carson_module.group_satellite_warehouseman'):
				if not record.is_return and not record.is_receive and record.is_consume and record.state == 'picapproved':
					is_allow_validate = True

			# if self.env.user.has_group('carson_module.group_project_supervisor'):
			# 	if self.state == 'picapproved':
			# 		is_allow_validate = True

			# RETURN: Site to Main
			if self.env.user.has_group('carson_module.group_project_manager'):
				if record.is_return and record.is_transit and record.state == 'assigned':
					is_allow_validate = True

			# RETURN: Satellite to Site
			if self.env.user.has_group('carson_module.group_site_warehouseman'):
				if record.is_return and not record.is_transit and record.state == 'pmapproved':
					is_allow_validate = True

			record.is_allow_validate = is_allow_validate

	# OVERRIDE SHOW VALIDATE
	@api.multi
	@api.depends('state', 'is_locked')
	def _compute_show_validate(self):
		for picking in self:
			_logger.info("HELLO")
			_logger.info(self._context.get('planned_picking'))
			if self._context.get('planned_picking') and picking.state == 'draft':
				picking.show_validate = False
			elif picking.state not in ('draft', 'confirmed', 'assigned') or not picking.is_locked:
				picking.show_validate = False
			else:
				picking.show_validate = True
				if any(move.rof_id for move in picking.move_lines):
					picking.show_validate = False

	@api.one
	@api.depends('state','location_id','location_dest_id')
	def _compute_transit(self):
		is_receive = False
		is_transit = False
		is_transit_main = False
		is_transit_site = False
		is_consume = False

		if self.location_id.usage in ['transit','supplier']:
			# Receive From Transit Location
			is_receive = True
		if self.location_dest_id.usage == 'transit':
			is_transit = True
			# Check if transit is main to site or site to site
			warehouse_type = self.location_id.warehouse_id.warehouse_type
			warehouse_dest_type = self.location_dest_id.warehouse_id.warehouse_type
			if warehouse_type == 'main' and warehouse_dest_type == 'site':
				is_transit_main = True
			else:
				is_transit_site = True
		if self.location_dest_id.usage == 'production':
			is_consume = True

		self.is_receive = is_receive	
		self.is_transit = is_transit
		self.is_transit_main = is_transit_main
		self.is_transit_site = is_transit_site
		self.is_consume = is_consume

	@api.multi
	def button_validate(self):
		if self.picking_type_id.code == 'outgoing':
			for move in self.move_line_ids:
				if move.qty_done > move.available_qty:
					raise UserError(_("You cannot validate transfer with done quantity greater than the available quantity. \n\n BLOCKING: %s" % move.product_id.display_name))
		result = super(StockPicking, self).button_validate()

		stock_picking = self.env['stock.picking'].search([('origin','=',self.name)], limit=1)

		group = ''

		if stock_picking:
		
			if self.is_return:
				# Send notification to main warehouseman
				group = 'carson_module.group_main_warehouseman'


			else:
				# Send notification to site warehouseman
				group = 'carson_module.group_site_warehouseman'

			
			activity_text = "New transfer to process"
			activity_summary = "Please review this transfer"
			activity_type = self.env['mail.activity.type'].search([('id','in',[4])], limit=1)

			users = self.carson_project_id.project_users

			if self.is_transit and self.is_transit_site:
				users = self.related_site_project_id.project_users

			group_id = self.env.ref(group)
			for user in users:
				if user.groups == group_id and user.user_id.has_group(group):
					self.env['mail.activity'].create({
						'activity_type_id': activity_type.id,
						'res_id': stock_picking.id,
						'res_model_id': self.env.ref('carson_module.model_stock_picking').id,
						'date_deadline': datetime.today(),
						'user_id':user.user_id.id,
						'note': activity_text,
						'summary':activity_summary
					})

			stock_picking.write({
				# 'rof_ids': [(4, tuple(rof_ids.ids))],
				'carson_project_id': self.carson_project_id.id,
			})

			# UPDATE AVAILABLE QTY IN ROF ITEMS
			for move in self.move_lines:
				if move and move.rof_id:
					move.rof_id.action_check_availability()

		self.signature_creator() 

		return result

	@api.one
	def button_test(self):
		stock_picking = self.env['stock.picking'].search([('name','=',self.origin)], limit=1)

		_logger.info(stock_picking)

		group = ''

		if stock_picking:
			self.write({'rof_id':stock_picking.rof_id.id})

	@api.one
	def button_validate_wh_super(self):
		# self.write({'state': 'whchecked'})
		self.write({
			'is_picapproved': False,
			'is_psapproved': False,
			'is_pmapproved': False,
			'is_whchecked': True,
			'is_lhapproved': False
		})

		activity_text = "Please review this Material Transmittal for your approval"
		activity_summary = "Pending approval for Material Transmittal"
		activity_type = self.env['mail.activity.type'].search([('id','in',[4])], limit=1)
		group = 'carson_module.group_logistics_head'
		group_id = self.env.ref(group)

		# rof = self.rof_id
		# users = rof.carson_project_id.project_users
		users = self.carson_project_id.project_users
		for user in users:
			if user.groups == group_id and user.user_id.has_group(group):
				self.env['mail.activity'].create({
					'activity_type_id': activity_type.id,
					'res_id': self.id,
					'res_model_id': self.env.ref('carson_module.model_stock_picking').id,
					'date_deadline': datetime.today(),
					'user_id':user.user_id.id,
					'note': activity_text,
					'summary':activity_summary
				})

		self.signature_creator()

	@api.one
	def button_validate_log_head(self):
		# self.write({'state': 'lhapproved'})
		self.write({
			'is_picapproved': False,
			'is_psapproved': False,
			'is_pmapproved': False,
			'is_whchecked': False,
			'is_lhapproved': True
		})

		activity_text = "Please review this Material Transmittal for your approval"
		activity_summary = "Pending approval for Material Transmittal"
		activity_type = self.env['mail.activity.type'].search([('id','in',[4])], limit=1)
		group = 'carson_module.group_purchasing_boq'

		# Check special items
		if any(move.product_id.categ_id.name == 'Special Items' for move in self.move_lines):
			_logger.info("PICKING HAS SPECIAL ITEMS")
			group = 'carson_module.group_purchasing_qs'

		group_id = self.env.ref(group)

		users = self.carson_project_id.project_users
		for user in users:
			if user.groups == group_id and user.user_id.has_group(group):
				self.env['mail.activity'].create({
					'activity_type_id': activity_type.id,
					'res_id': self.id,
					'res_model_id': self.env.ref('carson_module.model_stock_picking').id,
					'date_deadline': datetime.today(),
					'user_id':user.user_id.id,
					'note': activity_text,
					'summary':activity_summary
				})

		self.signature_creator()

	@api.one
	def button_validate_pm(self):
		# self.write({'state': 'pmapproved'})
		self.write({
			'is_picapproved': False,
			'is_psapproved': False,
			'is_pmapproved': True,
			'is_whchecked': False,
			'is_lhapproved': False
		})

		activity_type = self.env['mail.activity.type'].search([('id','in',[4])], limit=1)
		users = self.carson_project_id.project_users

		if self.is_return and self.is_transit:
			activity_text = "Please review this Material Transmittal for your approval"
			activity_summary = "Pending approval for Material Transmittal"

			group = 'carson_module.group_op_manager'
			group_id = self.env.ref(group)

			for user in users:
				if user.groups == group_id and user.user_id.has_group(group):
					self.env['mail.activity'].create({
						'activity_type_id': activity_type.id,
						'res_id': self.id,
						'res_model_id': self.env.ref('carson_module.model_stock_picking').id,
						'date_deadline': datetime.today(),
						'user_id':user.user_id.id,
						'note': activity_text,
						'summary':activity_summary
					})

		if not self.is_receive and not self.is_return and not self.is_consume:
			activity_text = "Please review this Material Transmittal to receive"
			activity_summary = "Approved transfer to receive"

			group = 'carson_module.group_satellite_warehouseman'
			group_id = self.env.ref(group)

			for user in users:
				if user.groups == group_id and user.user_id.has_group(group):
					self.env['mail.activity'].create({
						'activity_type_id': activity_type.id,
						'res_id': self.id,
						'res_model_id': self.env.ref('carson_module.model_stock_picking').id,
						'date_deadline': datetime.today(),
						'user_id':user.user_id.id,
						'note': activity_text,
						'summary':activity_summary
					})

		# Backload: Satellite to Site
		if self.is_return and not self.is_transit:
			activity_text = "Please review this Material Transmittal for your approval"
			activity_summary = "Pending approval for Material Transmittal"

			group = 'carson_module.group_site_warehouseman'
			group_id = self.env.ref(group)

			for user in users:
				if user.groups == group_id and user.user_id.has_group(group):
					self.env['mail.activity'].create({
						'activity_type_id': activity_type.id,
						'res_id': self.id,
						'res_model_id': self.env.ref('carson_module.model_stock_picking').id,
						'date_deadline': datetime.today(),
						'user_id':user.user_id.id,
						'note': activity_text,
						'summary':activity_summary
					})

		self.signature_creator()

	@api.one
	def button_validate_pic(self):
		# self.write({'state': 'picapproved'})
		self.write({
			'is_picapproved': True,
			'is_psapproved': False,
			'is_pmapproved': False,
			'is_whchecked': False,
			'is_lhapproved': False
		})

		activity_text = "Please review this Material Transmittal for your approval"
		activity_summary = "Pending approval for Material Transmittal"
		activity_type = self.env['mail.activity.type'].search([('id','in',[4])], limit=1)
		users = self.carson_project_id.project_users
		group = ''

		if not self.is_return and not self.is_transit and not self.is_consume:
			group = 'carson_module.group_project_manager'

		if not self.is_return and not self.is_transit and self.is_consume:
			group = 'carson_module.group_satellite_warehouseman'

		# Backload: Satellite to Site
		if self.is_return and not self.is_transit and not self.is_consume:
			group = 'carson_module.group_project_manager'

		if users and group:
			group_id = self.env.ref(group)
			for user in users:
				if user.groups == group_id and user.user_id.has_group(group):
					self.env['mail.activity'].create({
						'activity_type_id': activity_type.id,
						'res_id': self.id,
						'res_model_id': self.env.ref('carson_module.model_stock_picking').id,
						'date_deadline': datetime.today(),
						'user_id':user.user_id.id,
						'note': activity_text,
						'summary':activity_summary
					})

		self.signature_creator()

	@api.one
	def button_validate_ps(self):
		# self.write({'state': 'psapproved'})
		self.write({
			'is_picapproved': False,
			'is_psapproved': True,
			'is_pmapproved': False,
			'is_whchecked': False,
			'is_lhapproved': False
		})

		activity_type = self.env['mail.activity.type'].search([('id','in',[4])], limit=1)
		users = self.carson_project_id.project_users

		activity_text = "Please review this Material Transmittal to consume"
		activity_summary = "Approved transfer to consume"

		group = 'carson_module.group_satellite_warehouseman'
		group_id = self.env.ref(group)

		for user in users:
			if user.groups == group_id and user.user_id.has_group(group):
				self.env['mail.activity'].create({
					'activity_type_id': activity_type.id,
					'res_id': self.id,
					'res_model_id': self.env.ref('carson_module.model_stock_picking').id,
					'date_deadline': datetime.today(),
					'user_id':user.user_id.id,
					'note': activity_text,
					'summary':activity_summary
				})

		self.signature_creator()

	@api.multi
	def action_assign(self):
		result = super(StockPicking, self).action_assign()

		for record in self:

			if all(move.state in ['assigned'] for move in record.move_lines):

				activity_text = "Please review this Material Transmittal for your approval"
				activity_summary = "Pending approval for Material Transmittal"
				activity_type = self.env['mail.activity.type'].search([('id','in',[4])], limit=1)
				users = record.carson_project_id.project_users
				group = ''

				# Transit
				if not record.is_return and not record.is_consume and record.is_transit:
					# Site to Site
					if record.is_transit_site:
						group = 'carson_module.group_poc'
					else:
						# Main to Site
						group = 'carson_module.group_warehouse_supervisor'				

				# Site to Satellite
				if not record.is_return and not record.is_transit and not record.is_consume and not record.is_receive:
					group = 'carson_module.group_poc'

				# Satellite to Production
				if not record.is_return and not record.is_transit and record.is_consume:
					group = 'carson_module.group_poc'

				# Main To Site - Back Order
				if record.is_receive and record.backorder_id:
					group = 'carson_module.group_site_warehouseman'

				# Main - Receipts from Purchase
				if record.is_receive and record.purchase_id:
					group = 'carson_module.group_warehouse_supervisor'

				if users and group:
					group_id = self.env.ref(group)
					for user in users:
						if user.groups == group_id and user.user_id.has_group(group):
							self.env['mail.activity'].create({
								'activity_type_id': activity_type.id,
								'res_id': record.id,
								'res_model_id': self.env.ref('carson_module.model_stock_picking').id,
								'date_deadline': datetime.today(),
								'user_id':user.user_id.id,
								'note': activity_text,
								'summary':activity_summary
							})

		return result

	# OVERRIDE FOR CENTRAL TO CENTRAL TRANSFER (SITE TO SITE)
	@api.multi
	def action_confirm(self):
		# call `_action_confirm` on every draft move
		self.mapped('move_lines')\
			.filtered(lambda move: move.state == 'draft')\
			.sudo()._action_confirm()
		# call `_action_assign` on every confirmed move which location_id bypasses the reservation
		self.filtered(lambda picking: picking.location_id.usage in ('supplier', 'inventory', 'production') and picking.state == 'confirmed')\
			.mapped('move_lines').sudo()._action_assign()
		return True

	# OVERRIDE FOR CENTRAL TO CENTRAL TRANSFER (SITE TO SITE)
	@api.multi
	def action_cancel(self):
		self.mapped('move_lines').sudo()._action_cancel()
		self.write({'is_locked': True})
		return True

	# @api.multi
	# def set_status_booleans(self):
	# 	for record in self:
	# 		if record.state == 'picapproved':
	# 			record.is_picapproved = True
	# 		elif record.state == 'psapproved':
	# 			record.is_psapproved = True
	# 		elif record.state == 'pmapproved':
	# 			record.is_pmapproved = True
	# 		elif record.state == 'whchecked':
	# 			record.is_whchecked = True
	# 		elif record.state == 'lhapproved':
	# 			record.is_lhapproved = True

	@api.depends('move_type', 'move_lines.state', 'move_lines.picking_id', 'is_picapproved', 'is_psapproved', 'is_pmapproved', 'is_whchecked', 'is_lhapproved')
	@api.one
	def _compute_state(self):
		''' State of a picking depends on the state of its related stock.move
		- Draft: only used for "planned pickings"
		- Waiting: if the picking is not ready to be sent so if
		  - (a) no quantity could be reserved at all or if
		  - (b) some quantities could be reserved and the shipping policy is "deliver all at once"
		- Waiting another move: if the picking is waiting for another move
		- Ready: if the picking is ready to be sent so if:
		  - (a) all quantities are reserved or if
		  - (b) some quantities could be reserved and the shipping policy is "as soon as possible"
		- Done: if the picking is done.
		- Cancelled: if the picking is cancelled
		'''
		if not self.move_lines:
			self.state = 'draft'
		elif any(move.state == 'draft' for move in self.move_lines):  # TDE FIXME: should be all ?
			self.state = 'draft'
		elif all(move.state == 'cancel' for move in self.move_lines):
			self.state = 'cancel'
		elif all(move.state in ['cancel', 'done'] for move in self.move_lines):
			self.state = 'done'
		elif self.is_picapproved == True:
			self.state = 'picapproved'
		elif self.is_psapproved == True:
			self.state = 'psapproved'
		elif self.is_pmapproved == True:
			self.state = 'pmapproved'
		elif self.is_whchecked == True:
			self.state = 'whchecked'
		elif self.is_lhapproved == True:
			self.state = 'lhapproved'
		else:
			relevant_move_state = self.move_lines._get_relevant_state_among_moves()
			if relevant_move_state == 'partially_available':
				self.state = 'assigned'
			else:
				self.state = relevant_move_state

	# CREATE APPROVER SIGNATURES MANUALLY FOR BACKORDERS WITHOUT ESIGN
	@api.multi
	def update_esignature(self):
		self.ensure_one()
		if self.backorder_id and self.is_lhapproved == True and not self.e_signature:
			project_id = self.carson_project_id
			sign_user = []
			for user in project_id.project_users:
				if user.groups.id == self.env.ref('carson_module.group_warehouse_supervisor').id:
					self.env['carson.esignature'].create({
						'picking_id':self.id,
						'user_id':user.user_id.id,
						'sign_state':'assigned'
					})
				elif user.groups.id == self.env.ref('carson_module.group_logistics_head').id:
					self.env['carson.esignature'].create({
						'picking_id':self.id,
						'user_id':user.user_id.id,
						'sign_state':'whchecked'
					})

				elif user.groups.id == self.env.ref('carson_module.group_purchasing_boq').id:
					self.env['carson.esignature'].create({
						'picking_id':self.id,
						'user_id':user.user_id.id,
						'sign_state':'lhapproved'
					})

class ReturnPicking(models.TransientModel):
	_inherit = 'stock.return.picking'

	location_id = fields.Many2one('stock.location', 'Return Location', 
		domain="['|', ('id', '=', original_location_id),'|',('usage', '=', 'transit'), '&', ('return_location', '=', True), ('id', 'child_of', parent_location_id)]")

	def _create_returns(self):
		# TODO sle: the unreserve of the next moves could be less brutal
		for return_move in self.product_return_moves.mapped('move_id'):
			return_move.move_dest_ids.filtered(lambda m: m.state not in ('done', 'cancel'))._do_unreserve()

		# create new picking for returned products
		picking_type_id = self.picking_id.picking_type_id.return_picking_type_id.id or self.picking_id.picking_type_id.id
		new_picking = self.picking_id.copy({
			'move_lines': [],
			'picking_type_id': picking_type_id,
			'state': 'draft',
			'origin': _("Return of %s") % self.picking_id.name,
			'location_id': self.picking_id.location_dest_id.id,
			'location_dest_id': self.location_id.id,
			'is_return': True})
		new_picking.message_post_with_view('mail.message_origin_link',
			values={'self': new_picking, 'origin': self.picking_id},
			subtype_id=self.env.ref('mail.mt_note').id)
		returned_lines = 0
		for return_line in self.product_return_moves:
			if not return_line.move_id:
				raise UserError(_("You have manually created product lines, please delete them to proceed"))
			# TODO sle: float_is_zero?
			if return_line.quantity:
				returned_lines += 1
				vals = self._prepare_move_default_values(return_line, new_picking)
				r = return_line.move_id.copy(vals)
				vals = {}

				# +--------------------------------------------------------------------------------------------------------+
				# |       picking_pick     <--Move Orig--    picking_pack     --Move Dest-->   picking_ship
				# |              | returned_move_ids              ↑                                  | returned_move_ids
				# |              ↓                                | return_line.move_id              ↓
				# |       return pick(Add as dest)          return toLink                    return ship(Add as orig)
				# +--------------------------------------------------------------------------------------------------------+
				move_orig_to_link = return_line.move_id.move_dest_ids.mapped('returned_move_ids')
				move_dest_to_link = return_line.move_id.move_orig_ids.mapped('returned_move_ids')
				vals['move_orig_ids'] = [(4, m.id) for m in move_orig_to_link | return_line.move_id]
				vals['move_dest_ids'] = [(4, m.id) for m in move_dest_to_link]
				r.write(vals)
		if not returned_lines:
			raise UserError(_("Please specify at least one non-zero quantity."))

		new_picking.action_confirm()
		new_picking.action_assign()

		# Backload: Notificcation to PM
		activity_text = "Please review this Material Transmittal for your approval"
		activity_summary = "Pending approval for Material Transmittal"
		activity_type = self.env['mail.activity.type'].search([('id','in',[4])], limit=1)

		group = ''
		group_id = False
		# RETURN: Site to Main
		if new_picking.is_return and new_picking.is_transit:
			group = 'carson_module.group_project_manager'
		# RETURN: Satellite to Site
		if new_picking.is_return and not new_picking.is_transit:
			group = 'carson_module.group_poc'
		
		if group:
			group_id = self.env.ref(group)

		users = self.picking_id.carson_project_id.project_users
		for user in users:
			if  user.groups == group_id and user.user_id.has_group(group):
				self.env['mail.activity'].create({
					'activity_type_id': activity_type.id,
					'res_id': new_picking.id,
					'res_model_id': self.env.ref('carson_module.model_stock_picking').id,
					'date_deadline': datetime.today(),
					'user_id':user.user_id.id,
					'note': activity_text,
					'summary':activity_summary
				})
		return new_picking.id, picking_type_id