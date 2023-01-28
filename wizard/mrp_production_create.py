# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models,_
from odoo.exceptions import ValidationError,UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class MrpProductionCreate(models.TransientModel):
    _name = 'mrp.production.create'

    quantity = fields.Float(string="Quantity to produce", digits='Product Unit of Measure')
    product_uom_id = fields.Many2one('uom.uom', 'Product Unit of Measure', readonly=True)

    def apply(self):
        if float_compare(self.quantity, 0.0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise ValidationError(_('Quantity to produce must be positive!'))
        if self.env.context.get('active_ids') and self.env.context.get('active_model') == 'mrp.production.request':
            #if len(self.env.context.get('active_ids', list())) > 1:
            #    raise UserError(_("You may only return one production request at a time."))
            production_requests = self.env['mrp.production.request'].browse(self.env.context.get('active_ids'))
            production_requests._action_make_production_order(quantity=self.quantity)
        else:
            raise UserError(_("No production request source detected!"))




    def _prepare_production_request(self,item):
        return {
            'product_id':item.product_id.id,
            'product_uom_id':item.product_uom_id.id,
            'date_request':fields.Datetime.now(),
            'date_desired':item.date_desired,
            'quantity':item.quantity_to_do,
            'sale_line_id':item.sale_line_id.id,
            'sale_id':item.sale_line_id.order_id.id,
            'origin':item.sale_line_id.order_id.name
        }




class ProductionRequestsCreateItem(models.TransientModel):
    _name = 'production.requests.create.item'

    checked = fields.Boolean(string='Check',default=False)
    request_id = fields.Many2one('production.requests.create')
    product_id = fields.Many2one('product.product',string='Product',required=True)
    quantity = fields.Float(string="Quantity to plan", digits='Product Unit of Measure')
    quantity_to_do = fields.Float(string="Quantity to do", digits='Product Unit of Measure', requied=True)
    product_uom_id = fields.Many2one('uom.uom', 'Product Unit of Measure',required=True)
    date_desired = fields.Datetime('Desired Date')
    sale_line_id = fields.Many2one('sale.order.line', 'Sale Line', required=True)
