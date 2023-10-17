# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import (
    api,
    fields,
    models
)
from odoo.exceptions import (UserError)


class AccountWithdrawing(models.Model):
    """ Implementacion de documento de retencion """
    _name = 'account.retention'
    _description = 'Withdrawing Documents'
    _order = 'date DESC'

    @api.depends('move_ids.amount')
    def _compute_total(self):
        """
        Calcula el total de la retención
        calcula los valores para el reporte
        """
        self.amount_valor_retencion = 0  # / 0.30
        self.isb = 0
        self.val_ret_bienes = 0
        self.val_ret_bien_10 = 0
        self.val_ret_serv_20 = 0
        self.val_ret_serv_50 = 0
        self.val_ret_serv_100 = 0
        for tax in self.move_ids:
            # if tax.base == 0:
            #    self.recalcular_base(tax)
            
         if tax.amount != None:
             self.amount_valor_retencion += tax.amount  # / 0.30
         if tax.tax_id.tax_group_id.l10n_ec_type == 'ice':
             self.isb += tax.amount
         if tax.tax_id.tax_group_id.l10n_ec_type == 'withhold_vat':
             if abs(int(tax.tax_id.amount)) == 30:
                 self.amount += tax.amount
             if abs(int(tax.tax_id.amount)) == 10:
                 self.val_ret_bien_10 += tax.amount
         if tax.tax_id.tax_group_id.l10n_ec_type == 'withhold_vat':
             if abs(int(tax.tax_id.amount)) == 70:
                 self.val_ret_serv += tax.amount
             if abs(int(tax.tax_id.amount)) == 20:
                 self.val_ret_serv_20 += tax.amount
             if abs(int(tax.tax_id.amount)) == 50:
                 self.val_ret_serv_50 += tax.amount
             if abs(int(tax.tax_id.amount)) == 100:
                 self.val_ret_serv_100 += tax.amount

        self.amount_total = sum(tax.amount for tax in self.move_ids)

    def _get_report_base_filename(self):
        return self.name

    def _get_in_type(self):
        context = self._context
        return context.get('in_type', 'ret_out_invoice')
        """_summary_
        """

    def _default_type(self):
        context = self._context
        return context.get('type', 'out_invoice')

    STATES_VALUE = {'draft': [('readonly', False)]}

    name = fields.Char(
        'Número',
        size=64,
        readonly=True,
        states=STATES_VALUE,
        copy=False
    )
    internal_number = fields.Char(
        'Número Interno',
        size=64,
        readonly=True,
        copy=False
    )

    date = fields.Date(
        'Fecha Emision',
        readonly=True,
        states={'draft': [('readonly', False)]}, required=True
    )

    in_type = fields.Selection(
        [
            ('ret_in_invoice', u'Retención a Proveedor'),
            ('ret_out_invoice', u'Retención de Cliente')
        ],
        string='Tipo',
        readonly=True,
        default=_get_in_type
    )

    move_ids = fields.One2many(
        'account.retention.move',
        'retention_id',
        'Detalle de Impuestos',
        readonly=True,
        states=STATES_VALUE,
        copy=False
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Documento',
        required=False,
        readonly=True,
        states=STATES_VALUE,
        # domain=[('state', '=', 'open')],
        copy=False
    )
    move_id = fields.Many2one(
        'account.move',
        string='Asiento Contable',
        required=False,
        readonly=True,
        copy=False
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Empresa',
        required=True,
        readonly=True,
        states=STATES_VALUE
    )
    bank_retention = fields.Boolean(
        string='Retención Tarjeta Crédito',
        readonly=True,
        states=STATES_VALUE
    )
    
    bank_document = fields.Char(
        string='Documento',
        size=17,
    )


    l10n_latam_document_type_id = fields.Many2one(
        'l10n_latam.document.type', 'Document Type', index=True)

    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('done', 'Validado'),
            ('cancel', 'Anulado')
        ],
        readonly=True,
        string='Estado',
        default='draft'
    )

    def action_cancel(self):
        """
        Método para cambiar de estado a cancelado el documento
        """
        for ret in self:
            self.write({'state': 'cancel'})
        return True

    def button_validate(self):
        """
        Botón de validación de Retención que se usa cuando
        se creó una retención manual, esta se relacionará
        con la factura seleccionada.
        :return:
        """
        self.ensure_one()
        if self.in_type == 'ret_out_invoice':
            if len(self.name) != 17:
                raise UserError(
                    u'El número de retención inconcorrecto debe el siquiente formato 000-000-000000000')
            self.write({
                'state': 'done',
            })
        else:
            sequence = self._set_next_sequence()
            str_sequence = str(sequence).zfill(9)
            l10n_ec_retention_entity = self.invoice_id.journal_id.l10n_ec_retention_entity
            l10n_ec_retention_emission = self.invoice_id.journal_id.l10n_ec_retention_emission
            name = "{}-{}-{}".format(l10n_ec_retention_entity,
                                     l10n_ec_retention_emission, str_sequence)

            self.write({
                'state': 'done',
                'l10n_ec_retention_entity': l10n_ec_retention_entity,
                'l10n_ec_retention_emission': l10n_ec_retention_emission,
                'name': name,
                'sequence': sequence
            })
        self.invoice_id.write({'retention_id': self.id})
        if not self.invoice_id.has_retention:
            self._create_move()
        else:
            self.sudo().write({'move_id': self.invoice_id.id})
        return True

    def action_validate(self):
        """
        Valida la retencion desde la factura, no genera movimientos
        :return:
        """
        self.ensure_one()
        sequence = self._set_next_sequence()

        str_sequence = str(sequence).zfill(9)
        l10n_ec_retention_entity = self.invoice_id.journal_id.l10n_ec_retention_entity
        l10n_ec_retention_emission = self.invoice_id.journal_id.l10n_ec_retention_emission
        name = "{}-{}-{}".format(l10n_ec_retention_entity,
                                 l10n_ec_retention_emission, str_sequence)

        self.write({
            'state': 'done',
            'l10n_ec_retention_entity': l10n_ec_retention_entity,
            'l10n_ec_retention_emission': l10n_ec_retention_emission,
            'name': name,
            'sequence': sequence
        })

        return True

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        retention = super(AccountWithdrawing, self).create(vals_list)
        retention.invoice_id.write({'retention_id': retention.id})
        return retention

    def _create_move(self):
        """
        Genera los asientos contables de la retencion
        :return:
        """
        self.ensure_one()
        inv = self.invoice_id
        total_counter = 0
        lines = []
        if self.move_id:
            self.move_id.unlink()

        move_data = {
            'journal_id': self.invoice_id.journal_id.id,
            'ref': "RET-{}".format(self.name),
            'date': self.date,
            'move_type': 'entry',
            'l10n_latam_document_type_id': self.l10n_latam_document_type_id.id,
            'l10n_latam_document_number': self.name,
        }
        if self.bank_retention:
            journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
            move_data.update({'journal_id': journal.id})
            if journal==None or not journal.account_bank_retention:
                raise UserError(u'Especifique la cuenta de retención bancaria en el diario de ventas')
                     
            for line in self.move_ids:
                lines.append((0, 0, {
                    'partner_id': self.partner_id.id,
                    'account_id': journal.account_bank_retention.id,
                    'name': self.name,
                    'credit': 0.00,
                    'debit': abs(line.amount)
                }))
                total_counter += abs(line.amount)

            lines.append((0, 0, {
                'partner_id': self.partner_id.id,
                'account_id': self.partner_id.property_account_payable_id.id,
                'name': self.name,
                'credit': total_counter,
                'debit': 0.00
            }))

        elif self.invoice_id.move_type in ('in_invoice', 'liq_purchase'):
            for line in self.move_ids:
                lines.append((0, 0, {
                    'partner_id': self.partner_id.id,
                    'account_id': line.account_id.id,
                    'name': self.name,
                    'debit': 0.00,
                    'credit': abs(line.amount)
                }))
                total_counter += abs(line.amount)

            lines.append((0, 0, {
                'partner_id': self.partner_id.id,
                'account_id': inv.partner_id.property_account_payable_id.id,
                'name': self.name,
                'debit': total_counter,
                'credit': 0.00
            }))
        elif self.invoice_id.move_type in ('out_invoice'):
            for line in self.move_ids:
                lines.append((0, 0, {
                    'partner_id': self.partner_id.id,
                    'account_id': line.account_id.id,
                    'name': self.name,
                    'credit': 0.00,
                    'debit': abs(line.amount)
                }))

                total_counter += abs(line.amount)

            lines.append((0, 0, {
                'partner_id': self.partner_id.id,
                'account_id': inv.partner_id.property_account_payable_id.id,
                'name': self.name,
                'credit': total_counter,
                'debit': 0.00
            }))

        move_data.update({'line_ids': lines})

        move = self.env['account.move'].sudo().create(move_data)

        # acctype = self.type == 'in_invoice' and 'payable' or 'receivable'
        # inv_lines = inv.move_id.line_ids
        # acc2rec = inv_lines.filtered(lambda l: l.account_id.internal_type == acctype)  # noqa
        # acc2rec += move.line_ids.filtered(lambda l: l.account_id.internal_type == acctype)  # noqa
        # acc2rec.auto_reconcile_lines()

        move_name = move.name.split(' ')

        move_name = "RET-{}-{}".format(self.company_id.id, move_name[1])
        move.sudo().write({'name': move_name})

        self.sudo().write({'move_id': move.id})
        move.action_post()

        return True

    amount_total = fields.Float(
        compute='_compute_total',
        string='Total',
        store=True,
        readonly=True
    )
    amount_valor_retencion = fields.Float(
        string='Ret. IVA',
        store=True,
        readonly=True
    )
    val_ret_bienes = fields.Float(
        string='Ret. Bienes',
        store=True,
        readonly=True
    )
    val_ret_bien_10 = fields.Float(
        string='Ret. Bienes 10%',
        store=True,
        readonly=True
    )

    val_ret_serv = fields.Float(
        string='Ret. Servicios',
        store=True,
        readonly=True
    )
    val_ret_serv_20 = fields.Float(
        string='Ret. Servicios 20%',
        store=True,
        readonly=True
    )
    val_ret_serv_50 = fields.Float(
        string='Ret. Servicios 50%',
        store=True,
        readonly=True
    )
    val_ret_serv_100 = fields.Float(
        string='Ret. Servicios 100%',
        store=True,
        readonly=True
    )
    isb = fields.Float(
        string='isb',
        help="Contribución Superitendencia de Bancos",
        store=True,
        readonly=True
    )

    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        change_default=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env.company.id
    )

    authorization_number = fields.Char(
        string='Numero de autorizacion',
        size=64
    )

    authorization_state = fields.Char(
        'Estado de Autorización',
        size=64,
        readonly=True,
        copy=False
    )
    authorization_date = fields.Datetime(
        'Fecha Autorización',
        readonly=True,
        copy=False
    )
    environment = fields.Char(
        'Ambiente',
        size=64,
        readonly=True,
        copy=False
    )
    authorization_sri = fields.Boolean(
        '¿Autorizado SRI?', readonly=True, copy=False)

    sequence = fields.Integer(string='Sequence', default=1, store=True)
    l10n_ec_retention_entity = fields.Char(
        string="Emission Retention Entity", size=3)
    l10n_ec_retention_emission = fields.Char(
        string="Emission Retencion Point", size=3)

    def _set_next_sequence(self):
        """
        Set the next sequence on the journal
        """
        self.ensure_one()
        sql = """
                select  max(ar.sequence) max  from account_retention ar 
                inner join account_move am on ar.invoice_id = am.id 
                where am.company_id  = {} and l10n_ec_retention_entity = '{}' and l10n_ec_retention_emission = '{}' 
            """.format(self.company_id.id, self.invoice_id.journal_id.l10n_ec_retention_entity,
                       self.invoice_id.journal_id.l10n_ec_retention_emission)

        self.env.cr.execute(sql)
        value = self.env.cr.fetchone()
        return value[0] + 1 if value[0] else 1

    def action_draft(self):
        self.write({'state': 'draft'})
        return True

    def print_retention(self):
        return self.env.ref('l16n_ec_withholding.account_withholding_report').report_action(self)
