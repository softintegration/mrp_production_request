# -*- coding: utf-8 -*- 

import datetime

from odoo import models, fields, api, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'


    mrp_production_request_ids = fields.Many2many('mrp.production.request','mrp_production_request_mrp_production'
                                                  ,'mrp_production_id','mrp_production_request_id')

