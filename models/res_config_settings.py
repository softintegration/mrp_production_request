# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mrp_production_request_date_desired_remove_check = fields.Boolean("Remove Desired Date check")

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set('res.config.settings', "mrp_production_request_date_desired_remove_check", self.mrp_production_request_date_desired_remove_check,
                      company_id=self.company_id.id or self.env.user.company_id.id)