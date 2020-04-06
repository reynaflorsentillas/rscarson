import logging
from datetime import datetime
from odoo import models, fields, api, exceptions, _
from datetime import date
from odoo.tools.translate import _
from odoo.tools.float_utils import float_compare

from odoo.exceptions import UserError, AccessError
_logger = logging.getLogger('models')
from datetime import datetime  

#OLD STATUS
#        ('draft', 'RFQ'),
#        ('sent', 'RFQ Sent'),
#        ('to approve', 'To Approve'),
#        ('validate_purchasing_ceo', 'For Validation by RMT'),
#        ('validate_purchasing_qs', 'QS - Supervisor'),
#        ('validate_purchasing_head', 'Purchasing Supervisor'),
#        ('validate_logistic_head', 'Logistic Head'),
#        ('validate_purchasing_boq', 'BOQ Staff'),
#        ('validate_purchasing_boq_head', 'BOQ Head'),
#        ('validate_purchasing_cost', 'COST'),
#        ('validate_accounting_staff_qs', 'Accounting Staff - QS'),
#        ('validate_purchasing_ap_head', 'AP-Head'),
#        ('validate_purchasing_cfo', 'For Validation by SCT'),
#        ('purchase', 'Purchase Order'),
#        ('done', 'Locked'),
#        ('cancel', 'Cancelled')

