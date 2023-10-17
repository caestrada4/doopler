# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import (UserError)
from . import utils


class AccountEpayment(models.Model):
    _name = 'account.epayment'

    code = fields.Char('Código')
    name = fields.Char('Forma de Pago')



class AccountMove(models.Model):
    _inherit='account.move'
    
    @api.depends('invoice_line_ids.tax_ids')
    def _check_retention(self):
        """
        Determina si hay impuestos de retenciones en las lineas de las factura
        :return:
        """
        try:
            TAXES = ['withhold_vat','withhold_income_tax']
            for tax in self.invoice_line_ids:
                for tax_line in tax.tax_ids:
                    if tax_line.tax_group_id.l10n_ec_type in TAXES:
                        self.has_retention = True
                        return True
            self.has_retention = False
        except:
            self.has_retention = False
    
    has_retention = fields.Boolean("Retencion" , compute='_check_retention'
                                   ,store=True)
    
    retention_id = fields.Many2one('account.retention', string='Retención', readonly=True, copy=False)
    sustento_sri = fields.Many2one('l10n_ec.sri.payment', string='Sustento del Comprobante',  copy=True)
    epayment_id = fields.Many2one('account.epayment', 'Forma de Pago')
    off_accounting = fields.Boolean('Fuera de Contabilidad', default=False)
       # === Date fields === #
    invoice_date = fields.Date(
        string='Invoice/Bill Date',
        readonly=True,
        states={'draft': [('readonly', False)]},
        index=True,
        copy=False,
        default=fields.Date.context_today,
        )
    
    authorization_number = fields.Char(
        string='Clave de Acceso',
        size=64,
        copy=False
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
    authorization_sri = fields.Boolean('¿Autorizado SRI?', readonly=True, copy =False)
    
    def action_post(self):
        super(AccountMove, self).action_post()
        if self.has_retention:
            self.action_withholding_create()
    
    def action_withholding_create(self):
        """
        Este método genera el documento de retencion en varios escenarios
        considera casos de:
        * Generar retencion automaticamente
        * Generar retencion de reemplazo
        * Cancelar retencion generada
        """
        TYPES_TO_VALIDATE = ['in_invoice', 'liq_purchase']
        wd_number = False
        for inv in self:
            if not self.has_retention:
                return True
            if inv.move_type in ['out_refund', 'in_refund']:
                raise UserError(utils.CODE810)
            ret_taxes =[]
            for line in inv.invoice_line_ids:
                for tax in line.tax_ids:
                    if tax.tax_group_id.l10n_ec_type in ['withhold_vat','withhold_income_tax']:
                         ret_taxes.append(line)
                         continue
                             
            if inv.retention_id:
                raise UserError(u'No se puede generar la retención, ya existe una retención generada para esta factura')

            type_doc = inv.move_type
            if inv.move_type == 'liq_purchase':
                type_doc = 'in_invoice'
            l10n_latam_document_type_id = self.env['l10n_latam.document.type'].search([('code', '=', 42)], limit=1)
            
            withdrawing_data = {
                'partner_id': inv.partner_id.id,
                'name': wd_number,
                'invoice_id': inv.id,
                'l10n_latam_document_type_id': l10n_latam_document_type_id.id,
                'in_type': 'ret_%s' % type_doc,
                'date': inv.invoice_date,
            }
            
            lines_data = []
            for line in inv.invoice_line_ids:
                for tax in line.tax_ids:
                    if tax.tax_group_id.l10n_ec_type in ['withhold_vat','withhold_income_tax']:
                        value_base = 0
                        value_amount = 0
                        if tax.tax_group_id.l10n_ec_type == 'withhold_vat':
                            value_amount = (line.price_subtotal * 12 / 100) * (tax.amount/100)
                            value_base = (line.price_subtotal * 12 / 100)
                            
                        elif tax.tax_group_id.l10n_ec_type == 'withhold_income_tax':
                            value_amount = (line.price_subtotal * tax.amount) /100 
                            value_base = line.price_subtotal 
                            
                        try:
                            if not tax.invoice_repartition_line_ids[1].account_id:
                                raise UserError(u'Especifique la cuenta contable para el impuesto %s' % tax.display_name)   
                        except:
                            raise UserError(u'Especifique la cuenta contable para el impuesto %s' % tax.display_name)

                        lines_data.append((0, 0, {
                            'fiscal_year': datetime.now().year,
                            'tax_id': tax.id,
                            'base': value_base,
                            'amount': value_amount,
                            'account_id': tax.invoice_repartition_line_ids[1].account_id.id
                        }))

            withdrawing_data.update({'move_ids': lines_data})
            withdrawing = self.env['account.retention'].create(withdrawing_data)
            withdrawing.write({'move_id': inv.id})

            if inv.move_type in TYPES_TO_VALIDATE:
                withdrawing.action_validate()

            inv.write({'retention_id': withdrawing.id})
        return True   
            
       


class AccountRetentionMove(models.Model):
    _name = 'account.retention.move'
    
    fiscal_year = fields.Char('Año Fiscal', default= lambda self: datetime.now().year)
    
    
    @api.onchange('tax_id')
    def _compute_base(self):
        for rec in self:
            if rec.tax_id:
                if not rec.retention_id.invoice_id and rec.retention_id.bank_retention == False:
                    raise UserError(_('No se ha seleccionado una factura'))
                try:
                    rec.account_id = rec.tax_id.invoice_repartition_line_ids[1].account_id
                except:
                    pass
                try:
                    # ('tax_group_id.l10n_ec_type','in',['withhold_vat','withhold_income_tax','outflows_tax','other'])]"
                    if rec.retention_id.bank_retention == True:
                        rec.base = 0
                        rec.amount = 0
                    elif rec.tax_id.tax_group_id.l10n_ec_type in ['withhold_vat']:
                        rec.base = rec.retention_id.invoice_id.amount_tax
                        rec.amount = rec.retention_id.invoice_id.amount_tax * rec.tax_id.amount / 100
                    elif rec.tax_id.tax_group_id.l10n_ec_type in ['withhold_income_tax','outflows_tax']:
                        rec.base = rec.retention_id.invoice_id.amount_untaxed
                        rec.amount = rec.retention_id.invoice_id.amount_untaxed * rec.tax_id.amount / 100
                    else:
                        rec.base = 0
                        rec.amount = 0
                except:
                    pass
    
    tax_id = fields.Many2one(
        'account.tax',
        string='Impuesto',
        required=True,
        copy=False
    )
    retention_id = fields.Many2one(
        'account.retention',
        string='Retencion',
        required=True,
        copy=False
    )
    
            
            
    l10n_ec_code_base = fields.Char(string='Codigo Base')
    base = fields.Float(string='Base',  store=True)
    amount = fields.Float(string='Valor Retenido', store=True)
    account_id = fields.Many2one('account.account', string='Cuenta', store=True)