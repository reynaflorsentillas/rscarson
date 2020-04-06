# -*- coding: utf-8 -*-

from odoo import fields, models, api

class ResUsersPinWiz(models.TransientModel):
	_name = 'res.users.pin.wizard'

	def _default_user_ids(self):
		res_users = self.env['res.users'].browse(self._context.get('active_id'))
		return res_users

	user_id = fields.Many2one('res.users', string="Users", default=_default_user_ids)
	pin_numb = fields.Char(string='Pin Number', size=6, required=True)

	@api.one
	def generatePin(self):
		res_users_pin_model = self.env['res.users.pin']
		return res_users_pin_model.maintainUserPin(self.user_id.id, self.pin_numb)