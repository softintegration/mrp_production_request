# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models,_
from odoo.exceptions import ValidationError,UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class MrpProductionRequestConfirm(models.TransientModel):
    _name = 'mrp.production.request.confirm'

    request_ids = fields.Many2many('mrp.production.request','mrp_production_request_confirm_request','confirm_id','production_request_id')
    confirm_message = fields.Text()

    def apply(self):
        return self.request_ids.action_make_production_order()
