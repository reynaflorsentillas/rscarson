# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import logging
import PyPDF2
import xml.dom.minidom
import zipfile

from odoo import api, models

_logger = logging.getLogger(__name__)

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.multi
    def unlink(self):
        for attachment in self:
            if attachment.res_model == 'purchase.order':
                purchase_order_obj = self.env[attachment.res_model].search([('id', '=', self.res_id)])
                message_str = "<strong>File Has Been Remove.</strong>"
                message_str += "<ul><li>Purchase Order: %s </li> <li>File Name: %s </li><li>File Type: %s </li> </ul>" %(purchase_order_obj.name, self.datas_fname, self.mimetype or '')
                res = purchase_order_obj.message_post(body=message_str)
        return super(IrAttachment, self).unlink()

    @api.model
    def create(self,vals):
        #Create a LOG NOTE When Attach a File in Purchase Order
        res = super(IrAttachment, self).create(vals)
        if vals['res_model'] == 'purchase.order' and res:
            purchase_order_obj = self.env[vals['res_model']].search([('id', '=', vals['res_id'])])
            if purchase_order_obj:
                message_str = "<strong>File Has Been Uploaded</strong>"
                message_str += "<ul><li>Purchase Order: %s </li>  <li>File Name: %s </li><li>File Type: %s </li> </ul>" %(purchase_order_obj.name, vals['datas_fname'], res.mimetype or '')
                res = purchase_order_obj.message_post(body=message_str)
                #raise Warning(res)

        return res
