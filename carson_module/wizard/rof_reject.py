# -*- coding: utf-8 -*-
# Copyright YEAR(S), AUTHOR(S)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models
from datetime import datetime

class CarsonRofReject(models.TransientModel):
	_name = 'carson.rof.reject'
	_description = 'Wizard to reject Requisition Order'

	def _default_rof(self):
		return self.env['carson.rof'].browse(self._context.get('active_id'))

	rof_id = fields.Many2one('carson.rof', string='Requisition Order', default=_default_rof, required=True)
	reason = fields.Char(required=True)

	def apply(self):
		self.ensure_one()  
		rof = self.rof_id
		rof.signature_unlinker()

		group = ''
		creator = False

		activity_summary = 'Pending review/revision of Requisition Order'
		activity_text = 'Your Requisition Order has been rejected. Kindly review and revise accordingly. <br/> <b>Reason: </b> %s <br/> <b>Rejected By: </b> %s' % (self.reason, self.env.user.name)

		if rof.rof_type == 'main':
			rof.sudo().write({
				'is_rejected': True,
				'is_whmchecked': False,
				'is_whchecked': False,
			})
			creator = rof.create_uid
		else:
			if rof.rof_state in ['whmchecked','whchecked']:
				# if rof.has_special_items:
				# 	rof.sudo().write({
				# 		'is_qsvalidated': True,
				# 		'is_whmchecked': False,
				# 		'is_whchecked': False,
				# 	})
				# else:
				# 	rof.sudo().write({
				# 		'is_omapproved': True,
				# 		'is_whmchecked': False,
				# 		'is_whchecked': False,
				# 	})

				rof.sudo().write({
					'is_qsvalidated': True,
					'is_whmchecked': False,
					'is_whchecked': False,
				})
			else:
				rof.sudo().write({'is_rejected': True})


			if rof.rof_state in ['omapproved','qsvalidated']:
				# Get Warehouseman
				group = 'group_main_warehouseman'
			else:
				creator = rof.create_uid

		for item in rof.rof_items:
			item.sudo().write({'is_checked_available_qty': False})


		rof.activity_creator(activity_text,activity_summary,group,creator)

		group_user = ''
		if self.env.user.has_group('carson_module.group_poc'):
			group_user = 'carson_module.group_poc'
		if self.env.user.has_group('carson_module.group_project_manager'):
			group_user = 'carson_module.group_project_manager'
		if self.env.user.has_group('carson_module.group_op_manager'):
			group_user = 'carson_module.group_op_manager'
		if self.env.user.has_group('carson_module.group_warehouse_supervisor'):
			group_user = 'carson_module.group_warehouse_supervisor'
		if self.env.user.has_group('carson_module.group_logistics_head'):
			group_user = 'carson_module.group_logistics_head'
		if group_user:
			rof.action_activity_done(group_user)