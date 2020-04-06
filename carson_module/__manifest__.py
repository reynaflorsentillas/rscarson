# -*- coding: utf-8 -*-
{
    'name': "RS Carson module",

    'summary': """
        Development module for RS Carson customizations and enhancements""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Omnitechnical Global Solutions",
    'website': "http://www.omnitechnical.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base','product','sale','stock','purchase','mail','purchase_requisition', 'document', 'web', 'purchase_discount','mrp'],

    # always loaded
    'data': [
        'security/user_groups.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/rof_sequence.xml',
        'data/prod_category.xml',
        'data/pettycash.xml',
        'data/po_shoot_to_print_paper_format.xml',
        'data/data_area_zone.xml',
        'data/stock_warehouse.xml',
        'reports/rof_report.xml',
        'reports/rof_report_template.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/rof_views.xml',
        'views/preference_view.xml',
        'views/purchase_req_view.xml',
        'views/inventory_adjustment_view.xml',
        'views/custom_product_template_form.xml',
        'views/carson_projects_views.xml',
        'views/jo_views.xml',
        'views/stock_move_views.xml',
        'views/stock_picking_views.xml',
        'views/carson_menu_views.xml',
        'views/purchase_order_view.xml',
        'views/purchase_order_form_extend.xml',
        'views/price_discount.xml',
        'views/quantity_done.xml',
        # 'views/rof_views_addfield.xml',
        'views/stock_warehouse_views.xml',
        'views/mrp_production_views.xml',
        'wizard/rof_generate_purchase_view.xml',
        'wizard/rof_generate_job_view.xml',
        'wizard/rof_generate_mtf_view.xml',
        'wizard/rof_reject_view.xml',
        'wizard/rof_add_mtf_view.xml',
        'wizard/rof_generate_production_views.xml',
        'wizard/daily_purchase_summary_wiz.xml',
        'wizard/rof_add_purchase_view.xml',
        'wizard/res_user_pin_wizard.xml',
        'wizard/rof_user_pin_wizard.xml',
        'reports/report_deliveryslip.xml',
        'reports/report_stockpicking_operations.xml',
        'reports/purchase_order_quotation.xml',
        'reports/purchase_order_report.xml',
        'reports/purchase_order_shoot_to_print.xml',
        'reports/purchase_cash_transaction.xml',
        'reports/daily_purchase_summary_views.xml',
        'reports/daily_purchase_summary_report.xml',
        'views/res_partner.xml',
        'views/rof_wizard.xml',
        'views/stock_view_form_changes.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
