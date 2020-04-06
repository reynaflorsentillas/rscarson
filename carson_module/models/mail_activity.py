from odoo import models, fields, api, _ 

import logging
_logger = logging.getLogger('models')

class MailActivity(models.Model):
	_inherit = 'mail.activity'
	_order = 'date_deadline, create_date DESC'

	# @api.multi
	# def action_done(self):

	# 	_logger.info('HEARTE')

	# 	for activity in self:
	# 		record = self.env[activity.res_model].browse(activity.res_id)
			
	# 		_logger.info(record)

	# 	result = super(MailActivity, self).action_done()



	# 	return result

	def action_cancel_dup_activity(self, res_model, res_id, activity_id):
		_logger.info(res_model)
		_logger.info(res_id)
		_logger.info(activity_id)
		if res_model == 'carson.rof':
			mail_activity = self.env['mail.activity'].search([('res_model','=',res_model),('res_id','=',res_id),('id','!=',activity_id)])
			_logger.info(mail_activity)
			for activity in mail_activity:
				if self.env.user.has_group('carson_module.group_poc') and activity.user_id.has_group('carson_module.group_poc') and activity.user_id != self.env.user:
					activity.unlink()
				elif self.env.user.has_group('carson_module.group_project_manager') and activity.user_id.has_group('carson_module.group_project_manager') and activity.user_id != self.env.user:
					activity.unlink()



	def action_feedback(self, feedback=False):

		# if self.env.user.has_group('carson_module.group_poc'):
		# 	mail_activity = self.env['mail.activity'].search([('res_id','=',self.res_id)])
		# 	_logger.info("HELLO")
		# 	_logger.info(mail_activity)
		# 	for act in mail_activity:
		# 		if act.user_id.has_group('carson_module.group_poc') and act.user_id != self.env.user:
		# 			act.action_done()

		# result = super(MailActivity, self).action_feedback(feedback)

		# return result

		_logger.info("FEEDBACK")
		message = self.env['mail.message']
		if feedback:
			self.write(dict(feedback=feedback))
		for activity in self:
			record = self.env[activity.res_model].browse(activity.res_id)
			_logger.info(record)
			record.message_post_with_view(
				'mail.message_activity_done',
				values={'activity': activity},
				subtype_id=self.env.ref('mail.mt_activities').id,
				mail_activity_type_id=activity.activity_type_id.id,
			)
			message |= record.message_ids[0]
			activity.action_cancel_dup_activity(activity.res_model, activity.res_id, activity.id)



		self.unlink()
		return message.ids and message.ids[0] or False

