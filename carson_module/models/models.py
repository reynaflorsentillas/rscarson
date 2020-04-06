# -*- coding: utf-8 -*-
from datetime import datetime
from datetime import timedelta
from datetime import date
from odoo.addons import decimal_precision as dp
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import ValidationError, UserError

import logging
_logger = logging.getLogger('models')

ADMIN = 1

class RofArea(models.Model):
	_name = 'carson.rof.area'
	_description = 'Carson Area'

	name = fields.Char(string='Area')

class RofZone(models.Model):
	_name = 'carson.rof.zone'
	_description = 'Carson Zone'

	name = fields.Char(string='Zone')

class Rof(models.Model):
	_name = 'carson.rof'
	_description = 'Requisition Order Form'
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_order = 'requested_date desc,name desc'

	def _set_rof_type(self):
		if self.env.user.has_group('carson_module.group_main_warehouseman'):
			return 'main'
		elif self.env.user.has_group('carson_module.group_satellite_warehouseman'):
			return 'satellite'
		elif self.env.user.has_group('carson_module.group_production_user') or self.env.user.has_group('carson_module.group_production_manager'):
			return 'production'
		else:
			return 'site'

	name = fields.Char('Requisition Order', required=True,readonly=True, default='New')
	rof_items = fields.One2many('carson.rof.items','rof_item_id', string='Items', track_visibility='onchange')
	# mtf_items = fields.One2many('stock.picking','rof_id', string='Material Transmittal Items', track_visibility='onchange')
	mtf_items = fields.Many2many('stock.picking', string='Material Transmittal Items', track_visibility='onchange')
	po_items = fields.One2many('purchase.order','rof_id', string='Purchase Orders', track_visibility='onchange')
	po_item_ids = fields.Many2many('purchase.order', string='Purchase Orders', track_visibility='onchange')
	pa_items = fields.One2many('purchase.requisition','rof_id', string='Purchase Agreements', track_visibility='onchange')
	e_signature = fields.One2many('carson.esignature','ref_id', string='E-Signature')
	items = fields.One2many('product.template','rof_item_id', string='Items', track_visibility='onchange')
	requested_date = fields.Date('Requested Date', track_visibility='onchange',default=fields.Datetime.now)
	rof_user_name = fields.Char("User",readonly=True)
	project_id = fields.Many2one('res.partner',string='Company', related='carson_project_id.company_id',readonly=True)
	carson_project_id =  fields.Many2one('carson.projects',string='Project')
	rof_state_values = [('draft','Draft'),('submit','Submitted'), ('pending','Pending'), ('picapproved','PIC Approved'), ('pmapproved','PM Approved'), ('omapproved',' OM Approved')
		, ('qsvalidated','QS Validated'),('whmchecked','Warehouse man'), ('whchecked','WH Checked'), ('inprogress','In Progress')
		, ('done','Done'), ('cancelled','Cancelled')]
	rof_state = fields.Selection(rof_state_values, default='draft', store=True, track_visibility='onchange', compute='_compute_state')
	jo_ids = fields.One2many('carson.job.order', 'rof_id', string='Job Orders')
	location_id = fields.Many2one('stock.location', string="Source Location", help='If not set, default location of warehouse will be used as source location of MTF.')
	warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', ondelete='cascade', default=lambda self: self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1))
	area = fields.Selection([
		('level_12', 'Level 12' ),
		('Level_16', 'Level 16'),
		('level_17', 'Level 17'),
		('tv_12', 'Tower Villa 12'),
		('tv_16', 'Tower Villa 16'),
		('tv_17', 'Tower Villa 17')
		], string='Area')

	zone = fields.Selection([
		('z1', 'Zone 1'),
		('z2', 'Zone 2'),
		('z3', 'Zone 3'),
		('none', 'none')], string='Zone')

	is_inprogress = fields.Boolean()
	is_done = fields.Boolean(compute='_compute_done', store=True)
	is_picapproved = fields.Boolean()
	is_pmapproved = fields.Boolean()
	is_omapproved = fields.Boolean()
	is_qsvalidated = fields.Boolean()
	is_whmchecked = fields.Boolean()
	is_whchecked = fields.Boolean()
	is_rejected = fields.Boolean()
	is_pending = fields.Boolean()
	is_cancelled = fields.Boolean()
	is_submitted = fields.Boolean()
	has_special_items = fields.Boolean(compute='_compute_has_special_items')
	for_wh_check = fields.Boolean(compute='compute_for_wh_check')
	is_cancel_visible = fields.Boolean(compute='compute_cancel_due')
	has_for_purchase = fields.Boolean(compute='compute_has_for_puchase')
	has_for_production = fields.Boolean(compute='compute_has_for_production')
	production_requested = fields.Boolean()
	active = fields.Boolean(string='Active', default=True)

	#ADDED BY SDS
	allow_to_view_gen_po = fields.Boolean(compute='_compute_allow_to_view_gen_po')

	rof_type = fields.Selection([
		('site', 'Site'),
		('satellite', 'Satellite'),
		('main', 'Main'),
		('production', 'Production')
		], string='Request From', default=_set_rof_type, store=True)

	package_no = fields.Char(string='Package #')
	area_id = fields.Many2one('carson.rof.area')
	zone_id = fields.Many2one('carson.rof.zone')

	# production_ids = fields.Many2many('mrp.production', string='Manufacturing Orders', track_visibility='onchange')
	# production_ids = fields.Related('rof_items.production_ids', string='Manufacturing Orders')
	production_ids = fields.One2many('mrp.production', 'rof_id', string='Manufacturing Orders')

	# is_allow_edit = fields.Boolean(compute='_compute_is_allow_edit')
	site_rof_id = fields.Char(string='Site Requisition')
	is_production_request = fields.Boolean(compute='_compute_is_prod_request', store=True)

	@api.multi
	@api.depends('rof_type')
	def _compute_is_prod_request(self):
		for record in self:
			if record.rof_type == 'site' and self.env.user.has_group('carson_module.group_production_user') or self.env.user.has_group('carson_module.group_production_manager'):
				record.is_production_request = True
			else:
				record.is_production_request = False

	@api.onchange('location_id')
	def _set_item_location(self):
		for item in self.rof_items:
			item.location_id = self.location_id

	# @api.one
	# @api.depends('rof_state','create_uid')
	# def _compute_is_allow_edit(self):
	# 	is_allow_edit = True
	# 	if self.rof_state in ['done','cancelled']:
	# 		is_allow_edit = False

	# 	if self.env.user.has_group('carson_module.group_site_warehouseman') or self.env.user.has_group('carson_module.group_satellite_warehouseman'):
	# 		_logger.info("HELLO")
	# 		_logger.info(self.create_uid)
	# 		_logger.info(self.env.user)
	# 		if self.create_uid and self.create_uid != self.env.user:
	# 			is_allow_edit = False

	# 	if self.env.user.has_group('carson_module.group_site_qs'):
	# 		if self.create_uid and self.create_uid != self.env.user:
	# 			is_allow_edit = False
	# 		if self.rof_state == 'omapproved':
	# 			is_allow_edit = True

	# 	self.is_allow_edit = is_allow_edit


	#ADDED By SDS 20/11/2019
	is_verifiedviapin_pic = fields.Boolean() 
	is_verifiedviapin_pm = fields.Boolean()
	is_verifiedviapin_om = fields.Boolean()
	is_verifiedviapin_qs = fields.Boolean()


	def _compute_allow_to_view_gen_po(self):
		self.allow_to_view_gen_po = False
		if self.rof_state  == 'inprogress':
			if self.is_whchecked == False and self.is_inprogress == True:
				self.allow_to_view_gen_po = True


	@api.depends('is_submitted','is_pending','is_picapproved','is_pmapproved','is_omapproved','is_qsvalidated','is_whmchecked','is_whchecked','is_rejected','is_cancelled','is_inprogress','is_done')
	@api.one
	def _compute_state(self):
		if self.is_rejected == True:
			self.rof_state = 'draft'
		elif self.is_submitted == True:
			self.rof_state = 'submit'
		elif self.is_pending == True:
			self.rof_state ='pending'
		elif self.is_picapproved == True:
			self.rof_state = 'picapproved'
		elif self.is_pmapproved == True:
			self.rof_state = 'pmapproved'
		elif self.is_omapproved == True:
			self.rof_state = 'omapproved'
		elif self.is_qsvalidated == True:
			self.rof_state = 'qsvalidated'
		elif self.is_whmchecked == True:
			self.rof_state = 'whmchecked'
		elif self.is_whchecked == True:
			self.rof_state = 'whchecked'
		elif self.is_inprogress == True:
			self.rof_state = 'inprogress'
		elif self.is_done == True:
			self.rof_state = 'done'
		elif self.is_cancelled == True:
			self.rof_state = 'cancelled'
		else:
			self.rof_state = 'draft'

	@api.onchange('warehouse_id')
	def _set_operation(self):
		# self.picking_type_id = self.warehouse_id.int_type_id
		self.location_id = self.warehouse_id.sudo().int_type_id.default_location_src_id

	def _compute_has_special_items(self):
		if any(item.product_id.categ_id.name == 'Special Items' for item in self.rof_items):
			self.has_special_items = True

	@api.one
	def compute_for_wh_check(self):
		if self.has_special_items:
			if self.rof_state == 'qsvalidated':
				self.for_wh_check = True
		else:
			if self.rof_state == 'omapproved':
				self.for_wh_check = True

	@api.one
	@api.depends('requested_date')
	def compute_cancel_due(self):
		requested_date = datetime.strptime(self.requested_date,"%Y-%m-%d")
		week = timedelta(days=7)
		cancel_due_date = requested_date + week
		if datetime.today().date() <= cancel_due_date.date():
			if self.rof_state in ['draft','pending']:
				self.is_cancel_visible = True
			else:
				self.is_cancel_visible = False
		else:
			self.is_cancel_visible = False

	@api.one
	def compute_has_for_puchase(self):
		if any(item.state in ['purchase','partial'] for item in self.rof_items):
			self.has_for_purchase = True

	def action_rof_req_purchase_approve(self):
		if self.rof_type == 'production' or self.rof_type == 'site' and self.is_production_request == True:
			ir_attachment_obj = self.env['ir.attachment'].sudo().search([('res_model','=', 'carson.rof'),('res_id','=', self.id)])
			if ir_attachment_obj:
				self.write({'is_pmapproved': False})
				self.write({'is_inprogress': True})
				self._compute_state()

				items = '<ul>'
				purchase_items = self.rof_items.filtered(lambda item: item.state in ['purchase','partial'])
				for item in purchase_items:
					items += "<li> %s </li>" % (item.name)

				items += '<ul/>'

				activity_summary = 'Request for purchase'
				activity_text = 'Please review this Requistion Order for purchasing of unavailable items. The following items are not available: <br/>%s' % (items)
				self.activity_creator(activity_text,activity_summary,'group_purchasing_staff')
				self.action_activity_done('carson_module.group_production_user')
				self.signature_creator()
			else:
				raise UserError(_('No File Attached Found.'))
		else:
			items = '<ul>'
			purchase_items = self.rof_items.filtered(lambda item: item.state in ['purchase','partial'])
			for item in purchase_items:
				items += "<li> %s </li>" % (item.name)

			items += '<ul/>'
		
			if self.is_omapproved == True:
				self.write({'is_omapproved': False})
			if self.is_qsvalidated == True:
				self.write({'is_qsvalidated': False})
			self.write({'is_whmchecked': True})
			self._compute_state()
			activity_message = 'Please review this Requisition Order for purchase approval of the following items: <br/>%s' % (items)
			self.activity_creator(activity_message,'Pending approval of Requisition Order','group_warehouse_supervisor')
			self.signature_creator()

	@api.one
	@api.depends('rof_items.move_lines','rof_items.move_lines.state','po_items','po_items.state','jo_ids.state')
	def _compute_done(self):
		is_done = False
		purchase_done = False
		job_done = False
		item_done = False

		if self.po_items:
			if all(purchase.state in ['cancel','done','purchase'] for purchase in self.po_items):
				purchase_done = True
		else:
			purchase_done = True

		if self.jo_ids:
			if all(job.state in ['cancelled','done'] for job in self.jo_ids):
				job_done = True
		else:
			job_done = True

		if self.rof_items:
			if all(item.state in ['delivered','satellite','consumed'] for item in self.rof_items):
				# if all(item.ordered_qty != 0 and item.delivered_qty >= item.ordered_qty for item in self.rof_items):
				item_done = True

		if purchase_done and job_done and item_done:
			is_done = True
			self.write({
				'is_submitted': False,
				'is_pending': False,
				'is_picapproved': False,
				'is_pmapproved': False,
				'is_omapproved': False,
				'is_qsvalidated': False,
				'is_whmchecked': False,
				'is_whchecked': False,
				'is_inprogress': False,
			})

		self.is_done = is_done

	@api.multi
	def action_rof_accept(self):
		model = self.env['carson.rof'].search([('id', '=', self.id)])
		items = self.env['carson.rof.items'].search([('rof_item_id', '=', self.id)])
		ord_qty = 0
		rfq_lines = []

		# Validation FOR ROF IN MAIN
		if self.rof_type == 'main':
			if self.env.user.has_group('carson_module.group_main_warehouseman'):
				self.write({'is_omapproved': False})
				self.write({'for_wh_check': False})
				activity_summary = 'Pending approval of Requisition Order'
				activity_text = 'Please review this Requisition Order for your approval'
				self.activity_creator(activity_text,activity_summary,'group_warehouse_supervisor')
				self.action_activity_done('carson_module.group_main_warehouseman')

			if self.env.user.has_group('carson_module.group_warehouse_supervisor'):
				items = '<ul>'
				purchase_items = self.rof_items.filtered(lambda item: item.state in ['purchase','partial'])
				for item in purchase_items:
					items += "<li> %s </li>" % (item.name)

				items += '<ul/>'
				self.write({'is_whmchecked': False})
				self.write({'is_whchecked': True})
				activity_summary = 'Pending approval of Requisition Order'
				activity_text = 'Please review this Requisition Order for your approval'
				if self.has_for_purchase:
					activity_text = 'Please review this Requisition Order for purchase approval of the following items: <br/>%s' % (items)
				self.activity_creator(activity_text,activity_summary,'group_logistics_head')
				self.action_activity_done('carson_module.group_warehouse_supervisor')

			if self.env.user.has_group('carson_module.group_logistics_head'):
				self.write({'is_whchecked': False})
				self.write({'is_inprogress': True})
				if self.has_for_purchase:
					items = '<ul>'
					purchase_items = self.rof_items.filtered(lambda item: item.state in ['purchase','partial'])
					for item in purchase_items:
						items += "<li> %s </li>" % (item.name)

					items += '<ul/>'
					
					activity_summary = 'Request for purchase'
					activity_text = 'Please review this Requistion Order for purchasing of unavailable items. The following items are not available: <br/>%s' % (items)
					self.activity_creator(activity_text,activity_summary,'group_purchasing_staff')
					self.action_activity_done('carson_module.group_logistics_head')
		elif self.rof_type == 'production':
			if self.env.user.has_group('carson_module.group_production_manager'):
				self.write({'is_pending': False})
				self.write({'is_pmapproved': True})
				
				activity_summary = 'ROF Approved'
				activity_text = 'Please review this Requistion Order for submission to purchasing.'
				self.activity_creator(activity_text,activity_summary,False,self.create_uid)
				self.action_activity_done('carson_module.group_production_manager')
		else:

			if self.env.user.has_group('carson_module.group_poc'):
				self.write({'is_pending': False})
				self.write({'is_picapproved': True})

				self.write({'is_verifiedviapin_pic': True})

				activity_summary = 'Pending approval of Requisition Order'
				activity_text = 'Please review this Requisition Order for your approval'
				self.activity_creator(activity_text,activity_summary,'group_project_manager')
				self.action_activity_done('carson_module.group_poc')

			if self.env.user.has_group('carson_module.group_project_manager'):
				self.write({'is_picapproved': False})
				self.write({'is_pmapproved': True})

				self.write({'is_verifiedviapin_pm': True})

				activity_summary = 'Pending approval of Requisition Order'
				activity_text = 'Please review this Requisition Order for your approval'
				self.activity_creator(activity_text,activity_summary,'group_op_manager')
				self.action_activity_done('carson_module.group_project_manager')


			if self.env.user.has_group('carson_module.group_op_manager'):
				self.write({'is_pmapproved': False})
				self.write({'is_omapproved': True})

				# if self.has_special_items:
				# 	activity_summary = 'Pending approval of Requisition Order'
				# 	activity_text = 'Please review this Requisition Order for your approval'
				# 	self.activity_creator(activity_text,activity_summary,'group_purchasing_qs')
				# else:
				# 	activity_summary = 'Pending approval of Requisition Order'
				# 	activity_text = 'Please review this Requisition Order for your approval'
				# 	self.activity_creator(activity_text,activity_summary,'group_site_qs')
				self.write({'is_verifiedviapin_om': True})

				activity_summary = 'Pending approval of Requisition Order'
				activity_text = 'Please review this Requisition Order for your approval'
				self.activity_creator(activity_text,activity_summary,'group_main_warehouseman')
				self.action_activity_done('carson_module.group_op_manager')

			# if self.env.user.has_group('carson_module.group_qs_supervisor'):
			# 	self.write({'is_omapproved': False})
			# 	self.write({'is_qsvalidated': True})
			# 	self.write({'for_wh_check': False})
			# 	activity_summary = 'Pending approval of Requisition Order'
			# 	activity_text = 'Please review this Requisition Order for your approval'
			# 	self.activity_creator(activity_text,activity_summary,'group_main_warehouseman')

			# if self.env.user.has_group('carson_module.group_purchasing_qs') or self.env.user.has_group('carson_module.group_site_qs'):
			# 	self.write({'is_omapproved': False})
			# 	self.write({'is_qsvalidated': True})
			# 	self.write({'for_wh_check': False})
			# 	activity_summary = 'Pending approval of Requisition Order'
			# 	activity_text = 'Please review this Requisition Order for your approval'
			# 	self.activity_creator(activity_text,activity_summary,'group_main_warehouseman')

			if self.env.user.has_group('carson_module.group_warehouse_supervisor'):
				items = '<ul>'
				purchase_items = self.rof_items.filtered(lambda item: item.state in ['purchase','partial'])
				for item in purchase_items:
					items += "<li> %s </li>" % (item.name)

				items += '<ul/>'
				self.write({'is_whmchecked': False})
				self.write({'is_whchecked': True})
				activity_summary = 'Pending approval of Requisition Order'
				activity_text = 'Please review this Requisition Order for purchase approval of the following items: <br/>%s' % (items)
				self.activity_creator(activity_text,activity_summary,'group_logistics_head')
				self.action_activity_done('carson_module.group_warehouse_supervisor')

			if self.env.user.has_group('carson_module.group_logistics_head'):
				items = '<ul>'
				purchase_items = self.rof_items.filtered(lambda item: item.state in ['purchase','partial'])
				for item in purchase_items:
					items += "<li> %s </li>" % (item.name)

				items += '<ul/>'
				self.write({'is_whchecked': False})
				self.write({'is_inprogress': True})
				activity_summary = 'Request for purchase'
				activity_text = 'Please review this Requistion Order for purchasing of unavailable items. The following items are not available: <br/>%s' % (items)
				self.activity_creator(activity_text,activity_summary,'group_purchasing_staff')
				self.action_activity_done('carson_module.group_logistics_head')

			if self.env.user.has_group('carson_module.group_production_manager'):
				self.write({'is_pending': False})
				self.write({'is_inprogress': True})
				
				activity_summary = 'Site ROF Approved'
				activity_text = 'Please review this Requistion Order for submission to purchasing and/or generation of production order.'
				self.activity_creator(activity_text,activity_summary,False,self.create_uid)
				self.action_activity_done('carson_module.group_production_manager')

		self._compute_state()
		self.signature_creator()

	@api.multi
	def action_activity_done(self, group):
		mail_activity = self.env['mail.activity'].search([('res_model','=','carson.rof'),('res_id','=',self.id),('user_id','=',self.env.uid)])
		if mail_activity:
			for activity in mail_activity:
				if self.env.user.has_group(group):
					activity.action_feedback()


	@api.multi
	def action_rof_reject(self):
		return {
			'name': _('Reject Requisition Order'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'carson.rof.reject',
			'target': 'new',
		}

	#Added by SDS
	@api.multi
	def action_open_pin_verification(self):
		return {
				'name': _('ROF Pin Verification'),
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'rof.user.pin.wizard2',
				'target': 'new',}

	@api.multi
	def action_rof_req_approve_override(self):
		if not self.rof_items:
			raise ValidationError(_('Please add an item to ROF to request approval.'))
	
		if self.rof_state in ['draft','submit']:
			if self.is_rejected:
				self.write({'is_rejected': False})
			# MAIN WAREHOUSE REQUEST
			if self.rof_type == 'main':
				self.write({'is_whmchecked': True})
				self.activity_creator('Please review this Requisition Order for you approval.','Pending approval of Requisition Order','group_warehouse_supervisor')
				# SITE REQUEST
			else:
				#Added By SDS for Solaire
				#Solaire Project
				# if self.carson_project_id.id == 4:
				if self.carson_project_id.name == 'Solaire':
					return {
						'name': _('OM Override'),
						'type': 'ir.actions.act_window',
						'view_type': 'form',
						'view_mode': 'form',
						'res_model': 'rof.user.pin.wizard',
						'target': 'new',
					}

				else:
					self.write({'is_submitted': False})
					self.write({'is_pending': False})
					self.write({'is_omapproved': True})
					self.activity_creator('Please review this Requisition Order for you approval.','Pending approval of Requisition Order','group_main_warehouseman')
		

	@api.multi
	def action_rof_req_approve(self):
		if not self.rof_items:
			raise ValidationError(_('Please add an item to ROF to request approval.'))

		if self.rof_state in ['draft','submit']:
			if self.is_rejected:
				self.write({'is_rejected': False})
			# MAIN WAREHOUSE REQUEST
			if self.rof_type == 'main':
				self.write({'is_whmchecked': True})
				self.activity_creator('Please review this Requisition Order for you approval.','Pending approval of Requisition Order','group_warehouse_supervisor')
			# PRODUCTION REQUEST
			elif self.rof_type == 'production':
				self.write({'is_pending': True})
				self.activity_creator('Please review this Requisition Order for you approval.','Pending approval of Requisition Order','group_production_manager')
			# SITE REQUEST BY PROD
			elif self.rof_type == 'site' and self.is_production_request == True:
				self.write({'is_pending': True})
				self.activity_creator('Please review this Requisition Order for you approval.','Pending approval of Requisition Order','group_production_manager')
			# SITE REQUEST
			else:
				self.write({'is_submitted': False})
				self.write({'is_pending': True})
				self.activity_creator('Please review this Requisition Order for you approval.','Pending approval of Requisition Order','group_poc')

			self.signature_creator()

	@api.multi
	def action_rof_submit(self):
		if not self.rof_items:
			raise ValidationError(_('Please add an item to ROF to submit.'))

		if self.rof_state == 'draft':
			if self.is_rejected:
				self.write({'is_rejected': False})

			self.write({'is_submitted': True})
			self.activity_creator('Please review this Requisition Order for you approval.','Pending approval of Requisition Order','group_site_warehouseman')

			self.signature_creator()

	@api.multi
	def action_generate_mtf(self):
		return {
			'name': _('ROF Generate Material Transmittal'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'carson.rof.generate.mtf',
			'target': 'new',
		}

	@api.multi
	def action_add_mtf(self):
		return {
			'name': _('ROF Add To Existing Material Transmittal'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'carson.rof.add.mtf',
			'target': 'new',
		}

	@api.multi
	def action_rof_cancel(self):
		self.write({
			'is_pending': False,
			'is_picapproved': False,
			'is_pmapproved': False,
			'is_omapproved': False,
			'is_qsvalidated': False,
			'is_whmchecked': False,
			'is_whchecked': False,
			'is_inprogress': False,
			'available_qty': 0,
			'is_checked_available_qty': False,
			'is_rejected': False,
			'is_cancelled': True,
		})
		# Cancel pending activities
		self.activity_cancel(self.id)

	def action_generate_jo(self):
		return {
			'name': _('ROF Generate Job Order'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'carson.rof.generate.job',
			'target': 'new',
		}

	def action_generate_purchase(self):
		return {
			'name': _('ROF Generate Purchase'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'carson.rof.generate.purchase',
			'target': 'new',
		}

	@api.multi
	def action_add_purchase(self):
		return {
			'name': _('ROF Add To Existing Purchase Order'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'carson.rof.add.purchase',
			'target': 'new',
		}

	@api.multi
	def action_generate_production(self):
		return {
			'name': _('ROF Generate Manufacturing Order'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'carson.rof.generate.production',
			'target': 'new',
		}

	@api.model
	def generate_mtf_notes(self):
		for item in self.rof_items:
			for move in item.move_lines:
				if str(move.picking_id.name) not in str(item.note):
					if item.note:
						item.write({
							'note': str(move.picking_id.name) + ', ' + str(item.note)
						})
					else:
						item.write({
							'note': str(move.picking_id.name)
						})
		return True


	@api.model
	def generate_po_notes(self):
		for po in self.po_items:
			for order in po.order_line:
				for rof in self.rof_items:
					if order.name == rof.name:
						if str(po.name) not in str(rof.note):
							data = str(rof.note)
							_logger.info(rof.note)
							if rof.note:
								res = rof.write({
								'note': str(po.name) + ', ' + str(rof.note)
								})
							else:
								res = rof.write({
								'note': str(po.name)
								})

		return True




	@api.model
	def create(self, vals):
		if vals.get('name', 'New') == 'New':
			vals['name'] = self.env['ir.sequence'].next_by_code('carson.rof') or 'New'
			vals['rof_user_name'] = self.env.user.name

		record = super(Rof, self).create(vals)

		carson_proj = self.env['carson.projects'].search([('project_rofs','=',record.id)])
		carson_list = carson_proj.project_users
		added_list = []

		for x in carson_list:
			_logger.info('Followers Name: ' + x.user_id.name )

			if x.user_id.name not in added_list and not x.user_id.has_group('carson_module.group_manager') and x.user_id.name not in self.env.user.name:
				self.env['mail.followers'].create({
				'res_id': record.id,
				'res_model': 'carson.rof',
				'partner_id': x.user_id.partner_id.id,
				})
			else:
				_logger.info('User already here!')


			added_list.append(x.user_id.name)

			_logger.info('Added List length: ' + str(len(added_list)))


		return record

	def activity_creator(self,activity_text,activity_summary,group,creator=False):
		_logger.info('Activity Creation Function')
		users = []
		activity_type = self.env['mail.activity.type'].search([('id','in',[4])], limit=1)
		model_orig = self.env['ir.model'].search([('name','=','Requisition Order Form')])
		model = self.env['carson.rof'].search([('id', '=', self.id)])
		users_ids = model.carson_project_id.project_users



		group_id = False

		group_name = ''
		if group:
			group_id = self.env.ref('carson_module.'+group)
			group_name = group_id.name


		is_exist = False

		_logger.info('user id: ' + str(len(users_ids)))

		#Loop through the records

		for x in users_ids:
			if creator and not group:
				users = creator
				is_exist = True
			else:
				if x.groups == group_id and x.user_id.has_group('carson_module.'+group):
					users.append(x.user_id)
					is_exist = True

		if not is_exist:
			raise exceptions.ValidationError("This project doesn't have a "+group_name+" assigned to it.")

		for user in users:
			self.env['mail.activity'].create({
				'activity_type_id': activity_type.id,
				'res_id': model.id,
				'res_model_id': model_orig.id,
				'date_deadline': datetime.today(),
				'user_id':user.id,
				'note': activity_text,
				'summary':activity_summary
				})

	def activity_cancel(self,res_id):
		mail_activiy = self.env['mail.activity'].search([('res_id','=',res_id)])
		mail_activiy.unlink()

	def signature_creator(self):
		 self.env['carson.esignature'].create({
			'ref_id':self.id,
			'user_id':self.env.user.id,
			'sign_state':self.rof_state
			})

	def signature_unlinker(self):
		signature = self.env['carson.esignature'].search([
			('ref_id','=',self.id),
			('user_id','=',self.env.user.id),
			('sign_state','=',self.rof_state)
			])
		if signature.exists():
			_logger.info('Signature ID: ' + str(signature.id))

	def state_rejecter(self):
		current_list = self.rof_state_values
		for x,y in enumerate(current_list):
			if(self.rof_state in y):
				_logger.info('State that should be display is: ' + str(current_list[x-1]))
				self.write({'rof_state':current_list[x-1][0]})

	@api.multi
	def action_check_availability(self):
		self.ensure_one()
		if not self.rof_items:
			raise ValidationError(_('Please add an item to ROF to check availability.'))

		for line in self.rof_items:
			# # inv_loc = self.location_id
			inv_loc = line.location_id
			stock_quant = self.env['stock.quant'].sudo().search([('product_id','=',line.product_id.id),('location_id','=',inv_loc.id)])
			inv_qty = 0
			reserved_qty = 0
			for stock in stock_quant:
				inv_qty += stock.quantity
				reserved_qty += stock.reserved_quantity

			available_qty = inv_qty - reserved_qty

			line.sudo().write({
				'is_checked_available_qty': True,
				'available_qty': available_qty
			})
			line.sudo()._compute_qty()
			line.sudo()._compute_state()
			# line._check_availability()

		self._compute_done()

	@api.multi
	def unlink(self):
		for record in self:
			if record.rof_state not in ['draft','cancelled']:
				raise ValidationError(_('You can only delete draft or cancelled requisition orders.'))
		result = super(Rof, self).unlink()
		return result

	# @api.multi
	# def write(self, values):
	# 	rof_items = values.get('rof_items')
	# 	result = super(Rof,self).write(values)

	# 	if rof_items:
	# 		item_count = 0
	# 		to_manufacture = False
	# 		for item in rof_items:
	# 			_logger.info(item)
	# 			if item[2] and 'to_manufacture' in item[2]:
	# 				to_manufacture = item[2]['to_manufacture']
					
	# 			item_count += 1

	# 		_logger.info("HANNN")
	# 		_logger.info(to_manufacture)
	# 		if to_manufacture and self.env.user.has_group('carson_module.group_main_warehouseman'):
	# 			items = '<ul>'
	# 			production_items = self.rof_items.filtered(lambda item: item.state in ['production'])
	# 			for item in production_items:
	# 				items += "<li> %s </li>" % (item.name)

	# 			items += '<ul/>'
	# 			activity_summary = 'Request for production'
	# 			activity_text = 'Please review this Requistion Order for production. The following items are for production: <br/>%s' % (items)
	# 			self.activity_creator(activity_text,activity_summary,'group_production_manager')

	# 	return result

	@api.one
	def compute_has_for_production(self):
		if any(item.to_manufacture == True for item in self.rof_items):
			self.has_for_production = True

	def action_rof_req_production(self):
		items = '<ul>'
		production_items = self.rof_items.filtered(lambda item: item.to_manufacture == True)
		for item in production_items:
			items += "<li> %s </li>" % (item.name)

		items += '<ul/>'
		activity_summary = 'Request for production'

		if self.is_omapproved == True:
			self.write({'is_omapproved': False})
		if self.is_qsvalidated == True:
			self.write({'is_qsvalidated': False})
		self.write({'is_whmchecked': True})
		self._compute_state()

		activity_text = 'Please review this Requistion Order for production. The following items are for production: <br/>%s' % (items)
		self.activity_creator(activity_text,activity_summary,'group_production_manager')
		self.production_requested = True

	def action_update_purchase(self):
		for record in self:
			for po in record.po_items:
				if po.id not in record.po_item_ids.ids:
					record.write({'po_item_ids': [( 4, po.id)]})
				if po.rof_id:
					for line in po.order_line:
						for item in record.rof_items:
							if line.product_id == item.product_id:
								line.write({'rof_item_id': item.id})
						line.write({'rof_id': record.id})
			return True
				

class Rof_items(models.Model):
	_name = 'carson.rof.items'
	_description = 'Requisition Order Items'

	rof_item_id = fields.Many2one('carson.rof','Requisition Order')
	product_id = fields.Many2one('product.product', string='Item')
	location_dest_id = fields.Many2one('stock.location', required=False)
	location_id = fields.Many2one('stock.location', string="Source Location")
	is_checked_available_qty = fields.Boolean(default=False)
	ordered_qty = fields.Float('Ordered Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True)
	available_qty = fields.Float('Available Quantity', digits=dp.get_precision('Product Unit of Measure'))
	delivered_qty = fields.Float('Delivered Quantity', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_qty')
	reserved_qty = fields.Float('Reserved Quantity', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_qty')
	purchase_qty = fields.Float('Purchase Quantity', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_qty')
	# purchase_qty = fields.Float('Purchase Quantity', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_qty')
	satellite_qty = fields.Float('Satellite Quantity', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_qty')
	consumed_qty = fields.Float('Consumed Quantity', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_qty')
	manufacture_qty = fields.Float('Manufacture Quantity', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_qty')
	name = fields.Char('Description', index=True, required=True)	
	product_uom = fields.Many2one('product.uom', 'Unit of Measure', required=True)
	note = fields.Text('Notes')
	partner_id = fields.Many2one(
		'res.partner', 'Destination Address ',
		states={'done': [('readonly', True)]},
		help="Optional address where goods are to be delivered, specifically used for allotment")
	# picking_type_id = fields.Many2one('stock.picking.type', 'Operation Type')
	state = fields.Selection([
		('draft', 'New'), ('cancel', 'Cancelled'),
		('approval', 'Approval'),
		('available', 'Available'),
		('partial', 'Partially Available'),
		('delivered', 'Delivered'),
		('production', 'Production'),
		('purchase', 'For Purchase'),
		('satellite', 'In Satellite'),
		('consumed', 'Consumed'),
		('done', 'Done'),
		('cancelled', 'Cancelled'),], string='Status',
		copy=False, default='draft', index=True, readonly=True, compute='_compute_state', store=True,
		help="* New: When the ROF is created.\n"
			 "* Approval: This state can be seen when ROF is in approval stage.\n"
			 "* Available: This state is reached when an ROF item is available in stock after checking availability\n"
			 "* Delivered: When ROF items are delivered, it is set to \'Delivered\'.\n"
			 "* Purchase: When an ROF item is not available and for purchase, the state is \'For Purchase\'.")

	move_lines = fields.One2many('stock.move', 'rof_item_id', string="Stock Moves", copy=False)

	#Added Fields For Report Purposes
	#Daily Purchase Summary

	rof_name = fields.Char(related='rof_item_id.name', string="REQ")
	rof_project_name = fields.Char(related='rof_item_id.carson_project_id.name', string="Allocation")

	# is_delivered = fields.Float(compute='_compute_location')
	# is_satellite = fields.Float(compute='_compute_location')
	# is_consumed = fields.Float(compute='_compute_location')

	to_manufacture = fields.Boolean(string='To Manufacture')
	production_ids = fields.One2many('mrp.production', 'rof_item_id', string='Manufacturing Orders')

	#Method For Report Purposes
	@api.multi
	def getProject(self,docs):
		project_list =[]
		for doc in docs:
			if len(project_list) == 0:
				project_list.append(doc.rof_project_name)
			else:
				if doc.rof_project_name not in project_list:
					project_list.append(doc.rof_project_name)		
		return project_list	

	@api.model
	def getTotalRecordPerProject(self, project_name, docs):
		if docs:
			rof_items_obj = self.env['carson.rof.items'].sudo().search([('id','in', docs.ids),('rof_project_name','=', project_name)])
			if rof_items_obj:
				return len(rof_items_obj)
		return 1

	@api.model
	def getROF(self,project_name):	
		carson_project_obj = self.env['carson.projects'].sudo().search([('name','=', project_name)])
		if carson_project_obj:
			rof_obj = self.env['carson.rof'].sudo().search([('carson_project_id','=', carson_project_obj.id),('rof_state','=', 'inprogress')])
			if rof_obj:
				return rof_obj.ids
		return False

	@api.model
	def getProductListByProject(self, rof_id, docs):		
		rof_item_list =[]
		rof_items_obj = self.env['carson.rof.items'].search([('id','in', docs.ids),('rof_item_id','=', rof_id)])
		
		for rof_item in rof_items_obj:
			rof_item_list.append({
				'quantity': rof_item.ordered_qty,
				'product_uom': rof_item.product_uom.name,
				'particulars': rof_item.name,
				'req_name': rof_item.rof_name,
				'allocation': rof_item.rof_project_name,
				'no': len(rof_items_obj)})
		if rof_item_list:
			return rof_item_list
		return []

	@api.model
	def getSequence(self):
		ir_sequence_object = self.env['ir.sequence'].sudo().search([('code','=', 'daily.purchase.summary.report')])
		if ir_sequence_object:
			update_date = datetime.strptime(ir_sequence_object.write_date, '%Y-%m-%d %H:%M:%S').date()
			today_date = datetime.strptime(fields.Date.today(), '%Y-%m-%d').date()
			if update_date != today_date:
				ir_sequence_object.write({'number_next_actual':1})
			val = self.env['ir.sequence'].next_by_code('daily.purchase.summary.report') 
			return val or 'None'

	@api.model
	def getRequestedBy(self):
		carson_project_obj = self.env['carson.projects'].search([],limit=1)
		if carson_project_obj:
			carson_project_user_obj = self.env['carson.projects.users'].search([('carson_project_id','=',carson_project_obj.id),
                                                                            ('groups','=', self.env.ref('carson_module.group_warehouse_supervisor').id)])
			if carson_project_user_obj:
				return carson_project_user_obj.user_id
		return False

	@api.model
	def getNotedBy(self):
		carson_project_obj = self.env['carson.projects'].search([],limit=1)
		if carson_project_obj:
			carson_project_user_obj = self.env['carson.projects.users'].search([('carson_project_id','=',carson_project_obj.id),
                                                                            ('groups','=', self.env.ref('carson_module.group_logistics_head').id)])
			if carson_project_user_obj:
				return carson_project_user_obj.user_id
		return False

	@api.model
	def getApprovedBy(self):
		carson_project_obj = self.env['carson.projects'].search([],limit=1)
		if carson_project_obj:
			carson_project_user_obj = self.env['carson.projects.users'].search([('carson_project_id','=',carson_project_obj.id),
                                                                            ('groups','=', self.env.ref('carson_module.group_purchasing_ceo').id)])
			if carson_project_user_obj:
				return carson_project_user_obj.user_id
		return False




	@api.model
	def getDateToday(self):
		date = datetime.strptime(fields.Date.today(), '%Y-%m-%d')
		dateToday = date.strftime("%B %d, %Y")
		return dateToday
	#End Method For Report Purposes

	@api.depends('rof_item_id.rof_state','delivered_qty','move_lines','move_lines.state')
	@api.multi
	def _compute_state(self):
		for record in self:
			
			if record.rof_item_id.rof_state == 'draft' and record.rof_item_id.rof_type in ['site','satellite']:
				record.state = 'draft'
			elif record.rof_item_id.rof_state == 'draft' and record.rof_item_id.rof_type == 'main':
				# Check Delivered
				if record.ordered_qty != 0:
					if record.delivered_qty >= record.ordered_qty:
						# Compute state if in satellite or consumed
						if record.satellite_qty >= record.ordered_qty:
							record.state = 'satellite'
						elif record.consumed_qty >= record.ordered_qty:
							record.state = 'consumed'
						else:
							record.state = 'delivered'
					elif record.available_qty >= record.ordered_qty:
						record.state = 'available'
					elif record.reserved_qty >= record.ordered_qty:
						record.state = 'available'
					elif record.available_qty != 0 and record.available_qty < record.ordered_qty:
						if record.reserved_qty != 0:
							record.state = 'available'
						elif record.available_qty < 0:
							record.state = 'purchase'
						else:
							record.state = 'partial'
					else:
						record.state = 'purchase'

						# Status checking for production
						if record.to_manufacture == True and record.rof_item_id.production_requested == True:
							record.state = 'production'

						check_qty = record.delivered_qty + record.reserved_qty
						if check_qty >= record.ordered_qty:
							record.state = 'partial'
					
				else:
					record.state = 'draft'
			elif record.rof_item_id.rof_state in ['submit','pending','picapproved','pmapproved',]:
				record.state = 'approval'
			elif record.rof_item_id.rof_state in ['omapproved','qsvalidated','whmchecked','whchecked','inprogress','done']:
				# Check Delivered
				if record.ordered_qty != 0:
					if record.delivered_qty >= record.ordered_qty:
						# Compute state if in satellite or consumed
						if record.satellite_qty >= record.ordered_qty:
							record.state = 'satellite'
						elif record.consumed_qty >= record.ordered_qty:
							record.state = 'consumed'
						else:
							record.state = 'delivered'
					elif record.available_qty >= record.ordered_qty:
						record.state = 'available'
					elif record.reserved_qty >= record.ordered_qty:
						record.state = 'available'
					elif record.available_qty != 0 and record.available_qty < record.ordered_qty:
						if record.reserved_qty != 0:
							record.state = 'available'
						elif record.available_qty < 0:
							record.state = 'purchase'
						else:
							record.state = 'partial'
					else:
						record.state = 'purchase'

						# Status checking for production
						if record.to_manufacture == True and record.rof_item_id.production_requested == True:
							record.state = 'production'

						check_qty = record.delivered_qty + record.reserved_qty
						if check_qty >= record.ordered_qty:
							record.state = 'partial'
				else:
					record.state = 'draft'
			# elif record.rof_item_id.rof_state == 'done':
			# 	record.state = 'done'
			elif record.rof_item_id.rof_state == 'cancelled':
				record.state = 'cancelled'

	@api.onchange('product_id')
	def onchange_product_id(self):
		product = self.product_id.with_context(lang=self.partner_id.lang or self.env.user.lang)
		self.name = product.partner_ref
		self.product_uom = product.uom_id.id

	# def _check_availability(self):
	# 	inv_loc = self.location_id
	# 	stock_quant = self.env['stock.quant'].sudo().search([('product_id','=',self.product_id.id),('location_id','=',inv_loc.id)])
	# 	inv_qty = 0
	# 	reserved_qty = 0
	# 	for stock in stock_quant:
	# 		inv_qty += stock.quantity
	# 		reserved_qty += stock.reserved_quantity

	# 	available_qty = inv_qty - reserved_qty

	# 	self.sudo().write({
	# 		'is_checked_available_qty': True,
	# 		'available_qty': available_qty
	# 	})

	@api.multi
	@api.depends('location_id','move_lines','move_lines.state')
	def _compute_qty(self):
		for record in self:
			delivered_qty = 0
			reserved_qty = 0
			purchase_qty = 0
			satellite_qty = 0
			consumed_qty = 0
			manufacture_qty = 0

			# location_id = record.rof_item_id.location_id or record.rof_item_id.warehouse_id.int_type_id.default_location_src_id
			# move_ids = record.rof_item_id.mapped('mtf_items').mapped('move_lines').filtered(lambda move: move.state in ['assigned','wh_super','logistic_head','done'] and move.location_id == location_id)
			location_id = record.location_id
			move_ids = record.mapped('move_lines').filtered(lambda move: move.state in ['assigned','done'])

			for move in move_ids:
				if not record.to_manufacture:
					if move.location_id == location_id:
						if move.state == 'done':
							if move.move_dest_ids and all(move.state in ['done'] for move in move.move_dest_ids):
								delivered_qty += move.quantity_done
							else:
								reserved_qty += move.product_uom_qty
						if move.state == 'assigned':
							reserved_qty += move.product_uom_qty
					else:
						# GET DELIVERED MOVES FROM PURCHASE FOR REQUEST FROM PRODUCTION
						if record.rof_item_id.rof_type == 'production' and move.location_dest_id.usage == 'internal' and move.state == 'done':
							delivered_qty += move.quantity_done
						else:
							if move.state == 'done' and not move.move_orig_ids:
								picking_id = move.sudo().mapped('picking_id')
								if not picking_id.is_transit and not picking_id.is_return and not picking_id.is_receive and not picking_id.is_consume:
									satellite_qty += move.quantity_done
								if picking_id.is_consume:
									consumed_qty += move.quantity_done

				# COMPUTE DELIVERY BY PRODUCTION
				else:
					
					if move.state == 'done' and move.location_id.usage != 'production':
						_logger.info("HELLO")
						picking_id = move.sudo().mapped('picking_id')
						if move.location_dest_id.usage == 'internal' and picking_id.is_receive and not picking_id.is_return:
							delivered_qty += move.quantity_done
							_logger.info("DELIVERED")
							_logger.info(delivered_qty)
						if picking_id.is_transit and not picking_id.is_return and not picking_id.is_receive:
							reserved_qty += move.product_uom_qty
							_logger.info("RESERVED")
							_logger.info(reserved_qty)
						if not picking_id.is_transit and not picking_id.is_return and not picking_id.is_receive and not picking_id.is_consume:
							satellite_qty += move.quantity_done
							_logger.info("SATELLITE")
							_logger.info(satellite_qty)
						if picking_id.is_consume:
							consumed_qty += move.quantity_done
							_logger.info("CONSUMED")
							_logger.info(consumed_qty)
					if move.state == 'assigned' and move.location_id.usage != 'production':
						reserved_qty += move.product_uom_qty


			if record.ordered_qty != 0 and record.state in ['purchase','partial','production']:
				purchase_qty = record.ordered_qty
				if delivered_qty != 0:
					purchase_qty -= delivered_qty
				if reserved_qty != 0:
					purchase_qty -= reserved_qty
				if record.available_qty and record.available_qty < record.ordered_qty:
					purchase_qty -= record.available_qty

			record.delivered_qty = delivered_qty
			record.reserved_qty = reserved_qty
			record.purchase_qty = purchase_qty
			record.satellite_qty = satellite_qty
			record.consumed_qty = consumed_qty
			if record.to_manufacture == True:
				record.manufacture_qty = purchase_qty

	def post_item_changes(self, current_product, new_product, current_product_qty, new_product_qty, current_product_uom, new_product_uom):

		message = '<ul class="o_mail_thread_message_tracking">'

		current_product_name = ''
		get_current_product = self.env['product.product'].search([('id','=',current_product)], limit=1)
		for product in get_current_product:
			current_product_name = product.name

		if current_product and new_product:
			# get_current_product = self.env['carson.rof.items'].search([('id','=',current_product)], limit=1)
			# for product in get_current_product:
			message += '<li> %s &#8594; ' % (current_product_name)


			get_new_product = self.env['product.product'].search([('id','=',new_product)])
			for product in get_new_product:
				message += ' %s </li>' % (product.name)

		if current_product_qty and new_product_qty:
			message += '<li> %s: %s &#8594; %s </li>' % (current_product_name,current_product_qty,float(new_product_qty))

		if current_product_uom and new_product_uom:
			get_new_product_uom = self.env['product.uom'].search([('id','=',new_product_uom)], limit=1)
			for uom in get_new_product_uom:
				message += '<li> %s: %s &#8594; %s </li>' % (current_product_name,current_product_uom.name,uom.name)

		message += '</ul>'

		# message = _('<ul class="o_mail_thread_message_tracking"><li>Tags: %s &#8594; %s</li></ul>') % (current_tags_name, new_tags_name)
		self.rof_item_id.message_post(body=message)

	@api.multi
	def write(self, values):
		current_product = self.product_id
		new_product = values.get('product_id')
		current_product_qty = self.ordered_qty
		new_product_qty = values.get('ordered_qty')
		current_product_uom = self.product_uom
		new_product_uom = values.get('product_uom')
		if new_product:
			self.post_item_changes(current_product.id, new_product, False, False, False, False)
		if new_product_qty or new_product_uom:
			self.post_item_changes(current_product.id, False, current_product_qty, new_product_qty, current_product_uom, new_product_uom)
		# if new_product_uom:
		# 	self.post_item_changes(current_product.id, False, current_product_qty, new_product_qty, current_product_uom, new_product_uom)

		result = super(Rof_items, self).write(values)
		return result

	@api.model
	def create(self, values):
		rof_id = values.get('rof_item_id')
		result = super(Rof_items, self).create(values)
		if result.rof_item_id:
			rof_id = self.env['carson.rof'].browse(result.rof_item_id.id)
			if rof_id and rof_id.rof_state != 'draft':
				message = 'Added new item to ROF: <ul class="o_mail_thread_message_tracking"> <li>Product: %s</li> <li>Quantity: %s</li> </ul>' % (result.name, result.ordered_qty)
				rof_id.message_post(body=message)

		return result

	@api.multi
	def unlink(self):
		for record in self:
			if record.state in ['delivered','satellite','consumed']:
				raise ValidationError(_('You cannot delete delivered/in satellite/consumed items.'))
			if record.rof_item_id:
				rof_id = record.rof_item_id
				if rof_id and rof_id.rof_state != 'draft':
					message = 'Removed an item from ROF: <ul class="o_mail_thread_message_tracking"> <li>Product: %s</li> </ul>' % (record.name)
					rof_id.message_post(body=message)

		result = super(Rof_items, self).unlink()
		return result

class Items(models.Model):
	_inherit = 'product.template'
	rof_item_id = fields.Many2one('carson.rof','Items')
	#categ_id =  fields.Selection([('consumable','Consumable'), ('special','Special Items')])


	@api.multi
	def write(self, vals):
		#Check if Record is being edited by Site QS
		SPECIAL_ITEM = 'SPECIAL ITEMS'
		if self.env.user.id != ADMIN:
			if self.env.ref('carson_module.group_site_qs').id in self.env.user.groups_id.ids:
				for prod_tmp in self:
					if prod_tmp.categ_id.complete_name.upper().find(SPECIAL_ITEM) < 0:
						raise UserError(_("User is not Allowed to Maintain the Item %s. Item is not in Special Items Category.") % prod_tmp.name)
		return super(Items, self).write(vals)


class Category(models.Model):
	_inherit = 'product.category'
	property_valuation =  fields.Selection(required=False)


	#@api.one
	#def checkCategoryIsSpecialItem(self):
	#	SPECIAL_ITEM = 'Special Items'
	#	still_loop = True
	#	do {
	#
#
#
#
#		}while(still_loop == True)
#
#		return False

	@api.model
	def create_category(self):
		self.env['product.category'].create({
			'name':'Special Items',
			'property_cost_method':'standard'
				})
		self.env['product.category'].create({
			'name':'Consumables',
			'property_cost_method':'standard'
			})

# class Material_transmittal(models.Model):
# 	_inherit = 'stock.picking'
# 	rof_id = fields.Many2one('carson.rof', 'Reference Number')

class PurchaseOrders(models.Model):
	_inherit = 'purchase.order'
	rof_ids = fields.Many2many('carson.rof', string='Requistion Orders')
	rof_id = fields.Many2one('carson.rof', 'Reference Number')
	area_id = fields.Many2one('carson.rof.area', string="Area", related='rof_id.area_id')
	zone_id = fields.Many2one('carson.rof.zone', string="Zone", related='rof_id.zone_id')
	project_id = fields.Many2one('carson.projects', string="Project", related='rof_id.carson_project_id')

class Esignature(models.Model):
	_inherit = 'res.users'
	e_signature = fields.Binary(string="E-Signature")
	signatory = fields.One2many('carson.esignature','user_id',string='Signatory')

	@api.multi
	def write(self, vals):
		if 'e_signature' in vals:
			self = self.sudo()
		res = super(Esignature, self).write(vals)
		return res

	@api.multi
	def preference_change_pin(self):
		return{
            #'type': 'ir.actions.client',
            #'tag': 'res.users.pin.wizard',
            #'target': 'new',
			'name': _('Change Pin'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'res.users.pin.wizard',
			'target': 'new',            
		}

class UsersPin(models.Model):
	_name = 'res.users.pin'
	user_id = fields.Many2one('res.users', string="Users")
	pin_numb = fields.Char(string='Pin Number', size=6)

	@api.model
	def maintainUserPin(self, user_id, pin_number):
		res_user_mod = self.env['res.users']
		res_user_pin_mode = self.env['res.users.pin']
		res_user_obj = res_user_pin_mode.search([('user_id', '=', user_id)])
		if res_user_obj:
			res_user_obj.write({'pin_numb': pin_number})
		else:
			res_user_pin_mode.create({'user_id':user_id, 'pin_numb':pin_number})
		return True

class UserEsignature(models.Model):
	_name = 'carson.esignature'
	date_signed = fields.Date('Date Signed', default=datetime.today())
	user_id = fields.Many2one('res.users', 'User')
	ref_id = fields.Many2one('carson.rof', 'Reference Number')
	picking_id = fields.Many2one('stock.picking', 'Transmittal Reference')
	sign_state = fields.Char(string='State')


class PurchaseAgreements(models.Model):
	_inherit="purchase.requisition"
	rof_id = fields.Many2one('carson.rof', 'Reference Number')


class ProductInventory(models.Model):
	_name = 'stock.inventory'
	_inherit = ['stock.inventory','mail.thread', 'mail.activity.mixin']
	state = fields.Selection([('draft', 'Draft'),('cancel', 'Cancelled'),('confirm', 'In-progress'),
		('verified', 'Verified'),('done','Validated')])

	@api.multi
	def action_verified(self):
		if self.state == 'confirm':
			self.write({'state': 'verified'})

		return True


	@api.multi
	def write(self,values):

		if 'stop_write_recursion' not in self.env.context:
			ProductInventory.product_post_activity(self,'Pending approval of Inventory adjustment form','Please review this Inventory Adjustment for you approval.')

		return super(ProductInventory,self).write(values)


	def product_post_activity(self,activity_text,activity_summary):
		_logger.info('Activity Creation Function')
		activity_type = self.env['mail.activity.type'].search([('id','in',[4])], limit=1)
		model_orig = self.env['ir.model'].search([('name','=','Inventory')])
		model = self.env['stock.inventory'].search([('id', '=', self.id)])
		user = self.env.user

		#if len(model.message_follower_ids) > 0:
		#	for x in model.message_follower_ids:
		#		_logger.info('Follower Name: ' + str(x.partner_id.user_id.name))
		#		if x.partner_id.user_id.has_group('carson_module.group_op_manager'):
		#			user = x.partner_id.user_id


		record = self.env['mail.activity'].with_context(stop_write_recursion=1).create({
			'activity_type_id': activity_type.id,
			'res_id': model.id,
			'res_model_id': model_orig.id,
			'date_deadline': datetime.today(),
			'user_id':user.id,
			'note': activity_text,
			'summary':activity_summary
			})

		return record



class CarsonProjects(models.Model):
	_name = 'carson.projects'
	_inherit = ['mail.thread', 'mail.activity.mixin']

	name = fields.Char('Carson Project Name', required=True)
	project_rofs = fields.One2many('carson.rof','carson_project_id', string='Requisition Order Form', track_visibility='onchange')
	company_id = fields.Many2one('res.partner', string='Company',required=True )
	date_deadline = fields.Date('Deadline')
	project_users = fields.One2many('carson.projects.users','carson_project_id', string='Authorized Users', track_visibility='onchange')
	warehouse_id = fields.Many2one('stock.warehouse', 'Main Warehouse', ondelete='cascade', required=True)
	site_warehouse_id = fields.Many2one('stock.warehouse', 'Site Warehouse', ondelete='cascade', required=True)
	location_dest_id = fields.Many2one('stock.location', string='Default Finished Product Location', required=True)

	# Purchase Order Sequence of Project
	purchase_seq_id = fields.Many2one('ir.sequence', string='Purchase Order Sequence')
	prod_purchase_seq_id = fields.Many2one('ir.sequence', string='Production Purchase Order Sequence')

	@api.model
	def create(self, vals):

		record = super(CarsonProjects,self).create(vals)

		if len(record.project_users) < 1:
			raise exceptions.ValidationError("You must assign approvers for this project")

		warehouse_ids = self.env['stock.warehouse'].sudo().search([])
		for warehouse in warehouse_ids:
			warehouse.sudo()._get_projects()

		return record

	@api.multi
	def write(self, vals):
		res = super(CarsonProjects, self).write(vals)
		# Set Projects and Users in Warehouse to add restriction
		warehouse_ids = self.env['stock.warehouse'].sudo().search([])
		for warehouse in warehouse_ids:
			warehouse.sudo()._get_projects()
		return res

	@api.multi
	def unlink(self):
		for record in self:
			if any(rof.rof_state not in ['draft','cancelled'] for rof in self.project_rofs):
				raise ValidationError(_('You can only delete project with draft or cancelled requisition orders.'))
		result = super(CarsonProjects, self).unlink()
		return result

class CarsonProjectUsers(models.Model):
	_name = 'carson.projects.users'

	name = fields.Char('Carson Users')
	# value2 = fields.Integer(compute="_value_pc")
	groups = fields.Many2one('res.groups', string='Role', domain=lambda self: [('category_id','=',self.env.ref('carson_module.carson_module_management').id )] )
	user_id = fields.Many2one('res.users',string='Name',domain="[('groups_id','=',groups)]" )
	carson_project_id = fields.Many2one('carson.projects',string='Project',readonly=True)

class ResPartner(models.Model):
	_inherit = 'res.partner'
	fax_number = fields.Char('Telefax')

# class MailActivity(models.Model):
# 	_inherit = 'mail.activity'
# 	_order = 'date_deadline, create_date DESC'