class PurchaseOrder(models.Model):
	_inherit = "purchase.order"

	READONLY_STATES = {
			'purchase': [('readonly', True)],
			'done': [('readonly', True)],
			'cancel': [('readonly', True)],
	}    

	has_special_items = fields.Boolean(compute='_compute_has_special_items')
	move_to_acct_staff_qs = fields.Boolean(compute='_compute_acct_staff_qs')
	move_to_acct_ap_head = fields.Boolean(compute='_compute_acct_ap_head')

	#move_to_purch_staff_qs = fields.Boolean(compute='_compute_pruchasing_staff_qs')
	#move_to_purch_ap_head = fields.Boolean(compute='_compute_pruchasing_ap_head')

	#For CFO
	allow_to_approve_by_cfo = fields.Boolean(compute='_compute_allowed_by_to_approve_by_cfo')
	allow_to_confirm_po = fields.Boolean(compute='_compute_allow_to_confirmed_order')

	is_approved_by_ceo = fields.Boolean('Approved by CEO',track_visibility='onchange', copy=False)
	is_approved_by_cfo = fields.Boolean('Approved by CFO',track_visibility='onchange', copy=False)

	is_po_paid_by_cash = fields.Boolean('Cash Transaction',track_visibility='onchange', copy=False, states=READONLY_STATES)
	is_pocash_skip_to_ap_head = fields.Boolean('Cash Transaction Skip')

	is_pocash_apprv_loghead = fields.Boolean('Cash Transaction Validated By Warehouse Head')
	is_pocash_apprv_purchasing_head = fields.Boolean('Cash Transaction Validated By Purchasing Head')
	is_pocash_apprv_auditor = fields.Boolean('Cash Transaction Validated By Auditor')
	is_pocash_apprv_ceo = fields.Boolean('Cash Transaction Validated By CEO')

	is_ready_to_apprv_draft_ceo = fields.Boolean('Ready for Approval')


	allow_to_pocash_appov = fields.Boolean(compute='_allow_to_pocash_appov')

	allow_to_pocash_appov_loghead = fields.Boolean(compute='_compute_allow_to_pocash_appov_loghead')
	allow_to_pocash_appov_phead = fields.Boolean(compute='_compute_allow_to_pocash_appov_phead')
	allow_to_pocash_appov_audit = fields.Boolean(compute='_compute_allow_to_pocash_appov_audit')


	e_signature = fields.One2many('purchase.order.esign','purchase_id', string='E-Signature')
	daily_po_summary = fields.Char('Daily Purchase Summary')

	state = fields.Selection([
			('draft', 'Draft'), #
			('sent', 'For Validation Of CEO'), # Notify CeO -> Notify Purchasing QS
			('to approve', 'To Approve'),
			('validate_purchasing_ceo', 'For Validation By Purchasing QS'),  #QS Supervisor - Obselete No0 Use
			('validate_purchasing_qs', 'For Validation By Purchasing QS'),
			('validate_purchasing_head', 'For Validation By Purchasing Head' ),
			('validate_logistic_head', 'For Validation By Warehouse Head' ), #Logistic Head
			('validate_auditor', 'For Validation By Auditor' ), #Logistic Head
			('validate_purchasing_boq', 'For Validation By BOQ' ), #For Validation By Billing Quantity
			('validate_purchasing_boq_head', 'For Validation By BOQ Head' ),
			('validate_purchasing_cost', 'For Validation By Costing' ),
			('validate_accounting_staff_qs', 'For Validation by Accounting QS' ),
			('validate_purchasing_ap_head', 'For Validation By AP Head' ),
			('validate_purchasing_cfo', 'For Validation By CFO'),
			('validate_purchasing_confirmation', 'PO Confirmation'),
			('purchase', 'Purchase Order'),
			('done', 'Locked'),
			('cancel', 'Cancelled')
			], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')


	is_admin = fields.Boolean(compute='_compute_is_admin')
	has_multiple_rof = fields.Boolean(compute='_compute_multiple_rof')
	rof_ref_no = fields.Text(compute='_compute_multiple_rof', string='Requistion Orders')
	project_location = fields.Text(compute='_get_project_location')
	active = fields.Boolean(default=True, copy=False)

	def _compute_is_admin(self):

		# carson_project_id = self.sudo().rof_id and self.sudo().rof_id.sudo().carson_project_id and self.sudo().rof_id.sudo().carson_project_id.sudo().id or False
		# data = False

		context = self._context

		current_uid = context.get('uid')

		user_login = self.env['res.users'].search([('id','=',current_uid),('groups_id','in',[str(self.env.ref('carson_module.group_manager').id),str(self.env.ref('base.group_erp_manager').id),str(self.env.ref('base.group_system').id)])], limit=1)

		# x = 0
		if user_login:
			for group in user_login.groups_id.ids:
					groups = self.env['res.groups'].search([('id', 'in', [str(self.env.ref('carson_module.group_manager').id),str(self.env.ref('base.group_erp_manager').id),str(self.env.ref('base.group_system').id)])], limit=1)

					if groups:
						self.allow_to_confirm_po = False
						# self.is_admin = True
						# if str(self.allow_to_confirm_po) == 'True':
						# 	self.is_admin = True

					else:
						self.allow_to_confirm_po = True
						# self.is_admin = False

		# _logger.info(str(self.is_admin or self.allow_to_confirm_po))
		# _logger.info(str(self.is_admin or self.allow_to_confirm_po))
		# _logger.info(str(self.is_admin))
		# _logger.info(str(self.allow_to_confirm_po))
		# raise Warning(str(data))
		# return self.allow_to_confirm_po({'allow_to_confirm_po': data})

	def _compute_multiple_rof(self):
		for record in self:
			has_multiple_rof = False
			rof_ref_no = record.rof_id.name or ''
			rof_names = []
			if len(record.rof_ids) > 1:
				has_multiple_rof = True
				for rof in record.rof_ids:
					if rof.name not in rof_names:
						rof_names.append(rof.name)

			if rof_names:
				rof_ref_no = ''
				for name in rof_names:
					if rof_ref_no:
						rof_ref_no += ', '
						rof_ref_no += name
					else:
						rof_ref_no += name

			record.has_multiple_rof = has_multiple_rof
			record.rof_ref_no = rof_ref_no

	def _get_project_location(self):
		for record in self:
			project_location = "%s" % (record.rof_id.project_id.name or '')
			if record.area_id or record.zone_id:
				project_location += " ("
				project_location += "%s %s" % (record.area_id.name or '',record.zone_id.name or '')
				project_location += ")"

			if record.has_multiple_rof:
				if all(record.project_id == line.project_id for line in record.order_line):
					project_name = record.rof_id.project_id.name
					location_names = []

					for line in record.order_line:
						if line.area_id or line.zone_id:
							location_name = "%s %s" % (str(line.area_id.name),str(line.zone_id.name))
							if location_name not in location_names:
								location_names.append(location_name)
					project_location = "%s" % (project_name)
					if location_names:
						project_location += " ("
						locations = ""
						for name in location_names:
							if not locations:
								locations += name
							else:
								locations += ", "
								locations += name
						project_location += locations
						project_location += ")"
				else:
					locations = ""
					for line in record.order_line:
						if locations:
							locations += ", "
						project_name = ""
						location_name = ""
						if line.project_id:
							project_name = line.rof_id.project_id.name

						if project_name:
							locations += project_name
							locations += " ("

						if location_name:
							location_name += ", "

						if line.area_id:
							location_name += str(line.area_id.name)
							location_name += " "
						if line.zone_id:
							location_name += str(line.zone_id.name)

						locations += location_name
						locations += ")"
					project_location = "%s" % (locations)
			record.project_location = project_location

	def _compute_allow_to_pocash_appov_loghead(self):
		self.allow_to_pocash_appov_loghead = False

		if self.state == 'validate_purchasing_confirmation' and self.is_pocash_skip_to_ap_head == True and \
			 (self.is_pocash_apprv_loghead == False and self.is_pocash_apprv_auditor == False and self.is_pocash_apprv_purchasing_head == False and self.is_pocash_apprv_ceo == False):
				self.allow_to_pocash_appov_loghead = True

	def _compute_allow_to_pocash_appov_audit(self):
		self.allow_to_pocash_appov_audit = False
		if self.state == 'validate_purchasing_confirmation' and self.is_pocash_skip_to_ap_head == True and \
			 (self.is_pocash_apprv_auditor == False and self.is_pocash_apprv_purchasing_head == False and self.is_pocash_apprv_ceo == False and self.is_pocash_apprv_loghead == True):
				self.allow_to_pocash_appov_audit = True

	def _compute_allow_to_pocash_appov_phead(self):
		self.allow_to_pocash_appov_phead = False
		if self.state == 'validate_purchasing_confirmation' and self.is_pocash_skip_to_ap_head == True and \
			 (self.is_pocash_apprv_auditor == True and self.is_pocash_apprv_loghead == True and self.is_pocash_apprv_purchasing_head == False and self.is_pocash_apprv_ceo == False):
				self.allow_to_pocash_appov_phead = True


	def _allow_to_pocash_appov(self):
		self.allow_to_pocash_appov = False
		if self.state == 'validate_purchasing_confirmation' and self.is_pocash_skip_to_ap_head == True and \
			(self.is_pocash_apprv_auditor == True and self.is_pocash_apprv_loghead == True and self.is_pocash_apprv_purchasing_head == True and self.is_pocash_apprv_ceo == False):
				self.allow_to_pocash_appov = True

	@api.model
	def create(self,vals):
		if vals.get('name', 'New') == 'New':
			def_purchase_order = self.env['ir.sequence'].search([('prefix','=','PO')], limit=1)
			if not def_purchase_order:
				raise UserError("No default purchase order sequence found!")
			if vals.get('rof_id'):
				rof_id = self.env['carson.rof'].browse(vals.get('rof_id'))
				purchase_seq_id = self.env['ir.sequence'].search([('id','=',rof_id.carson_project_id.purchase_seq_id.id)], limit=1)
				prod_purchase_seq_id = self.env['ir.sequence'].search([('id','=',rof_id.carson_project_id.prod_purchase_seq_id.id)], limit=1)
				if purchase_seq_id and rof_id.rof_type != 'production':
					vals['name'] = purchase_seq_id[0].next_by_id() or '/'
				elif prod_purchase_seq_id and rof_id.rof_type == 'production':
					vals['name'] = prod_purchase_seq_id[0].next_by_id() or '/'
				else:
					vals['name'] = def_purchase_order[0].next_by_id() or '/'
			else:
				vals['name'] = def_purchase_order[0].next_by_id() or '/'
		return super(PurchaseOrder, self).create(vals)

	#For Report Purposes
	@api.multi
	def getDateToday(self):
		self.ensure_one()
		date = datetime.strptime(fields.Date.today(), '%Y-%m-%d')
		#raise Warning(date)
		#raise Warning(date.strftime("%B %d, %Y"))
		dateToday = date.strftime("%B %d, %Y")
		return dateToday

	@api.multi
	def getReportHeaderValues(self, docs):
		if docs:
			for o in docs:
				company_street =''
				company_street_2 = ''
				company_city = ''
				if o.company_id.street:
					company_street = o.company_id.street
				if o.company_id.street2:
					company_street_2 = o.company_id.street2
				if o.company_id.city:
					company_city = o.company_id.city

				return {'company_name': o.company_id.name, 
						'company_address': company_street + ' ' + company_street_2 + ' ' + company_city, 
						'date_order': o.date_order}
	@api.model
	def getSequence(self):
		# #self.ensure_one()
		# #Check Sequence Last Updated to Reset Sequence
		# ir_sequence_object = self.env['ir.sequence'].sudo().search([('code','=', 'purchase.order.cash.transaction.report')])
		# if ir_sequence_object:
		# 	#raise Warning(datetime.strptime(fields.Date.today(), '%Y-%m-%d').date())
		# 	update_date = datetime.strptime(ir_sequence_object.write_date, '%Y-%m-%d %H:%M:%S').date()
		# 	today_date = datetime.strptime(fields.Date.today(), '%Y-%m-%d').date()
		# 	if update_date != today_date:
				
		# 		ir_sequence_object.write({'number_next_actual':1})


		# 	val = self.env['ir.sequence'].next_by_code('purchase.order.cash.transaction.report') 
		# 	if val:
		# 		return val
		# return 'None'
		return self.name


	@api.model
	def getReportPreparedBy(self):
		#return [self.env.user.name, self.env.user.e_signature or False]
		return self.env.user or False

	@api.model
	def getCheckByLogisticHead(self):
		carson_project_obj = self.env['carson.projects'].search([],limit=1)
		if carson_project_obj:
			carson_project_user_obj = self.env['carson.projects.users'].search([('carson_project_id','=',carson_project_obj.id),('groups','=', self.env.ref('carson_module.group_logistics_head').id)])
			if carson_project_user_obj:
				#return [carson_project_user_obj.user_id.name, carson_project_user_obj.user_id.e_signature or False]
				return carson_project_user_obj.user_id or False
		return False

	@api.model
	def getCheckByAuditor(self):
		carson_project_obj = self.env['carson.projects'].search([],limit=1)
		if carson_project_obj:

			carson_project_user_obj = self.env['carson.projects.users'].search([('carson_project_id','=',carson_project_obj.id),('groups','=', self.env.ref('carson_module.group_purchasing_auditor').id)])
			if carson_project_user_obj:
				return carson_project_user_obj.user_id or False
		return False

	@api.model
	def getNotedByPOHead(self):
		carson_project_obj = self.env['carson.projects'].search([],limit=1)
		if carson_project_obj:        
			carson_project_user_obj = self.env['carson.projects.users'].search([('carson_project_id','=',carson_project_obj.id),('groups','=', self.env.ref('carson_module.group_purchasing_head').id)])
			if carson_project_user_obj:
				return carson_project_user_obj.user_id or False
		return False

	@api.model
	def getCEOEsign(self):
		if self.state in ['purchase','done']:
			carson_project_obj = self.env['carson.projects'].search([],limit=1)
			if carson_project_obj:
				carson_project_user_obj = self.env['carson.projects.users'].search([('carson_project_id','=',carson_project_obj.id),('groups','=', self.env.ref('carson_module.group_purchasing_ceo').id)])
				if carson_project_user_obj:
					#return [carson_project_user_obj.user_id.name, carson_project_user_obj.user_id.e_signature or False]
					return carson_project_user_obj.user_id or False
		return False

	@api.multi
	def getReportValues(self, docs):

		if docs:
			cash_po_ids =[]
			for doc in docs:
				if doc.is_po_paid_by_cash:
					cash_po_ids.append(doc)

			int_sequence = 1
			product_cash_lines = {}
			for cash_po_id in cash_po_ids:          
				for order_line in cash_po_id.order_line:
					str_key_name = order_line.product_id.name + '_' +  str(order_line.price_unit)
					if len(product_cash_lines) == 0:
					#First Record to Populated              
						product_cash_lines[str_key_name] = {
								'sequence':  int_sequence,
								'product_name' : order_line.product_id.name,
								'product_uom' : order_line.product_uom.name,
								'description' : order_line.name,
								'product_qty' : order_line.product_qty,
								'price_unit' : order_line.price_unit,
								'total' : (order_line.product_qty * order_line.price_unit),
								'price_dropdown_notes': order_line.price_dropdown_notes,
								'discount_rate': order_line.discount,
								'discount_amount': (order_line.product_qty * order_line.price_unit) - order_line.price_subtotal,
								'rof_name': order_line.rof_id.name or '',
								'project_name': order_line.project_id.name or '',
								}
						int_sequence += 1

					else:
						#To Check if product Exist in the List
						#Then Check if Product Line has different Unit Price
						if str_key_name in product_cash_lines:
							
							if product_cash_lines[str_key_name]['price_unit'] == order_line.price_unit:
								
								product_cash_lines[str_key_name]['product_qty'] = product_cash_lines[str_key_name]['product_qty'] +  order_line.product_qty
								product_cash_lines[str_key_name]['total'] = product_cash_lines[str_key_name]['total'] + (order_line.product_qty * order_line.price_unit)

							else:
								product_cash_lines[str_key_name] = {
								'sequence':  int_sequence,
								'product_name' : order_line.product_id.name,
								'product_uom' : order_line.product_uom.name,
								'description' : order_line.name,
								'product_qty' : order_line.product_qty,
								'price_unit' : order_line.price_unit,
								'total' : (order_line.product_qty * order_line.price_unit),
								'price_dropdown_notes': order_line.price_dropdown_notes,
								'discount_rate': order_line.discount,
								'discount_amount': (order_line.product_qty * order_line.price_unit) - order_line.price_subtotal,
								'rof_name': order_line.rof_id.name or '',
								'project_name': order_line.project_id.name or '',}
								int_sequence += 1
						else:
								product_cash_lines[str_key_name] = {
								'sequence':  int_sequence,
								'product_name' : order_line.product_id.name,
								'product_uom' : order_line.product_uom.name,
								'description' : order_line.name,
								'product_qty' : order_line.product_qty,
								'price_unit' : order_line.price_unit,
								'total' : (order_line.product_qty * order_line.price_unit),
								'price_dropdown_notes': order_line.price_dropdown_notes,
								'discount_rate': order_line.discount,
								'discount_amount': (order_line.product_qty * order_line.price_unit) - order_line.price_subtotal,
								'rof_name': order_line.rof_id.name or '',
								'project_name': order_line.project_id.name or '',}
								int_sequence += 1

			return product_cash_lines
		return False
	#End For Report Purposes


	@api.one
	def validate_cash_transaction(self):
		#for_logistic_head_approval
		if 'for_logistic_head_approval' in self._context:
			if self._context['for_logistic_head_approval']:
				self.write({'is_pocash_apprv_loghead':True})

				self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_auditor').id, 
										   'This PO has been approved for CASH transaction by Warehouse Head.')


		#for_auditor_approval
		if 'for_auditor_approval' in self._context:
			if self._context['for_auditor_approval']:
				self.write({'is_pocash_apprv_auditor':True,
										'state': 'validate_purchasing_confirmation'})
				#group_purchasing_head
				self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_staff_cash').id, 
														'This PO has been approved for CASH transaction.')

				self.saveInfo(self.id, 
				  'validate_auditor',
				  self._uid, 
				  self.env.ref('carson_module.group_purchasing_auditor').id, 
				  'Audited By')


		if 'for_ceo_approval' in self._context:
			if self._context['for_ceo_approval']:
				self.write({'is_pocash_apprv_ceo':True})


				self.saveInfo(self.id, 
				  'validate_purchasing_confirmation',
				  self._uid, 
				  self.env.ref('carson_module.group_purchasing_auditor').id, 
				  'Audited By')

				#self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_staff').id, 
				#                           'This PO has been approved for CASH transaction by CEO. Please proceed.')

		if 'for_purchasing_head_approval' in self._context:
			if self._context['for_purchasing_head_approval']:
				self.write({'is_pocash_apprv_purchasing_head':True})

				self.getCreateMailActivity(self.env.ref('carson_module.group_logistics_head').id, 
																	 'This PO has been approved for CASH transaction by Purchasing Head.')
		

	@api.model
	def removeAllSignature(self, purchase_id):
		return self.env['purchase.order.esign'].sudo().removeAllSignature(purchase_id)

	@api.model
	def rejectAllSignature(self, purchase_id):
		return self.env['purchase.order.esign'].sudo().rejectAllSignature(purchase_id)

	@api.multi
	def write(self,vals):
		#raise Warning(vals['order_line'])

		for order in self:                      
			if 'order_line' in vals:
				order_list = []
				order_list_info = {}
				new_exist_list = []
				for line in order.order_line:
					order_list.append(line.id)
					order_list_info[line.id] = {'product_name': line.name, 'product_qty': line.product_qty, 'price_unit': line.price_unit}
				for list_val in vals['order_line']:
					if list_val[0] == 1:
						new_exist_list.append(list_val[1])

				#This will Check the Record that will log as Deleted Record in Line
				final_lists =list(set(order_list) - set(new_exist_list))
				message_str = ""
				message_header = "<strong>Order Line has been Remove</strong>"
				for final_list in final_lists:
					message_str += "<ul><li>Product: %s </li><li>Quanity: %d </li> <li>Unit Price: %.2f </li>  </ul> <br/>" %(order_list_info[final_list]['product_name'], 
																																																								order_list_info[final_list]['product_qty'], 
																																																								order_list_info[final_list]['price_unit'])
				if len(message_str) > 0:
					self.message_post(body=message_header + message_str)

		res = super(PurchaseOrder, self).write(vals)
		if res:
			if 'order_line' in vals:
				message_str = ""
				message_header = "<strong>Order Line has been Added</strong>"
				for list_val in vals['order_line']:
					#Tuple for Added Records
					if list_val[0] == 0:
						#Get Product Info
						product_name = list_val[2]['name']
						product_qty = list_val[2]['product_qty']
						product_unit_price = list_val[2]['price_unit']
						message_str += "<ul><li>Product: %s </li><li>Quanity: %s </li> <li>Unit Price: %s </li>  </ul> <br/>" %(product_name, product_qty, product_unit_price)
				if len(message_str) > 0:
					self.message_post(body=message_header + message_str)

		return res

	@api.model
	def checkRoleExist(self, purchase_id=False, user_role=False):
		res = False
		esign_obj = self.env['purchase.order.esign'].sudo().search([('purchase_id', '=', purchase_id),
																																('user_role', '=', user_role),
																																('sequence', '!=', 1)])
		if esign_obj:
			res = True
		return res

	@api.model
	def saveInfo(self,purchase_id=False, state=False, user_id=False, user_role=False, report_user_penmanship=False):        
			return self.env['purchase.order.esign'].sudo().saveInfo(purchase_id, 
																														 state,
																														 user_id,
																														 user_role,
																														 report_user_penmanship)

	def getCreateMailActivity(self, group_id, note, summary=False):

			summary_final = summary or "PO Validation"
			res_model_id = self.env.ref('purchase.model_purchase_order').id
			res_id = self.id
			carson_project_id = self.sudo().rof_id and self.sudo().rof_id.sudo().carson_project_id and self.sudo().rof_id.sudo().carson_project_id.sudo().id or False
			if carson_project_id:
					carson_project_users_obj = self.env['carson.projects.users'].sudo().search([('carson_project_id','=', carson_project_id),
																																											('groups','=', group_id)])
					if carson_project_users_obj:
							for user in carson_project_users_obj:
									activity = self.env['mail.activity'].sudo().create({
																							'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
																							'note': _(note),
																							'res_id': res_id,
																							'res_model_id': res_model_id,
																							'summary': summary_final,
																							'user_id': user.user_id.id,
																							#'date_deadline': fields.date.today(),
																					})            
			return True

	@api.multi
	def print_quotation(self):
			#Check Prepared By
			self.write({'is_ready_to_apprv_draft_ceo': True})
			check_exist = self.env['purchase.order.esign'].sudo().search([('purchase_id','=', self.id),
																																		('state','=', 'sent')])
			if not check_exist:          
				self.saveInfo(self.id, 
										 'sent',
										 self._uid, 
										 self.env.ref('carson_module.group_purchasing_qs').id, 
										 'Prepared By')

			#Added This for the Changes
			check_approve_ceo_exist = self.env['purchase.order.esign'].sudo().search([('purchase_id','=', self.id),
																																								('state','=', 'approve_ceo'),
																																								('is_rejected','=', False)])
			#if not check_approve_ceo_exist:
			#  self.validate_from_sent_to_ceo_approval()

			return self.env.ref('carson_module.rpt_shoot_to_print_po_quote_selection').report_action(self)



	@api.one
	def validate_from_sent_to_ceo_approval(self):
			ir_attachment_obj = self.env['ir.attachment'].sudo().search([('res_model','=', 'purchase.order'),('res_id','=', self.id)])


			#if self.is_ready_to_apprv_draft_ceo == False:
			#  raise UserError(_('Please Print REQ first before Approving.'))

			message_str = "Please Validate PO."
			purchasing_staff_id = self.env.ref('carson_module.group_purchasing_staff').id
			if self.is_po_paid_by_cash:
				message_str = "Please Validate CASH transaction."
				purchasing_staff_id = self.env.ref('carson_module.group_purchasing_staff_cash').id

			if ir_attachment_obj:
					# User is Allowed By Cash Transaction Then
					if self.env.ref('carson_module.group_purchasing_staff_cash').id  in self.env.user.groups_id.ids and self.is_po_paid_by_cash:
						self.write({'state': 'validate_purchasing_confirmation', 
									'is_approved_by_cfo': True})

					else:
						if self.has_special_items:
								self.write({'state': 'validate_purchasing_qs', 
														'is_approved_by_ceo': True})

								self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_qs').id, message_str)
						else:
								self.write({'state': 'validate_purchasing_head', 
														'is_approved_by_ceo': True})
								self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_head').id, message_str)


					if self.rof_id:
						carson_project_user_obj = self.env['carson.projects.users'].sudo().search([('carson_project_id','=',self.rof_id.carson_project_id.id),
																								   ('groups','=', purchasing_staff_id)])

						check_exist = self.env['purchase.order.esign'].sudo().search([('purchase_id','=', self.id),('state','=', 'sent')])
						if not check_exist:
							for user in carson_project_user_obj:          
								self.saveInfo(self.id,'sent',user.user_id.id, self.env.ref('carson_module.group_purchasing_qs').id, 'Prepared By')

					#Get CEO Info
					carson_project_user_obj = self.env['carson.projects.users'].sudo().search([('carson_project_id','=',self.rof_id.carson_project_id.id),('groups','=', self.env.ref('carson_module.group_purchasing_ceo').id)])
					res_user_obj = self.env['res.users'].search([('groups_id', 'in',[self.env.ref('carson_module.group_purchasing_ceo').id])], limit=1) 
					self.saveInfo(self.id,'approve_ceo',carson_project_user_obj and carson_project_user_obj.user_id and carson_project_user_obj.user_id.id or  res_user_obj.id, 
								  self.env.ref('carson_module.group_purchasing_ceo').id, 
								  'Confirmed By')

			else:
					raise UserError(_('No File Attached Found.'))


	@api.one
	def validate_from_ap_head_to_cfo_approval(self):
			ir_attachment_obj = self.env['ir.attachment'].sudo().search([('res_model','=', 'purchase.order'),('res_id','=', self.id)])
			if not ir_attachment_obj:
					raise UserError(_('No File Attached Found.'))
			self.write({'state': "validate_purchasing_cfo"})


			purchasing_staff_id = self.env.ref('carson_module.group_purchasing_staff').id
			if self.is_po_paid_by_cash:
				purchasing_staff_id = self.env.ref('carson_module.group_purchasing_staff_cash').id


			self.getCreateMailActivity(purchasing_staff_id,                                    
																 "Please print and submit this PO for SCT's validation.",
																 'Print PO.')
			self.saveInfo(self.id, 
										'validate_purchasing_ap_head',
										self._uid, 
										self.env.ref('carson_module.group_purchasing_ap_head').id, 
										'Verified By')

	@api.one
	def confirm_by_cfo(self):
		ir_attachment_obj = self.env['ir.attachment'].sudo().search([('res_model','=', 'purchase.order'),('res_id','=', self.id)])
		if not ir_attachment_obj:
				raise UserError(_('No File Attached Found.'))      
		self.write({'is_approved_by_cfo': True,
								'state': 'validate_purchasing_confirmation'})

		purchasing_staff_id = self.env.ref('carson_module.group_purchasing_staff').id
		if self.is_po_paid_by_cash:
			purchasing_staff_id = self.env.ref('carson_module.group_purchasing_staff_cash').id

		self.getCreateMailActivity(purchasing_staff_id, 
															 'This PO has been approved.')

		#Get CFO Info
		res_user_obj = self.env['res.users'].search([('groups_id', 'in',[self.env.ref('carson_module.group_purchasing_cfo').id])], limit=1) 
		self.saveInfo(self.id, 
									'approve_cfo',
									res_user_obj.id, 
									self.env.ref('carson_module.group_purchasing_cfo').id, 
									'Approved By')


	@api.one
	def validate_purchasing_qs(self):
			self.write({'state': 'validate_purchasing_head'})

			message_str = "Please Validate PO."
			if self.is_po_paid_by_cash:
				message_str = "Please Validate CASH transaction."


			self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_head').id, 
																		 message_str)

			self.saveInfo(self.id, 
									 'validate_purchasing_qs',
									 self._uid, 
									 self.env.ref('carson_module.group_purchasing_qs').id, 
									 'Checked By')        
			return True

	@api.one
	def validate_purchasing_head(self):
			if self.is_po_paid_by_cash == True:
				
				self.write({'state': 'validate_logistic_head'})
				self.write({'is_approved_by_cfo': True,
										'is_pocash_skip_to_ap_head': True,
										'is_pocash_apprv_purchasing_head': True})
				self.getCreateMailActivity(self.env.ref('carson_module.group_logistics_head').id, 
																							'Please Validate CASH transaction.')
			else:
				self.write({'state': 'validate_logistic_head'})
				self.getCreateMailActivity(self.env.ref('carson_module.group_logistics_head').id, 
																								'Please Validate PO.')

				self.saveInfo(self.id, 
										 'validate_purchasing_head',
										 self._uid, 
										 self.env.ref('carson_module.group_purchasing_head').id, 
										 'Checked By')          
			return True

	@api.one
	def validate_purchasing_boq(self):
			# Change the Following SDS
			# self.write({'state': 'validate_purchasing_boq'})
			# users = self.env['res.users'].search([('groups_id', 'in',[self.env.ref('carson_module.group_purchasing_cost').id])])        
			# 'note': _('Purchasing COST kindly validate this Purchase Order.'),

			if self.is_po_paid_by_cash == True:
					self.write({'state': 'validate_auditor',
											'is_pocash_apprv_loghead': True})
					self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_auditor').id, 
																							'Please Validate CASH transaction.')
			else:
					self.write({'state': 'validate_purchasing_boq'})
					self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_boq').id, 
																									'Please Validate PO.')
			self.saveInfo(self.id, 
									 'validate_logistic_head',
									 self._uid, 
									 self.env.ref('carson_module.group_logistics_head').id, 
									 'Noted By')

			return True

	@api.one
	def validate_logistic_head_to_boq_staff(self):
			self.write({'state': 'validate_purchasing_boq'})
			self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_boq').id, 
																 'Please Validate PO.')
			return True

	@api.one
	def validate_purchasing_boq_staff_move_to_cost(self):
			self.write({'state': 'validate_purchasing_cost'})
			self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_cost').id, 
																 'Please Validate PO.')
			return True

	@api.one
	def validate_purchasing_boq_staff_move_to_boq_head(self):
			self.write({'state': 'validate_purchasing_boq_head'})
			self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_boq_head').id, 
																 'Please Validate PO.')
			self.saveInfo(self.id, 
									 'validate_purchasing_boq',
									 self._uid, 
									 self.env.ref('carson_module.group_purchasing_boq').id, 
									 'Validated By')

			return True   


	@api.one
	def validate_purchasing_cost(self):
			for_boq_head = False
			if self.state == 'validate_purchasing_boq_head':
					for_boq_head = True
			self.write({'state': 'validate_purchasing_cost'})
			self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_cost').id, 
																 'Please Validate PO.')
			if for_boq_head:
					self.saveInfo(self.id, 
											 'validate_purchasing_boq_head',
											 self._uid, 
											 self.env.ref('carson_module.group_purchasing_boq_head').id, 
											 'Checked and Validated By')            
			else:
					self.saveInfo(self.id, 
											 'validate_purchasing_boq',
											 self._uid, 
											 self.env.ref('carson_module.group_purchasing_boq').id, 
											 'Validated By')

			return True

	@api.one
	def validate_accounting_staff_qs(self):
			if self.has_special_items:
					self.write({'state': 'validate_accounting_staff_qs'})
					self.getCreateMailActivity(self.env.ref('carson_module.group_accounting_staff_qs').id, 
																 'Please Validate PO.')

			else:
					#skip accounting staff qs when it doesnt have a special item category
					self.write({'state': 'validate_purchasing_ap_head'})
					self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_ap_head').id, 
																 'Please Validate PO.')

			self.saveInfo(self.id, 
									 'validate_purchasing_costing',
									 self._uid, 
									 self.env.ref('carson_module.group_purchasing_cost').id, 
									 'Validated By')
			return True

	def _compute_has_special_items(self):
			if any(item.product_id.categ_id.name == 'Special Items' for item in self.order_line):
					self.has_special_items = True

	@api.one
	def validate_purchasing_ap_head(self):
			self.write({'state': 'validate_purchasing_ap_head'})
			self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_ap_head').id, 
																 'Please Validate PO.')
			self.saveInfo(self.id, 
									 'validate_accounting_staff_qs',
									 self._uid, 
									 self.env.ref('carson_module.group_accounting_staff_qs').id, 
									 'Validated By')
			return True

	@api.multi
	def button_reject(self):
		self.write({'state': 'cancel',
								'is_approved_by_ceo':False,
								'is_pocash_skip_to_ap_head':False,
								'is_pocash_apprv_loghead': False,
								'is_pocash_apprv_purchasing_head': False,
								'is_pocash_apprv_auditor': False,
								'is_pocash_apprv_ceo': False,
								'is_ready_to_apprv_draft_ceo': False,
								'is_approved_by_cfo': False,
								})
		self.rejectAllSignature(self.id)
		self.write({'state': 'draft'})


		if self.env.uid != self.create_uid.id:
				#Temporary Create a Rejection Activity
				activity = self.env['mail.activity'].sudo().create({
																		'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
																		'note': _("This Purchase Order has been rejected. Please coordinate with the last approver."),
																		'res_id': self.id,
																		'res_model_id': self.env.ref('purchase.model_purchase_order').id,
																		'summary': "POA Rejected.",
																		'user_id': self.create_uid.id,
																		#'date_deadline': fields.date.today(),
																})

	@api.multi
	def button_cancel(self):
		for order in self:
				for pick in order.picking_ids:
						if pick.state == 'done':
								raise UserError(_('Unable to cancel purchase order %s as some receptions have already been done.') % (order.name))
				for inv in order.invoice_ids:
						if inv and inv.state not in ('cancel', 'draft'):
								raise UserError(_("Unable to cancel this purchase order. You must first cancel related vendor bills."))

				# If the product is MTO, change the procure_method of the the closest move to purchase to MTS.
				# The purpose is to link the po that the user will manually generate to the existing moves's chain.
				if order.state in ('draft', 
													 'sent', 
													 'validate_purchasing_ceo',
													 'validate_purchasing_qs',
													 'validate_purchasing_head',
													 'validate_logistic_head',
													 'validate_purchasing_boq',
													 'validate_purchasing_boq_head',
													 'validate_purchasing_cost',
													 'validate_purchasing_cost',
													 'validate_accounting_staff_qs',
													 'validate_purchasing_ap_head',
													 'validate_purchasing_cfo',
													 'validate_auditor',
													 'to approve'):
						for order_line in order.order_line:
								if order_line.move_dest_ids:
										siblings_states = (order_line.move_dest_ids.mapped('move_orig_ids')).mapped('state')
										if all(state in ('done', 'cancel') for state in siblings_states):
												order_line.move_dest_ids.write({'procure_method': 'make_to_stock'})
												order_line.move_dest_ids._recompute_state()

				for pick in order.picking_ids.filtered(lambda r: r.state != 'cancel'):
						pick.action_cancel()

				order.order_line.write({'move_dest_ids':[(5,0,0)]})
		#To Track the Cancellation before to Make it a Draft      
		self.write({'state': 'cancel',
								'is_approved_by_ceo':False,
								'is_approved_by_cfo':False,
								'is_pocash_skip_to_ap_head':False,
								'is_pocash_apprv_loghead': False,
								'is_pocash_apprv_purchasing_head': False,
								'is_pocash_apprv_auditor': False,
								'is_pocash_apprv_ceo': False,
								'is_ready_to_apprv_draft_ceo': False,
								})

		#Purchasing Staff

		purchasing_staff_id = self.env.ref('carson_module.group_purchasing_staff').id
		if self.is_po_paid_by_cash:
			purchasing_staff_id = self.env.ref('carson_module.group_purchasing_staff_cash').id
			
		self.getCreateMailActivity(purchasing_staff_id, 
															 'This Purchase Order has been Cancelled. Kindly acknowledge by marking this activity as Done.', 
															 'Cancelled PO')

		if self.checkRoleExist(purchase_id=self.id, user_role=self.env.ref('carson_module.group_purchasing_qs').id):
				#Purchasing QS
				self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_qs').id, 
																	 'This Purchase Order has been Cancelled. Kindly acknowledge by marking this activity as Done.',
																	 'Cancelled PO')

		if self.checkRoleExist(self.id, self.env.ref('carson_module.group_purchasing_head').id):
				#Purchasing Head
				self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_head').id, 
																	 'This Purchase Order has been Cancelled. Kindly acknowledge by marking this activity as Done.',
																	 'Cancelled PO')

		if self.checkRoleExist(self.id, self.env.ref('carson_module.group_logistics_head').id):
				#Logistic Head
				self.getCreateMailActivity(self.env.ref('carson_module.group_logistics_head').id, 
																	 'This Purchase Order has been Cancelled. Kindly acknowledge by marking this activity as Done.',
																	 'Cancelled PO')  


		if self.checkRoleExist(self.id, self.env.ref('carson_module.group_purchasing_boq').id):
				#Purchasing BOQ
				self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_boq').id, 
																	 'This Purchase Order has been Cancelled. Kindly acknowledge by marking this activity as Done.',  
																		 'Cancelled PO')

		if self.checkRoleExist(self.id, self.env.ref('carson_module.group_purchasing_boq_head').id):
				#BOQ Head
				self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_boq_head').id, 
																	 'This Purchase Order has been Cancelled. Kindly acknowledge by marking this activity as Done.',
																	 'Cancelled PO',)

		if self.checkRoleExist(self.id, self.env.ref('carson_module.group_purchasing_cost').id):
				#Cost
				self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_cost').id, 
																	 'This Purchase Order has been Cancelled. Kindly acknowledge by marking this activity as Done.',
																		'Cancelled PO')

		if self.checkRoleExist(self.id, self.env.ref('carson_module.group_accounting_staff_qs').id):
				#Accounting QS
				self.getCreateMailActivity(self.env.ref('carson_module.group_accounting_staff_qs').id, 
																	 'This Purchase Order has been Cancelled. Kindly acknowledge by marking this activity as Done.',
																		'Cancelled PO')

		if self.checkRoleExist(self.id, self.env.ref('carson_module.group_purchasing_ap_head').id):
				#Ap Head
				self.getCreateMailActivity(self.env.ref('carson_module.group_purchasing_ap_head').id, 
																	 'This Purchase Order has been Cancelled. Kindly acknowledge by marking this activity as Done.',
																	 'Cancelled PO')

		self.removeAllSignature(self.id)


	@api.multi
	def button_confirm(self):
			for order in self:
					ir_attachment_obj = self.env['ir.attachment'].sudo().search([('res_model','=', 'purchase.order'),('res_id','=', order.id)])
					if not ir_attachment_obj:
							raise UserError(_('No File Attached Found.'))

					if order.is_po_paid_by_cash and self.env.ref('carson_module.group_purchasing_staff_cash').id  not in self.env.user.groups_id.ids:
						if order.is_pocash_apprv_loghead == False:
							raise UserError(_('PO Confirmation Denied.\nPurchase Order is a Cash Transaction and not yet Approve by Warehouse Head.'))

						if order.is_pocash_apprv_auditor == False:
							raise UserError(_('PO Confirmation Denied.\nPurchase Order is a Cash Transaction and not yet Approve by Auditor.'))

						if order.is_pocash_apprv_purchasing_head == False:
							raise UserError(_('PO Confirmation Denied.\nPurchase Order is a Cash Transaction and not yet Approve by Purchasing Head.'))

						if order.is_pocash_apprv_ceo == False:
							raise UserError(_('PO Confirmation Denied.\nPurchase Order is a Cash Transaction and not yet Approve by CEO.'))                            

					if order.state not in ['draft','sent','validate_purchasing_qs',
																	'validate_purchasing_head','validate_purchasing_boq',
																	'validate_purchasing_cost', 'validate_accounting_staff_qs',
																	'validate_purchasing_ap_head','validate_purchasing_cfo', 'validate_purchasing_confirmation']:
							continue
					order._add_supplier_to_product()
					# Deal with double validation process
					if order.company_id.po_double_validation == 'one_step'\
									or (order.company_id.po_double_validation == 'two_step'\
											and order.amount_total < self.env.user.company_id.currency_id.compute(order.company_id.po_double_validation_amount, order.currency_id))\
									or order.user_has_groups('purchase.group_purchase_manager'):
							order.button_approve()
					else:
							order.write({'state': 'to approve'})

			#Get CFO Info
			#res_user_obj = self.env['res.users'].search([('groups_id', 'in',[self.env.ref('carson_module.group_purchasing_cfo').id])], limit=1) 
			#self.saveInfo(self.id, 
			#              'approve_cfo',
			#              res_user_obj.id, 
			#              self.env.ref('carson_module.group_purchasing_cfo').id, 
			#              'Approved By')


			return True



	def _compute_allowed_by_to_approve_by_cfo(self):
		self.allow_to_approve_by_cfo = False
		if self.state == 'validate_purchasing_cfo' and self.is_approved_by_cfo == False:
				self.allow_to_approve_by_cfo = True

	def _compute_allow_to_confirmed_order(self):
		self.allow_to_confirm_po = True      
		#if self.state == 'validate_purchasing_cfo' and self.is_approved_by_cfo == True:
		if self.state == 'validate_purchasing_confirmation' and self.is_approved_by_cfo == True:
			self.allow_to_confirm_po = False



	def _compute_acct_staff_qs(self):
		self.move_to_acct_staff_qs = False
		if self.has_special_items == True and self.state == 'validate_purchasing_cost':
				self.move_to_acct_staff_qs = True

	def _compute_acct_ap_head(self):
		self.move_to_acct_ap_head = False
		if self.has_special_items == False and self.state == 'validate_purchasing_cost':
				self.move_to_acct_ap_head = True

	#RESERVED DONOT REMOVE
	#def _compute_pruchasing_staff_qs(self):
	#    self.move_to_purch_staff_qs = False
	#    if self.has_special_items == True and self.state == 'sent':
	#        self.move_to_purch_staff_qs = True

	#def _compute_pruchasing_ap_head(self):
	#    self.move_to_purch_ap_head = False
	#    if self.has_special_items == False and self.state == 'sent':
	#RESERVED DONOT REMOVE

	# @api.multi
	# def _clean_rof(self):
	# 	for record in self:
	# 		_logger.info("HELLO")
	# 		for rof in record.rof_ids:
	# 			_logger.info(rof)
	# 			in_order_line = False
	# 			for line in record.order_line:
	# 				if line.rof_id.id == rof.id:
	# 					in_order_line = True		
	# 			_logger.info(in_order_line)
	# 			if not in_order_line:
	# 				record.write({'rof_ids': [(3, rof.id)]})

	# RCS: OVERRIDE TO SET PROJECT TO TRANSFER GENERATED FROM PURCHASE
	@api.model
	def _prepare_picking(self):
		if not self.group_id:
			self.group_id = self.group_id.create({
				'name': self.name,
				'partner_id': self.partner_id.id
			})
		if not self.partner_id.property_stock_supplier.id:
			raise UserError(_("You must set a Vendor Location for this partner %s") % self.partner_id.name)
		return {
			'picking_type_id': self.picking_type_id.id,
			'partner_id': self.partner_id.id,
			'date': self.date_order,
			'origin': self.name,
			'location_dest_id': self._get_destination_location(),
			'location_id': self.partner_id.property_stock_supplier.id,
			'company_id': self.company_id.id,
			'carson_project_id': self.rof_id.carson_project_id.id,
		}

	# RCS: OVERRIDE TO NOTIFY WAREHOUSE RECEIPT
	@api.multi
	def _create_picking(self):
		StockPicking = self.env['stock.picking']
		for order in self:
			if any([ptype in ['product', 'consu'] for ptype in order.order_line.mapped('product_id.type')]):
				pickings = order.picking_ids.filtered(lambda x: x.state not in ('done','cancel'))
				if not pickings:
					res = order._prepare_picking()
					picking = StockPicking.create(res)
				else:
					picking = pickings[0]
				moves = order.order_line._create_stock_moves(picking)
				moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
				seq = 0
				for move in sorted(moves, key=lambda move: move.date_expected):
					seq += 5
					move.sequence = seq
				moves._action_assign()
				picking.message_post_with_view('mail.message_origin_link',
					values={'self': picking, 'origin': order},
					subtype_id=self.env.ref('mail.mt_note').id)
				# NOTIFICATION
				if all(move.state in ['assigned'] for move in moves):

					activity_text = "Please review this Material Transmittal for your approval"
					activity_summary = "Pending approval for Material Transmittal"
					activity_type = self.env['mail.activity.type'].search([('id','in',[4])], limit=1)
					users = picking.carson_project_id.project_users
					group = 'carson_module.group_warehouse_receipt'

					if users and group:
						group_id = self.env.ref(group)
						for user in users:
							if user.groups == group_id and user.user_id.has_group(group):
								self.env['mail.activity'].create({
									'activity_type_id': activity_type.id,
									'res_id': picking.id,
									'res_model_id': self.env.ref('carson_module.model_stock_picking').id,
									'date_deadline': datetime.today(),
									'user_id':user.user_id.id,
									'note': activity_text,
									'summary':activity_summary
								})
		return True

	@api.multi
	def button_archive_order(self):
		for record in self:
			record.active = False

	@api.multi
	def button_active_order(self):
		for record in self:
			record.active = True

