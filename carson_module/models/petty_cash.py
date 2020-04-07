from odoo import models, fields, api, _
from odoo.tools import float_is_zero, float_compare, pycompat
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
	_inherit = "account.invoice"

	state = fields.Selection([
		('draft','Draft'),
		('validate_warehouse_supervisor','Validated By Warehouse Supervisor'),
		('validate_ceo','Validated By CEO'),
		('open', 'Open'),
		('paid', 'Paid'),
		('cancel', 'Cancelled'),
		], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')

	@api.one
	def validate_ceo(self):
		self.write({'state': 'validate_ceo'})
		return True

	@api.one
	def validate_warehouse_supervisor(self):
		self.write({'state': 'validate_warehouse_supervisor'})
		return True

	@api.one
	def action_invoice_open(self):
		self.write({'state': 'open'})
		return True


	@api.multi
	def action_invoice_open(self):
		# lots of duplicate calls to action_invoice_open, so we remove those already open
		to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
		if to_open_invoices.filtered(lambda inv: inv.state != 'validate_ceo'):
			raise UserError(_("Invoice must be in draft state in order to validate it."))
		if to_open_invoices.filtered(lambda inv: float_compare(inv.amount_total, 0.0, precision_rounding=inv.currency_id.rounding) == -1):
			raise UserError(_("You cannot validate an invoice with a negative total amount. You should create a credit note instead."))
		to_open_invoices.action_date_assign()
		to_open_invoices.action_move_create()
		return to_open_invoices.invoice_validate()

	@api.multi
	def invoice_validate(self):
		self.write({'state': 'open'})
		for invoice in self.filtered(lambda invoice: invoice.partner_id not in invoice.message_partner_ids):
			invoice.message_subscribe([invoice.partner_id.id])
		self._check_duplicate_supplier_reference()
		return self
