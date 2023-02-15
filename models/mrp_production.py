# -*- coding: utf-8 -*- 

import datetime

from odoo import models, fields, api, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'


    mrp_production_request_ids = fields.Many2many('mrp.production.request','mrp_production_request_mrp_production'
                                                  ,'mrp_production_id','mrp_production_request_id')

    def _inherit_manual_creation_behaviour(self):
        for mrp_production in self:
            mrp_production._onchange_move_raw()
            mrp_production._onchange_company_id()
            mrp_production._onchange_product_id()
            mrp_production._onchange_product_qty()
            mrp_production._onchange_date_planned_start()
            #mrp_production._onchange_bom_id()
            #mrp_production._onchange_move_finished_product()
            mrp_production._onchange_move_finished()
            mrp_production._onchange_picking_type()
            mrp_production._onchange_location()
            mrp_production._onchange_location_dest()
            mrp_production._onchange_producing()
            mrp_production._onchange_lot_producing()
            mrp_production._onchange_workorder_ids()