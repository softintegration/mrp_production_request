# -*- coding: utf-8 -*- 

import datetime

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare, float_round, float_is_zero
from odoo.tools import format_datetime


class MrpProductionRequest(models.Model):
    """ Manufacturing Orders request"""
    _name = 'mrp.production.request'
    _description = 'Manufacturing Request'
    _date_name = 'date_order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_request asc, date_desired asc,id'

    @api.model
    def _get_default_date_request(self):
        return datetime.datetime.now()

    @api.model
    def _get_default_request_user_id(self):
        return self.env.user.id

    name = fields.Char('Reference', copy=False, readonly=True, default=lambda x: _('New'))
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain="""[
            ('type', 'in', ('product',)),
            '|',
                ('company_id', '=', False),
                ('company_id', '=', company_id)
        ]
        """,
        readonly=True, required=True, check_company=True,
        states={'draft': [('readonly', False)]})
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_uom_id = fields.Many2one('uom.uom', 'Product Unit of Measure', readonly=True, required=True,
                                     states={'draft': [('readonly', False)]},
                                     domain="[('category_id', '=', product_uom_category_id)]")
    date_request = fields.Datetime('Date', copy=False, default=_get_default_date_request, index=True, required=True,
                                   states={'draft': [('readonly', False)]}, readonly=True)
    date_desired = fields.Datetime('Desired Date', copy=False, index=True, required=True,
                                   states={'draft': [('readonly', False)]}, readonly=True)
    quantity = fields.Float(string="Requested Quantity", digits='Product Unit of Measure', copy=False, requied=True)
    request_user_id = fields.Many2one('res.users', string='Requested by', default=_get_default_request_user_id,
                                      states={'draft': [('readonly', False)]}, readonly=True, required=True)
    approving_user_id = fields.Many2one('res.users', string='Approved by', readonly=True)
    bom_id = fields.Many2one(
        'mrp.bom', 'Bill of Material', states={'draft': [('readonly', False)]}, readonly=True,
        domain="""[
        '&',
            '|',
                ('company_id', '=', False),
                ('company_id', '=', company_id),
            '&',
                '|',
                    ('product_id','=',product_id),
                    '&',
                        ('product_tmpl_id.product_variant_ids','=',product_id),
                        ('product_id','=',False),
        ('type', '=', 'normal')]""",
        check_company=True,
        help="Bill of Materials that will be used for the created MO's.")
    origin = fields.Char(
        'Source', copy=False, states={'draft': [('readonly', False)]}, readonly=True,
        help="Reference of the document that generated this production order request.")
    mrp_production_ids = fields.One2many('mrp.production', 'mrp_production_request_id', readonly=True)
    quantity_produced = fields.Float(string='Produced Quantity', compute='_compute_quantity_produced', store=True)
    note = fields.Html(tring='Note')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting'),
        ('validated', 'Validated'),
        ('cancel', 'Cancelled')], string='State',
        compute='_compute_state', copy=False, index=True, readonly=True,
        store=True, tracking=True, default='draft',
        help=" * Draft: The MR is not confirmed yet.\n"
             " * Waiting: The MR is confirmed but waiting for approving.\n"
             " * Validated: The MR is confirmed, the production order can be created.\n"
             " * Cancelled: The MR has been cancelled, can't be confirmed anymore.")
    mrp_production_ids_count = fields.Integer("Count of linked MOs", compute='_compute_mrp_production_ids_count')
    can_create_mrp_production = fields.Boolean(compute='_compute_can_create_mrp_production')
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company,
        index=True, required=True)
    locked = fields.Boolean(string='Locked', help="If the request is locked we can't edit Requested Quantity",
                            default=False)

    @api.onchange('product_id', 'company_id')
    def _onchange_product_id(self):
        """ Finds UoM of changed product. """
        if not self.product_id:
            self.bom_id = False
        elif not self.bom_id or self.bom_id.product_tmpl_id != self.product_id.product_tmpl_id or (
                self.bom_id.product_id and self.bom_id.product_id != self.product_id):
            bom = self.env['mrp.bom']._bom_find(self.product_id, company_id=self.company_id.id, bom_type='normal')[
                self.product_id]
            if bom:
                self.bom_id = bom.id
                self.product_uom_id = self.bom_id.product_uom_id.id
            else:
                self.bom_id = False
                self.product_uom_id = self.product_id.uom_id.id

    @api.model
    def _get_default_name(self):
        return self.env.ref('mrp_production_request.seq_mrp_production_request').next_by_id()

    @api.model
    def create(self, vals):
        if vals.get("name", _("New")) == _("New"):
            vals["name"] = self._get_default_name()
        return super(MrpProductionRequest, self).create(vals)

    def action_make_waiting(self):
        return self._action_make_waiting()

    def action_validate(self):
        self._check_state('validated')
        return self._action_validate()

    def action_make_production_order(self):
        new_wizard = self.env['mrp.production.create'].create({
            'quantity': self.quantity,
            'product_uom_id': self.product_uom_id.id,
        })
        view_id = self.env.ref('mrp_production_request.view_mrp_production_create').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Production Order'),
            'view_mode': 'form',
            'res_model': 'mrp.production.create',
            'target': 'new',
            'res_id': new_wizard.id,
            'views': [[view_id, 'form']],
        }

    def action_cancel(self):
        return self._action_cancel()

    def _action_make_waiting(self):
        self.write({'state': 'waiting', 'locked': True})

    def _action_validate(self):
        self.write({'state': 'validated', 'approving_user_id': self.env.user.id})

    def _action_make_production_order(self, quantity=False, product_uom_id=False):
        mrp_production_dict_list = self._prepare_mrp_production(quantity=quantity, product_uom_id=product_uom_id)
        mrp_productions = self.env['mrp.production'].create(mrp_production_dict_list)
        return mrp_productions

    def _prepare_mrp_production(self, quantity=False, product_uom_id=False):
        mrp_prod_dict_list = []
        for each in self:
            mrp_prod_dict_list.append(
                each._prepare_singleton_mrp_production(quantity=quantity, product_uom_id=product_uom_id))
        return mrp_prod_dict_list

    def _prepare_singleton_mrp_production(self, quantity=False, product_uom_id=False):
        self.ensure_one()
        return {
            'mrp_production_request_id': self.id,
            'origin': self.name,
            'product_id': self.product_id.id,
            'product_qty': quantity or self.quantity,
            'product_uom_id': product_uom_id and product_uom_id.id or self.product_uom_id.id,
            'date_planned_start': self.date_desired,
            'bom_id': self.bom_id and self.bom_id.id or False,
        }

    def _action_cancel(self):
        self.write({'state': 'cancel'})

    def action_lock(self):
        self.write({'locked': True})

    def action_unlock(self):
        self.write({'locked': False})

    def _check_state(self, state):
        if state == 'validated':
            for each in self:
                if float_is_zero(each.quantity, precision_rounding=each.product_uom_id.rounding):
                    raise UserError(_('The Requested quantity must be positive!'))

    @api.depends('mrp_production_ids')
    def _compute_mrp_production_ids_count(self):
        for each in self:
            each.mrp_production_ids_count = len(each.mrp_production_ids)

    @api.depends('mrp_production_ids')
    def _compute_can_create_mrp_production(self):
        for each in self:
            each.can_create_mrp_production = len(each.mrp_production_ids.filtered(lambda mp: mp.state != 'cancel')) > 0

    @api.depends('mrp_production_ids')
    def _compute_quantity_produced(self):
        pass

    @api.constrains('date_request', 'date_desired')
    def _check_date_range(self):
        for each in self:
            if each.date_request and each.date_desired and each.date_request > each.date_desired:
                raise ValidationError(_('%s : Desired Date (%s) should be greater than Date (%s)', each.name,
                                        format_datetime(self.env, each.date_desired),
                                        format_datetime(self.env, each.date_request)))
        return True

    def action_view_mrp_productions(self):
        mrp_production_ids = self.mrp_production_ids.ids
        return {
            'res_model': 'mrp.production',
            'type': 'ir.actions.act_window',
            'name': _("MO's"),
            'domain': [('id', 'in', mrp_production_ids)],
            'view_mode': 'tree,form',
        }