class PurchaseOrderLine(models.Model):
	_inherit ='purchase.order.line'

	@api.depends('product_qty', 'price_unit', 'taxes_id', 'override_price_subtotal')
	def _compute_amount(self):
		result = super(PurchaseOrderLine, self)._compute_amount()
		for line in self:
			if line.override_price_subtotal > 0:
				line.update({
					'price_subtotal': line.override_price_subtotal,
				})
		return result

	# def _set_amount(self):
	# 	for line in self:
	# 		if line.override_price_subtotal:
	# 			line.update({
	# 				# 'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
	# 				# 'price_total': taxes['total_included'],
	# 				'price_subtotal': line.override_price_subtotal,
	# 			})

	#cost_indicator = fields.Selection([
	#    ('previous', 'P'), # P - previous (same as last PO/price in record)
	#    ('new', 'N'), # N - new (no record of past PO/price for the item)
	#    ('up', 'U'), # U - up (price increase from last PO/price in record)
	#    ('down', 'D')],  # D - down (price decrease from last PO/price in record)
	#    string='Cost Indicator', copy=False)

	cost_indicator = fields.Char(string='Cost Indicator', copy=False,track_visibility='onchange')

	rof_id = fields.Many2one('carson.rof', string='Requistion Order', copy=True)
	rof_item_id = fields.Many2one('carson.rof.items', 'Requistion Order Item', copy=True)
	area_id = fields.Many2one('carson.rof.area', string="Area", related='rof_id.area_id')
	zone_id = fields.Many2one('carson.rof.zone', string="Zone", related='rof_id.zone_id')
	project_id = fields.Many2one('carson.projects', string="Zone", related='rof_id.carson_project_id')

	# OVERRIDE / RCS
	# price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
	override_price_subtotal = fields.Monetary(string='Override Subtotal')

	@api.multi
	def write(self,vals):

		for line in self:      
			old_product_name = line.product_id.name
			old_qty = line.product_qty
			old_cost_indicator = line.cost_indicator
			old_price_unit = line.price_unit
			old_schedule_date = line.date_planned
			old_name = line.name
			old_product_uom = line.product_uom.name
			old_price_dropdown_notes = line.price_dropdown_notes

		res = super(PurchaseOrderLine, self).write(vals)
		if res:
			#cost_indicator = {
			#  'previous':  'P', #P - previous (same as last PO/price in record)
			#  'new': 'N', # N - new (no record of past PO/price for the item)
			#  'up': 'U', # U - up (price increase from last PO/price in record)
			#  'down': 'D', # D - down (price decrease from last PO/price in record)
			#   'None': 'None'}
			message_str = "<strong>Order line has been Updated</strong> <br/> <ul>%s</ul>"
			li_str =""
			if 'product_id' in vals:
				product_name =  old_product_name + "&#8594;" + self.env['product.product'].search([('id','=', vals['product_id'])], limit=1).name
				li_str += "<li>%s: %s </li>" %('Product', product_name)
				
			if 'product_qty' in vals:
				product_name = str(old_qty) + "&#8594;" + str(vals['product_qty'])
				li_str += "<li>%s: %s </li>" %('Quantity', product_name)

			if 'cost_indicator' in vals:
				product_name = str(old_cost_indicator or 'None') + "&#8594;" + str(vals['cost_indicator'] or 'None')
				li_str += "<li>%s: %s </li>" %('Cost Indicator', product_name)

			if 'price_dropdown_notes' in vals:
				product_name = str(old_price_dropdown_notes or 'None')  + "&#8594;" + str(vals['price_dropdown_notes'])
				li_str += "<li>%s: %s </li>" %('Notes', product_name)

			if 'price_unit' in vals:
				product_name = str(old_price_unit) + "&#8594;" + str(vals['price_unit'])
				li_str += "<li>%s: %s </li>" %('Unit Price', product_name)

			if 'name' in vals:
				product_name = str(old_name) + "&#8594;" + str(vals['name'] or 'None')
				li_str += "<li>%s: %s </li>" %('Description', product_name)

			if 'product_uom' in vals:
				product_name = str(old_product_uom) + "&#8594;" + self.env['product.uom'].search([('id','=', vals['product_uom'])], limit=1).name
				li_str += "<li>%s: %s </li>" %('Unit of Measurement', product_name)


			#if 'date_planned' in vals:
			#  product_name = str(old_schedule_date) + "&#8594;" + str(vals['date_planned'])
			#  li_str += "<li>%s: %s </li>" %('Schedule Date', product_name)

			if li_str:
				message_str = message_str %(li_str)
				self.order_id.message_post(body=message_str )
		return res

	# @api.multi
	# def unlink(self):
	# 	record = super(PurchaseOrderLine, self).unlink()
	# 	if record.rof_id
	# 	return record

	@api.multi
	def _prepare_stock_moves(self, picking):
		""" Prepare the stock moves data for one order line. This function returns a list of
		dictionary ready to be used in stock.move's create()
		"""
		self.ensure_one()
		res = []
		if self.product_id.type not in ['product', 'consu']:
			return res
		qty = 0.0
		price_unit = self._get_stock_move_price_unit()
		for move in self.move_ids.filtered(lambda x: x.state != 'cancel' and not x.location_dest_id.usage == "supplier"):
			qty += move.product_qty
		template = {
			'name': self.name or '',
			'product_id': self.product_id.id,
			'product_uom': self.product_uom.id,
			'date': self.order_id.date_order,
			'date_expected': self.date_planned,
			'location_id': self.order_id.partner_id.property_stock_supplier.id,
			'location_dest_id': self.order_id._get_destination_location(),
			'picking_id': picking.id,
			'partner_id': self.order_id.dest_address_id.id,
			'move_dest_ids': [(4, x) for x in self.move_dest_ids.ids],
			'state': 'draft',
			'purchase_line_id': self.id,
			'company_id': self.order_id.company_id.id,
			'price_unit': price_unit,
			'picking_type_id': self.order_id.picking_type_id.id,
			'group_id': self.order_id.group_id.id,
			'origin': self.order_id.name,
			'route_ids': self.order_id.picking_type_id.warehouse_id and [(6, 0, [x.id for x in self.order_id.picking_type_id.warehouse_id.route_ids])] or [],
			'warehouse_id': self.order_id.picking_type_id.warehouse_id.id,
			'rof_id': self.rof_id.id,
			'rof_item_id': self.rof_item_id.id,
		}
		diff_quantity = self.product_qty - qty
		if float_compare(diff_quantity, 0.0,  precision_rounding=self.product_uom.rounding) > 0:
			template['product_uom_qty'] = diff_quantity
			res.append(template)
		return res


