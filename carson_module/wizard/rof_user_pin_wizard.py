# -*- coding: utf-8 -*-

#from odoo import fields, models, api exceptions, _
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import ValidationError

class ROFUsersPinVerificationWiz(models.TransientModel):
	_name = 'rof.user.pin.wizard'
	_description = 'ROF User PIN for OM'

	def _default_carson_rof(self):
		carson_rof = self.env['carson.rof'].browse(self._context.get('active_id'))
		return carson_rof


	rof_id = fields.Many2one('carson.rof', string="Users", default=_default_carson_rof)
	pin_numb = fields.Char(string='Pin Number', size=6, required=True)

	@api.one
	def apply(self):
		rof_id = self.rof_id
		carson_project = self.rof_id.carson_project_id.id
		project_users = self.env['carson.projects.users'].search([('carson_project_id', '=', carson_project), ('groups','=', self.env.ref('carson_module.group_op_manager').id)])
		if project_users:

			#Search the Pin number and Check Verified
			res_users_pins_obj = self.env['res.users.pin'].search([('user_id','=', project_users.user_id.id),('pin_numb','=', self.pin_numb)])
			if res_users_pins_obj:				
				
				res = rof_id.write({'is_submitted': False,
									'is_pending': False,
									'is_omapproved': True,})
				rof_id.activity_creator('Please review this Requisition Order for you approval.','Pending approval of Requisition Order','group_main_warehouseman')
			else:
				raise ValidationError(_('Wrong Pin Number.'))
		return True


class ROFUsersPinVerificationWiz2(models.TransientModel):
	_name = 'rof.user.pin.wizard2'
	_description = 'ROF User PIN for PIC->PM->OM'

	def _default_carson_rof(self):
		carson_rof = self.env['carson.rof'].browse(self._context.get('active_id'))
		return carson_rof

	def _default_carson_user_id(self):
		carson_rof = self.env['carson.rof'].browse(self._context.get('active_id'))
		if not carson_rof.is_verifiedviapin_om and carson_rof.is_verifiedviapin_pic == True and carson_rof.is_verifiedviapin_pm == True:
			project_users = self.env['carson.projects.users'].search([('carson_project_id', '=', carson_project),('groups','=', self.env.ref('carson_module.group_op_manager').id)])
			if project_users:
				return project_users.user_id
		elif not carson_rof.is_verifiedviapin_pm and carson_rof.is_verifiedviapin_pic == True and not carson_rof.is_verifiedviapin_om:
			project_users = self.env['carson.projects.users'].search([('carson_project_id', '=', carson_project),('groups','=', self.env.ref('carson_module.group_project_manager').id)])
			if project_users:
				return project_users.user_id
		return False




	#@api.model
	def _filterbyrof_project_and_grp(self):
		carson_rof = self.env['carson.rof'].browse(self._context.get('active_id'))
		carson_project = carson_rof.carson_project_id.id
		project_users = self.env['carson.projects.users'].search([('carson_project_id', '=', carson_project),
																  ('groups','in', [self.env.ref('carson_module.group_poc').id,
																					self.env.ref('carson_module.group_project_manager').id,
																					self.env.ref('carson_module.group_op_manager').id])])
		user_ids = []
		for project_user in project_users:
			user_ids.append(project_user.user_id.id)
		return [('id', 'in', user_ids)]



	rof_id = fields.Many2one('carson.rof', string="ROF", default=_default_carson_rof)
	user_id = fields.Many2one('res.users', string='Users', domain=_filterbyrof_project_and_grp)	
	is_verifiedviapin_pic = fields.Boolean(related='rof_id.is_verifiedviapin_pic', string="Accepted by PIC?") 
	is_verifiedviapin_pm = fields.Boolean(related='rof_id.is_verifiedviapin_pm', string="Accepted by PM?")
	is_verifiedviapin_om = fields.Boolean(related='rof_id.is_verifiedviapin_om', string="Accepted by OM?")
	pin_numb = fields.Char(string='Pin Number', size=6, required=True)

	@api.one
	def apply(self):
		rof_id = self.rof_id
		carson_project = self.rof_id.carson_project_id.id
		res_users_pins_obj = self.env['res.users.pin'].search([('pin_numb','=', self.pin_numb),('user_id','=',self.user_id.id)])
		message_header = ""
		message_str = "<strong>ROF Accepted using PIN Verification</strong>  <br/> <ul>%s</ul>"
		if res_users_pins_obj:
			#ROFUsersPinVerificationWiz
			project_users = self.env['carson.projects.users'].search([('carson_project_id', '=', carson_project), ('user_id','=', res_users_pins_obj.user_id.id)])
			if project_users:
				#PIC
				li_str =""
				if project_users.groups == self.env.ref('carson_module.group_poc') and not rof_id.is_verifiedviapin_pic:
					rof_id.write({'is_verifiedviapin_pic': True})
					message_header = "<strong>ROF Accepted using PIN Verification</strong>  <br/> <ul>%s</ul>"
					li_str += "<li>%s: %s </li>" %('Verified by', res_users_pins_obj.user_id.name)
					li_str += "<li>%s: %s </li>" %('Authorized as', self.env.ref('carson_module.group_poc').name)

					self.env['carson.esignature'].create({
														'ref_id':rof_id.id,
														'user_id':res_users_pins_obj.user_id.id,
														'sign_state':rof_id.rof_state
														})


				#PM
				if project_users.groups == self.env.ref('carson_module.group_project_manager') and not rof_id.is_verifiedviapin_pm:
					rof_id.write({'is_verifiedviapin_pm': True})
					message_header = "<strong>ROF Accepted using PIN Verification</strong>"
					li_str += "<li>%s: %s </li>" %('Verified by', res_users_pins_obj.user_id.name)
					li_str += "<li>%s: %s </li>" %('Authorized as', self.env.ref('carson_module.group_project_manager').name)


					self.env['carson.esignature'].create({
														'ref_id':rof_id.id,
														'user_id':res_users_pins_obj.user_id.id,
														'sign_state':rof_id.rof_state
														})
				#OM
				if project_users.groups == self.env.ref('carson_module.group_op_manager') and not rof_id.is_verifiedviapin_om:
					rof_id.write({'is_verifiedviapin_om': True})
					message_header = "<strong>ROF Accepted using PIN Verification</strong>"
					li_str += "<li>%s: %s </li>" %('Verified by', res_users_pins_obj.user_id.name)
					li_str += "<li>%s: %s </li>" %('Authorized as', self.env.ref('carson_module.group_op_manager').name)


					self.env['carson.esignature'].create({
														'ref_id':rof_id.id,
														'user_id':res_users_pins_obj.user_id.id,
														'sign_state':rof_id.rof_state
														})

				if len(li_str) > 0:
					
					message_str = message_str %(li_str)
					rof_id.message_post(body=message_str)

				if rof_id.is_verifiedviapin_om == True and rof_id.is_verifiedviapin_pic == True and rof_id.is_verifiedviapin_pm == True:
					res = rof_id.write({'is_submitted': False,
										'is_pending': False,
										'is_omapproved': True,})
					rof_id.activity_creator('Please review this Requisition Order for you approval.','Pending approval of Requisition Order','group_main_warehouseman')
		else:
			raise ValidationError(_('Wrong Pin Number.'))
		return True