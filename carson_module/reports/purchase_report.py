# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

#
# Please note that these reports are not multi-currency !!!
#

from odoo import api, fields, models, tools


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    state = fields.Selection([
        ('draft', 'Draft RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
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
        ('done', 'Done'),
        ('cancel', 'Cancelled')
        ], 'Order Status', readonly=True)

    project_location = fields.Char(string="Project")

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'purchase_report')
        self._cr.execute("""
            create view purchase_report as (
                WITH currency_rate as (%s)
                select
                    min(l.id) as id,
                    s.date_order as date_order,
                    s.state,
                    s.date_approve,
                    s.dest_address_id,
                    spt.warehouse_id as picking_type_id,
                    s.partner_id as partner_id,
                    s.create_uid as user_id,
                    s.company_id as company_id,
                    s.fiscal_position_id as fiscal_position_id,
                    l.product_id,
                    p.product_tmpl_id,
                    t.categ_id as category_id,
                    s.currency_id,
                    t.uom_id as product_uom,
                    sum(l.product_qty/u.factor*u2.factor) as unit_quantity,
                    extract(epoch from age(s.date_approve,s.date_order))/(24*60*60)::decimal(16,2) as delay,
                    extract(epoch from age(l.date_planned,s.date_order))/(24*60*60)::decimal(16,2) as delay_pass,
                    count(*) as nbr_lines,
                    sum(l.price_unit / COALESCE(cr.rate, 1.0) * l.product_qty)::decimal(16,2) as price_total,
                    avg(100.0 * (l.price_unit / COALESCE(cr.rate,1.0) * l.product_qty) / NULLIF(ip.value_float*l.product_qty/u.factor*u2.factor, 0.0))::decimal(16,2) as negociation,
                    sum(ip.value_float*l.product_qty/u.factor*u2.factor)::decimal(16,2) as price_standard,
                    (sum(l.product_qty * l.price_unit / COALESCE(cr.rate, 1.0))/NULLIF(sum(l.product_qty/u.factor*u2.factor),0.0))::decimal(16,2) as price_average,
                    partner.country_id as country_id,
                    partner.commercial_partner_id as commercial_partner_id,
                    analytic_account.id as account_analytic_id,
                    sum(p.weight * l.product_qty/u.factor*u2.factor) as weight,
                    sum(p.volume * l.product_qty/u.factor*u2.factor) as volume,
                    (Select cps.name from carson_projects as cps where cps.id = (select cf.carson_project_id from carson_rof as cf where cf.id = s.rof_id)) as project_location
                from purchase_order_line l
                    join purchase_order s on (l.order_id=s.id)
                    join res_partner partner on s.partner_id = partner.id
                        left join product_product p on (l.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                            LEFT JOIN ir_property ip ON (ip.name='standard_price' AND ip.res_id=CONCAT('product.product,',p.id) AND ip.company_id=s.company_id)
                    left join product_uom u on (u.id=l.product_uom)
                    left join product_uom u2 on (u2.id=t.uom_id)
                    left join stock_picking_type spt on (spt.id=s.picking_type_id)
                    left join account_analytic_account analytic_account on (l.account_analytic_id = analytic_account.id)
                    left join currency_rate cr on (cr.currency_id = s.currency_id and
                        cr.company_id = s.company_id and
                        cr.date_start <= coalesce(s.date_order, now()) and
                        (cr.date_end is null or cr.date_end > coalesce(s.date_order, now())))
                group by
                    s.company_id,
                    s.create_uid,
                    s.partner_id,
                    u.factor,
                    s.currency_id,
                    l.price_unit,
                    s.date_approve,
                    l.date_planned,
                    l.product_uom,
                    s.dest_address_id,
                    s.fiscal_position_id,
                    l.product_id,
                    p.product_tmpl_id,
                    t.categ_id,
                    s.date_order,
                    s.state,
                    spt.warehouse_id,
                    u.uom_type,
                    u.category_id,
                    t.uom_id,
                    u.id,
                    u2.factor,
                    partner.country_id,
                    partner.commercial_partner_id,
                    analytic_account.id,
                    s.rof_id
            )
        """ % self.env['res.currency']._select_companies_rates())    