class PurchaseESignature(models.Model):
	_name = 'purchase.order.esign'


	name = fields.Char(related='purchase_id.name')
	sequence = fields.Integer('Sequence')
	purchase_id = fields.Many2one('purchase.order', string='Purchase')
	state = fields.Char('State')

	user_id = fields.Many2one('res.users')
	user_role = fields.Many2one('res.groups')
	report_user_penmanship = fields.Char('User Role')
	date_stamp = fields.Date('Date Stamp')
	is_rejected = fields.Boolean('Rejected', default=False)


	@api.model
	def rejectAllSignature(self, purchase_id=False):
		esignature_obj = self.env['purchase.order.esign'].sudo().search([('purchase_id','=', purchase_id)])
		res = esignature_obj.write({'is_rejected': True})


		esignature_obj_1 = self.env['purchase.order.esign'].sudo().search([('purchase_id','=', purchase_id),('state','=','sent')])
		esignature_obj_1.unlink()
		
		return res


	@api.model
	def removeAllSignature(self, purchase_id=False):
		esignature_obj = self.env['purchase.order.esign'].sudo().search([('purchase_id','=', purchase_id)])
		res = esignature_obj.unlink()
		
		return res



	@api.model
	def getInfo(self, purchase_id=False, state=False):
			esignature_obj = self.env['purchase.order.esign'].sudo().search([('purchase_id','=', purchase_id),
																															 ('state','=', state),
																															 ('is_rejected','=', False)], limit=1)
			raise Warning(esignature_obj)
			if esignature_obj:
					return {
							'user_id':  esignature_obj.user_id,
							'user_role':  esignature_obj.user_role,
							'date_stamp':  esignature_obj.date_stamp,
							'report_user_penmanship': esignature_obj.report_user_penmanship}
			return False

	@api.model
	def saveInfo(self,purchase_id=False, state=False, user_id=False, user_role=False, report_user_penmanship=False):
			purchase_order_obj = self.env['purchase.order'].sudo().search([('id','=', purchase_id)])
			esignature_obj = self.env['purchase.order.esign'].sudo().search([('purchase_id','=', purchase_id),('is_rejected','=', False)], limit=1, order="sequence desc")
			res = False
			if purchase_order_obj:        
					res = esignature_obj.create({
							'purchase_id': purchase_id,
							'user_id': user_id,
							'date_stamp': fields.Date.today(),
							'state': state,
							'user_role':user_role,
							'report_user_penmanship': report_user_penmanship,
							'sequence':esignature_obj.sequence + 1,})
			return res


