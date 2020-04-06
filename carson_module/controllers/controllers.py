# -*- coding: utf-8 -*-
from odoo import http

# class CarsonModule(http.Controller):
#     @http.route('/carson_module/carson_module/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/carson_module/carson_module/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('carson_module.listing', {
#             'root': '/carson_module/carson_module',
#             'objects': http.request.env['carson_module.carson_module'].search([]),
#         })

#     @http.route('/carson_module/carson_module/objects/<model("carson_module.carson_module"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('carson_module.object', {
#             'object': obj
#         })