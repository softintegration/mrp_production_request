# -*- coding: utf-8 -*- 

import datetime

from odoo import models, fields, api, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'


    mrp_production_request_id = fields.Many2one('mrp.production',ondelete='restrict')
