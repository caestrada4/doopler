# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ExtractoBancario(models.Model):
    _name = 'extracto.bancario'
    _order = 'date,referencia  DESC'

    date = fields.Date('Fecha', required=True)
    codigo = fields.Char('Código')
    concepto = fields.Char('Concepto')
    referencia = fields.Char('Referencia', required=True)
    oficina = fields.Char('Ocicina')
    debe = fields.Float('Debe Extracto')
    haber = fields.Float('Haber Extracto')
    conciliado = fields.Boolean('Conciliado', required=True)
    revisado = fields.Boolean('Revisado', default=False)
    select = fields.Boolean('Selecionar')

    type = fields.Selection([('ext', 'Extracto'), ('move', 'Banco')], 'Tipo')

    account_id = fields.Many2one(
        'account.account',
        'Cuenta',
        required=True,
        readonly=True)

    concile_id = fields.Many2one(
        'account.bank.reconcile',
        'Hoja de Conciliacion')

    move_id = fields.Many2one(
        'account.move.line',
        'Movimiento')

    extracto_ids = fields.Many2one('account.account', string='Conciliados')

    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        change_default=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('account.invoice')  # noqa
    )

    # _sql_constraints = [
    #     (
    #         'reference_unique', 'unique(referencia,codigo, company_id)',
    #         'Numero de movimiento bancario ya se encuentras en el sistema!'),
    # ]

    
    def action_done(self):
        self.select = not self.select
        self.write({'conciliado': not self.conciliado})
        # if self.type == 'move':
        #   self.move_id.write({'conciled': not self.conciliado})
