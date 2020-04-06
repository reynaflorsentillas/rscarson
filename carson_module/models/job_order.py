from odoo import models, fields, api, _ 

class CarsonJobOrder(models.Model):
	_name = "carson.job.order"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description ="Carson Job Order"

	name = fields.Char(string='JO No.', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
	customer_id = fields.Many2one('res.partner', string='Customer', required=True)
	state = fields.Selection([('draft','Draft'), 
		('pending','Pending'), 
		('approve','Approved'),
		('inprogress','In Progress'),
		('done','Done'), 
		('cancelled','Cancelled')], default='draft',readonly=True, track_visibility='onchange')
	line_ids = fields.One2many('carson.job.order.line', 'jo_id', string='Job Order Lines')
	rof_id = fields.Many2one('carson.rof', string='ROF')

	@api.model
	def create(self, vals):
		if vals.get('name', _('New')) == _('New'):
			vals['name'] = self.env['ir.sequence'].next_by_code('carson.jo') or _('New')
		result = super(CarsonJobOrder, self).create(vals)
		return result

class CarsonJobOrderLine(models.Model):
	_name = "carson.job.order.line"
	_description = "Carson Job Order Lines"

	jo_id = fields.Many2one('carson.job.order', 'Job Order')
	product_id = fields.Many2one('product.product', string='Item')
	location_id = fields.Many2one('stock.location',required=False) 
	location_dest_id = fields.Many2one('stock.location',required=False)