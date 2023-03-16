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
    date_desired = fields.Datetime('Desired Date', copy=False, index=True, required=True)
    quantity = fields.Float(string="Requested Quantity", digits='Product Unit of Measure', copy=False, requied=True)
    request_user_id = fields.Many2one('res.users', string='Requested by', default=_get_default_request_user_id,
                                      states={'draft': [('readonly', False)]}, readonly=True, required=True)
    approving_user_id = fields.Many2one('res.users', string='Approved by', readonly=True)
    bom_id = fields.Many2one(
        'mrp.bom', 'Bill of Material',
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
    mrp_production_ids = fields.Many2many('mrp.production', 'mrp_production_request_mrp_production',
                                          'mrp_production_request_id', 'mrp_production_id', readonly=True)
    quantity_produced = fields.Float(string='Produced Quantity', compute='_compute_quantity_produced',
                                     inverse='_set_quantity_produced', store=True)
    quantity_produced_set_man = fields.Boolean(default=False,
                                               help='If the Produced Quantity have been set manually,if this is true the field will not be overwritten by _compute_quantity_produced method')
    note = fields.Html(tring='Note', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting'),
        ('validated', 'Validated'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='State',
        compute='_compute_state', copy=False, index=True, readonly=True,
        store=True, tracking=True, default='draft',
        help=" * Draft: The MR is not confirmed yet.\n"
             " * Waiting: The MR is confirmed but waiting for approving.\n"
             " * Validated: The MR is confirmed, the production order can be created.\n"
             " * Done: The MR is done, can't be update or deleted anymore.\n"
             " * Cancelled: The MR has been cancelled, can't be confirmed anymore.")
    mrp_production_ids_count = fields.Integer("Count of linked MOs", compute='_compute_mrp_production_ids_count')
    can_create_mrp_production = fields.Boolean(compute='_compute_can_create_mrp_production')
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company,
        index=True, required=True)
    locked = fields.Boolean(string='Locked', help="If the request is locked we can't edit Requested Quantity",
                            default=False)
    mrp_production_request_date_desired_remove_check = fields.Boolean(
        compute='_compute_mrp_production_request_date_desired_remove_check')

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

    def write(self, vals):
        if not self.env.context.get('force_update', False) and any(each.state in ('done', 'cancel') for each in self):
            raise ValidationError(_("Can not update Done or Cancelled Request!"))
        return super(MrpProductionRequest, self).write(vals)

    def unlink(self):
        if any(production_request.state != 'draft' for production_request in self):
            raise ValidationError(_("Only draft Production requests can be removed!"))
        return super(MrpProductionRequest, self).unlink()

    def action_make_waiting(self):
        return self._action_make_waiting()

    def action_validate(self):
        self._check_state('validated')
        return self._action_validate()

    def action_done(self):
        self._check_state('done')
        return self._action_done()

    def action_make_production_order(self):
        product_ids = self.mapped("product_id")
        if len(product_ids) > 1:
            raise ValidationError(_("All the selected Production Requests must be for the same product!"))
        for each in self:
            if each.state != "validated":
                raise ValidationError(_("Only validated Production requests can create Production order!"))
        new_wizard = self.env['mrp.production.create'].create({
            'request_ids': [(6, 0, self.ids)],
            'quantity': sum(self.mapped("quantity")),
            'product_uom_id': self.mapped("product_uom_id")[0].id,
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
            'context': self.env.context
        }

    def action_cancel(self):
        return self._action_cancel()

    def _action_make_waiting(self):
        self.write({'state': 'waiting', 'locked': True})

    def _action_validate(self):
        self.write({'state': 'validated', 'approving_user_id': self.env.user.id})

    def _action_done(self):
        self.write({'state': 'done'})

    def _action_make_production_order(self, quantity=False, product_uom_id=False):
        mrp_production_dict_list = self._prepare_mrp_production(quantity=quantity, product_uom_id=product_uom_id)
        mrp_productions = self.env['mrp.production'].create(mrp_production_dict_list)
        mrp_productions._inherit_manual_creation_behaviour()
        return mrp_productions

    def _prepare_mrp_production(self, quantity=False, product_uom_id=False):
        return {
            'mrp_production_request_ids': [(6, 0, self.ids)],
            'origin': self.mapped("name")[0],
            'product_id': self.mapped("product_id")[0].id,
            'product_qty': quantity or self.quantity,
            'product_uom_id': product_uom_id and product_uom_id.id or self.mapped("product_uom_id")[0].id,
            'date_planned_start': self.mapped("date_desired")[0],
            'bom_id': self.mapped("bom_id") and self.mapped("bom_id")[0].id or False,
        }

    def _action_cancel(self):
        self.write({'state': 'cancel'})

    def action_lock(self):
        self.write({'locked': True})

    def action_unlock(self):
        self.write({'locked': False})

    def _check_state(self, state):
        if state in ('validated', 'done'):
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

    def _force_recompute_quantity_produced(self):
        self.with_context(force_update=True)._compute_quantity_produced()

    @api.depends('mrp_production_ids.state','mrp_production_ids.qty_produced','quantity_produced_set_man')
    def _compute_quantity_produced(self):
        # we have to re-calculate only production requests that have not been edited manually
        for each in self.filtered(lambda pr:not pr.quantity_produced_set_man):
            each.with_context(compute_update=True).quantity_produced = sum(
                production.product_uom_id._compute_quantity(production.qty_produced, each.product_uom_id)
                for production in each.mrp_production_ids.filtered(lambda pr: pr.product_id.id == each.product_id.id))

    def _set_quantity_produced(self):
        for each in self:
            each.quantity_produced_set_man = not self.env.context.get('compute_update',False)


    @api.constrains('date_request', 'date_desired', 'mrp_production_request_date_desired_remove_check')
    def _check_date_range(self):
        for each in self:
            if each.mrp_production_request_date_desired_remove_check:
                continue
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

    def _compute_mrp_production_request_date_desired_remove_check(self):
        """ The setting that tell if we have to always overwrite the module"""
        self.mrp_production_request_date_desired_remove_check = self._get_mrp_production_request_date_desired_remove_check()

    def _get_mrp_production_request_date_desired_remove_check(self):
        """ The private method of the previous setting"""
        IrDefault = self.env['ir.default'].sudo()
        return IrDefault.get('res.config.settings', 'mrp_production_request_date_desired_remove_check',
                             company_id=self.company_id.id or self.env.user.company_id.id)
